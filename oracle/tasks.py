"""
Celery tasks for periodic analysis and data fetching
"""
from celery import shared_task
from django.utils import timezone
from datetime import datetime, timedelta
import logging

from oracle.models import (
    Symbol, MarketType, Timeframe, Decision, FeatureContribution,
    MarketData, DerivativesData, MacroData, AnalysisRun
)
from oracle.engine import DecisionEngine
from oracle.providers import BinanceProvider, YFinanceProvider, MacroDataProvider

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def run_analysis(self, run_id: str):
    """
    Run analysis for a specific analysis run

    Args:
        run_id: UUID of the analysis run
    """
    try:
        # Get analysis run
        analysis_run = AnalysisRun.objects.get(run_id=run_id)
        analysis_run.status = 'RUNNING'
        analysis_run.started_at = timezone.now()
        analysis_run.save()

        # Get symbols, market types, timeframes
        symbols = Symbol.objects.filter(symbol__in=analysis_run.symbols, is_active=True)
        market_types = MarketType.objects.filter(name__in=analysis_run.market_types)
        timeframes = Timeframe.objects.filter(name__in=analysis_run.timeframes)

        # Initialize providers
        crypto_provider = BinanceProvider()
        traditional_provider = YFinanceProvider()
        macro_provider = MacroDataProvider()

        # Fetch macro data once
        macro_context = _fetch_macro_data(macro_provider)

        decisions_created = 0
        errors = []

        # Analyze each symbol
        for symbol in symbols:
            logger.info(f"Analyzing {symbol.symbol}")

            try:
                # Determine which provider to use
                if symbol.asset_type == 'CRYPTO':
                    provider = crypto_provider
                    # Convert symbol format (BTCUSDT -> BTC/USDT for CCXT)
                    provider_symbol = f"{symbol.base_currency}/{symbol.quote_currency}"
                else:
                    provider = traditional_provider
                    provider_symbol = symbol.symbol

                # Analyze for each market type and timeframe
                for market_type in market_types:
                    for timeframe in timeframes:
                        try:
                            # Fetch market data
                            df = provider.fetch_ohlcv(
                                symbol=provider_symbol,
                                timeframe=timeframe.name,
                                limit=500
                            )

                            if df.empty:
                                logger.warning(f"No data for {symbol.symbol} {timeframe.name}")
                                continue

                            # Build context
                            context = {
                                'macro': macro_context
                            }

                            # Add derivatives data if applicable
                            if market_type.name in ['PERPETUAL', 'FUTURES'] and symbol.asset_type == 'CRYPTO':
                                derivatives_context = _fetch_derivatives_data(
                                    crypto_provider,
                                    provider_symbol
                                )
                                context['derivatives'] = derivatives_context

                            # Run decision engine
                            engine = DecisionEngine(
                                symbol=symbol.symbol,
                                market_type=market_type.name,
                                timeframe=timeframe.name
                            )

                            decision_output = engine.generate_decision(df, context)

                            # Save decision
                            decision = Decision.objects.create(
                                symbol=symbol,
                                market_type=market_type,
                                timeframe=timeframe,
                                signal=decision_output.signal,
                                bias=decision_output.bias,
                                confidence=decision_output.confidence,
                                entry_price=decision_output.entry_price,
                                stop_loss=decision_output.stop_loss,
                                take_profit=decision_output.take_profit,
                                risk_reward=decision_output.risk_reward,
                                invalidation_conditions=decision_output.invalidation_conditions,
                                top_drivers=[d for d in decision_output.top_drivers],
                                raw_score=decision_output.raw_score,
                                regime_context=decision_output.regime_context
                            )

                            # Save feature contributions
                            for contrib in decision_output.top_drivers:
                                # Get or create feature
                                from oracle.models import Feature
                                feature, _ = Feature.objects.get_or_create(
                                    name=contrib['name'],
                                    defaults={
                                        'category': contrib['category'],
                                        'description': contrib.get('explanation', '')
                                    }
                                )

                                FeatureContribution.objects.create(
                                    decision=decision,
                                    feature=feature,
                                    raw_value=contrib['raw_value'],
                                    direction=contrib['direction'],
                                    strength=contrib['strength'],
                                    weight=contrib['weight'],
                                    contribution=contrib['contribution'],
                                    explanation=contrib['explanation']
                                )

                            decisions_created += 1

                        except Exception as e:
                            error_msg = f"Error analyzing {symbol.symbol} {market_type.name} {timeframe.name}: {str(e)}"
                            logger.error(error_msg)
                            errors.append(error_msg)

            except Exception as e:
                error_msg = f"Error analyzing {symbol.symbol}: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        # Update analysis run
        analysis_run.status = 'COMPLETED' if not errors else 'FAILED'
        analysis_run.completed_at = timezone.now()
        analysis_run.duration_seconds = (
            analysis_run.completed_at - analysis_run.started_at
        ).total_seconds()
        analysis_run.decisions_created = decisions_created
        analysis_run.errors = errors
        analysis_run.save()

        logger.info(f"Analysis {run_id} completed: {decisions_created} decisions created")

        return {
            'run_id': run_id,
            'status': analysis_run.status,
            'decisions_created': decisions_created,
            'errors': errors
        }

    except Exception as e:
        logger.error(f"Fatal error in analysis {run_id}: {str(e)}")
        if 'analysis_run' in locals():
            analysis_run.status = 'FAILED'
            analysis_run.completed_at = timezone.now()
            analysis_run.errors = [str(e)]
            analysis_run.save()
        raise self.retry(exc=e, countdown=60)


def _fetch_macro_data(provider: MacroDataProvider) -> dict:
    """Fetch all macro indicators"""
    try:
        indicators = provider.fetch_all_macro_indicators()
        return indicators
    except Exception as e:
        logger.error(f"Error fetching macro data: {e}")
        return {}


def _fetch_derivatives_data(provider: BinanceProvider, symbol: str) -> dict:
    """Fetch derivatives-specific data (funding, OI, etc.)"""
    try:
        funding = provider.fetch_funding_rate(symbol)
        oi = provider.fetch_open_interest(symbol)
        liquidations = provider.fetch_liquidations(symbol)

        # Convert to dataframe format
        import pandas as pd

        funding_df = pd.DataFrame([{
            'timestamp': funding['next_funding_time'] or datetime.now(),
            'rate': funding['rate']
        }])

        oi_df = pd.DataFrame([{
            'timestamp': oi['timestamp'],
            'value': oi['open_interest']
        }])

        return {
            'funding_rate': funding_df,
            'open_interest': oi_df,
            'mark_price': funding.get('mark_price'),
            'index_price': funding.get('index_price'),
            'liquidations': {
                'long': liquidations.get('liquidations_long', 0),
                'short': liquidations.get('liquidations_short', 0),
                'total': liquidations.get('liquidations_long', 0) + liquidations.get('liquidations_short', 0)
            }
        }
    except Exception as e:
        logger.error(f"Error fetching derivatives data: {e}")
        return {}


@shared_task
def fetch_market_data():
    """
    Periodic task to fetch and store market data for all active symbols
    Run every 1 hour
    """
    logger.info("Starting market data fetch task")

    symbols = Symbol.objects.filter(is_active=True)
    timeframes = Timeframe.objects.all()

    crypto_provider = BinanceProvider()
    traditional_provider = YFinanceProvider()

    for symbol in symbols:
        try:
            # Determine provider
            if symbol.asset_type == 'CRYPTO':
                provider = crypto_provider
                provider_symbol = f"{symbol.base_currency}/{symbol.quote_currency}"
            else:
                provider = traditional_provider
                provider_symbol = symbol.symbol

            for timeframe in timeframes:
                try:
                    # Fetch recent data
                    df = provider.fetch_ohlcv(
                        symbol=provider_symbol,
                        timeframe=timeframe.name,
                        limit=100
                    )

                    if df.empty:
                        continue

                    # Determine market type
                    market_type = MarketType.objects.get(name='SPOT')

                    # Store data
                    for _, row in df.iterrows():
                        MarketData.objects.update_or_create(
                            symbol=symbol,
                            market_type=market_type,
                            timeframe=timeframe,
                            timestamp=row['timestamp'],
                            defaults={
                                'open': row['open'],
                                'high': row['high'],
                                'low': row['low'],
                                'close': row['close'],
                                'volume': row['volume']
                            }
                        )

                except Exception as e:
                    logger.error(f"Error fetching {symbol.symbol} {timeframe.name}: {e}")

        except Exception as e:
            logger.error(f"Error fetching {symbol.symbol}: {e}")

    logger.info("Market data fetch task completed")


@shared_task
def fetch_derivatives_data():
    """
    Periodic task to fetch derivatives data (funding, OI)
    Run every 15 minutes
    """
    logger.info("Starting derivatives data fetch task")

    symbols = Symbol.objects.filter(asset_type='CRYPTO', is_active=True)
    provider = BinanceProvider()

    for symbol in symbols:
        try:
            provider_symbol = f"{symbol.base_currency}/{symbol.quote_currency}"

            # Fetch funding rate
            funding = provider.fetch_funding_rate(provider_symbol)

            # Fetch open interest
            oi = provider.fetch_open_interest(provider_symbol)

            # Store derivatives data
            DerivativesData.objects.create(
                symbol=symbol,
                timestamp=timezone.now(),
                funding_rate=funding.get('rate'),
                next_funding_time=funding.get('next_funding_time'),
                open_interest=oi.get('open_interest'),
                mark_price=funding.get('mark_price'),
                index_price=funding.get('index_price'),
                basis=((funding.get('mark_price', 0) - funding.get('index_price', 1)) /
                      funding.get('index_price', 1) * 100) if funding.get('index_price') else None
            )

        except Exception as e:
            logger.error(f"Error fetching derivatives data for {symbol.symbol}: {e}")

    logger.info("Derivatives data fetch task completed")


@shared_task
def fetch_macro_data():
    """
    Periodic task to fetch macro indicators
    Run every 1 hour
    """
    logger.info("Starting macro data fetch task")

    provider = MacroDataProvider()
    indicators = provider.fetch_all_macro_indicators()

    for indicator_name, df in indicators.items():
        try:
            if df.empty:
                continue

            # Get latest data point
            latest = df.iloc[-1]

            MacroData.objects.create(
                indicator_name=indicator_name,
                timestamp=latest['timestamp'],
                value=latest['close']
            )

        except Exception as e:
            logger.error(f"Error storing macro data for {indicator_name}: {e}")

    logger.info("Macro data fetch task completed")


@shared_task
def cleanup_old_data():
    """
    Cleanup task to remove old data
    Keep last 90 days of market data, 30 days of decisions
    Run daily
    """
    logger.info("Starting cleanup task")

    cutoff_market_data = timezone.now() - timedelta(days=90)
    cutoff_decisions = timezone.now() - timedelta(days=30)

    # Delete old market data
    deleted_market = MarketData.objects.filter(timestamp__lt=cutoff_market_data).delete()
    logger.info(f"Deleted {deleted_market[0]} old market data records")

    # Delete old decisions (but keep feature contributions via cascade)
    deleted_decisions = Decision.objects.filter(created_at__lt=cutoff_decisions).delete()
    logger.info(f"Deleted {deleted_decisions[0]} old decision records")

    # Delete old analysis runs
    cutoff_runs = timezone.now() - timedelta(days=7)
    deleted_runs = AnalysisRun.objects.filter(created_at__lt=cutoff_runs).delete()
    logger.info(f"Deleted {deleted_runs[0]} old analysis run records")

    logger.info("Cleanup task completed")
