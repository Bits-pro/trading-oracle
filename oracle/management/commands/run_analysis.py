"""
Management command to manually run trading analysis
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from oracle.models import Symbol, MarketType, Timeframe, Decision
from oracle.engine import DecisionEngine
from oracle.providers import BinanceProvider, YFinanceProvider, MacroDataProvider
from oracle.providers.news_provider import NewsSentimentProvider
import uuid


def sanitize_for_json(data):
    """
    Recursively convert all boolean and numpy values to JSON-serializable types
    Django JSONField cannot serialize Python bool objects or numpy types
    """
    import numpy as np

    # Handle numpy boolean types (np.bool_, np.True_, np.False_)
    if isinstance(data, (bool, np.bool_)):
        return 'YES' if data else 'NO'
    # Handle numpy numeric types (np.int64, np.float64, etc.)
    elif isinstance(data, (np.integer, np.floating)):
        return float(data)
    elif isinstance(data, dict):
        return {key: sanitize_for_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    else:
        return data


class Command(BaseCommand):
    help = 'Run trading analysis for specified symbols'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            default=['BTCUSDT', 'XAUUSD'],
            help='Symbols to analyze (space-separated)'
        )
        parser.add_argument(
            '--symbol',
            dest='single_symbols',
            nargs='+',
            help='Symbol(s) to analyze (alias for --symbols)'
        )
        parser.add_argument(
            '--timeframes',
            nargs='+',
            default=['1h', '4h', '1d'],
            help='Timeframes to analyze (space-separated)'
        )
        parser.add_argument(
            '--timeframe',
            dest='single_timeframes',
            nargs='+',
            help='Timeframe(s) to analyze (alias for --timeframes)'
        )
        parser.add_argument(
            '--market-types',
            nargs='+',
            default=['SPOT'],
            help='Market types to analyze (space-separated)'
        )
        parser.add_argument(
            '--skip-macro',
            action='store_true',
            help='Skip fetching macro indicators'
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output'
        )

    def handle(self, *args, **options):
        symbols_input = options['single_symbols'] or options['symbols']
        timeframes_input = options['single_timeframes'] or options['timeframes']
        market_types_input = options['market_types']
        verbose = options['verbose']
        skip_macro = options['skip_macro']

        self.stdout.write(self.style.SUCCESS('Starting Trading Analysis'))
        self.stdout.write('='*60)

        # Get database objects
        symbols = Symbol.objects.filter(symbol__in=symbols_input, is_active=True)
        if not symbols.exists():
            self.stdout.write(self.style.ERROR('No active symbols found!'))
            return

        timeframes = Timeframe.objects.filter(name__in=timeframes_input)
        if not timeframes.exists():
            self.stdout.write(self.style.ERROR('No timeframes found!'))
            return

        market_types = MarketType.objects.filter(name__in=market_types_input)
        if not market_types.exists():
            self.stdout.write(self.style.ERROR('No market types found!'))
            return

        # Initialize providers
        self.stdout.write('\nInitializing data providers...')
        crypto_provider = BinanceProvider()
        traditional_provider = YFinanceProvider()
        macro_provider = MacroDataProvider()
        news_provider = NewsSentimentProvider()

        # Fetch macro data
        if skip_macro:
            self.stdout.write('Skipping macro data fetch.')
            macro_context = {}
        else:
            self.stdout.write('Fetching macro data...')
            try:
                macro_context = macro_provider.fetch_all_macro_indicators(log_empty=verbose)
                self.stdout.write(self.style.SUCCESS(f'  ✓ Fetched {len(macro_context)} macro indicators'))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ! Error fetching macro data: {e}'))
                macro_context = {}

        # Fetch intermarket data
        self.stdout.write('Fetching intermarket data...')
        intermarket_context = {}
        intermarket_symbols = ['XAGUSD', 'COPPER', 'CRUDE', 'GLD', 'GDX']
        for sym in intermarket_symbols:
            try:
                df = traditional_provider.fetch_ohlcv(symbol=sym, timeframe='1d', limit=100)
                if not df.empty:
                    intermarket_context[sym] = df
                    self.stdout.write(f'  ✓ Fetched {sym}: {len(df)} rows')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'  ! Error fetching {sym}: {e}'))

        # Fetch news sentiment
        self.stdout.write('Fetching news sentiment...')
        try:
            sentiment_data = news_provider.fetch_sentiment(lookback_hours=24)
            self.stdout.write(self.style.SUCCESS(
                f'  ✓ News sentiment: fear_index={sentiment_data["fear_index"]:.3f}, '
                f'articles={sentiment_data["count"]}'
            ))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'  ! Error fetching news sentiment: {e}'))
            sentiment_data = {'fear_index': 0.0, 'count': 0, 'urgency': 0.0}

        decisions_created = 0
        errors = []

        # Analyze each symbol
        for symbol in symbols:
            self.stdout.write(f'\n{"="*60}')
            self.stdout.write(self.style.SUCCESS(f'Analyzing {symbol.symbol} ({symbol.name})'))
            self.stdout.write(f'{"="*60}')

            # Determine provider
            if symbol.asset_type == 'CRYPTO':
                provider = crypto_provider
                provider_symbol = f"{symbol.base_currency}/{symbol.quote_currency}"
            else:
                provider = traditional_provider
                provider_symbol = symbol.symbol

            for market_type in market_types:
                for timeframe in timeframes:
                    try:
                        self.stdout.write(f'\n  {market_type.name} | {timeframe.name}:')

                        # Fetch market data
                        df = provider.fetch_ohlcv(
                            symbol=provider_symbol,
                            timeframe=timeframe.name,
                            limit=500
                        )

                        if df.empty:
                            self.stdout.write(self.style.WARNING(f'    ⚠ No data available'))
                            continue

                        self.stdout.write(f'    → Fetched {len(df)} candles')

                        # Build context
                        context = {
                            'macro': macro_context,
                            'intermarket': intermarket_context,
                            'sentiment': sentiment_data
                        }

                        # Add derivatives data if applicable
                        if market_type.name in ['PERPETUAL', 'FUTURES'] and symbol.asset_type == 'CRYPTO':
                            try:
                                funding = provider.fetch_funding_rate(provider_symbol)
                                oi = provider.fetch_open_interest(provider_symbol)

                                import pandas as pd
                                context['derivatives'] = {
                                    'funding_rate': pd.DataFrame([{
                                        'timestamp': funding['next_funding_time'] or timezone.now(),
                                        'rate': funding['rate']
                                    }]),
                                    'open_interest': pd.DataFrame([{
                                        'timestamp': oi['timestamp'],
                                        'value': oi['open_interest']
                                    }]),
                                    'mark_price': funding.get('mark_price'),
                                    'index_price': funding.get('index_price'),
                                }
                                self.stdout.write(f'    → Fetched derivatives data')
                            except Exception as e:
                                self.stdout.write(self.style.WARNING(f'    ! Error fetching derivatives: {e}'))

                        # Run decision engine
                        engine = DecisionEngine(
                            symbol=symbol.symbol,
                            market_type=market_type.name,
                            timeframe=timeframe.name
                        )

                        decision_output = engine.generate_decision(df, context)

                        # Save decision (sanitize all JSON fields to convert bools to strings)
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
                            invalidation_conditions=sanitize_for_json(decision_output.invalidation_conditions),
                            top_drivers=sanitize_for_json([d for d in decision_output.top_drivers]),
                            raw_score=decision_output.raw_score,
                            regime_context=sanitize_for_json(decision_output.regime_context)
                        )

                        # Sanitize top drivers for FeatureContribution
                        sanitized_top_drivers = sanitize_for_json([d for d in decision_output.top_drivers])

                        # Create FeatureContribution records for all features
                        for feature_result in decision_output.all_features:
                            # Get or create the Feature record
                            from oracle.models import Feature, FeatureContribution
                            feature, _ = Feature.objects.get_or_create(
                                name=feature_result.name,
                                defaults={
                                    'category': feature_result.category,
                                    'description': feature_result.explanation[:200] if feature_result.explanation else '',
                                }
                            )

                            # Find this feature's contribution from top_drivers
                            contribution_data = next(
                                (d for d in sanitized_top_drivers if d['name'] == feature_result.name),
                                None
                            )

                            if contribution_data:
                                FeatureContribution.objects.create(
                                    decision=decision,
                                    feature=feature,
                                    raw_value=contribution_data['raw_value'],
                                    direction=contribution_data['direction'],
                                    strength=contribution_data['strength'],
                                    weight=contribution_data['weight'],
                                    contribution=contribution_data['contribution'],
                                    explanation=contribution_data['explanation']
                                )

                        decisions_created += 1

                        # Display decision
                        signal_color = self._get_signal_color(decision_output.signal)
                        self.stdout.write(
                            f'    ✓ {signal_color(decision_output.signal)} | '
                            f'{decision_output.bias} | '
                            f'Confidence: {decision_output.confidence}%'
                        )

                        if verbose:
                            self.stdout.write(f'      Entry: {decision_output.entry_price}')
                            self.stdout.write(f'      Stop: {decision_output.stop_loss}')
                            self.stdout.write(f'      Target: {decision_output.take_profit}')
                            self.stdout.write(f'      R:R: {decision_output.risk_reward}')
                            self.stdout.write(f'      Top Drivers:')
                            for driver in decision_output.top_drivers[:3]:
                                self.stdout.write(
                                    f'        - {driver["name"]}: '
                                    f'{driver["contribution"]:.3f} '
                                    f'({driver["explanation"]})'
                                )

                    except Exception as e:
                        error_msg = f'Error analyzing {symbol.symbol} {market_type.name} {timeframe.name}: {str(e)}'
                        self.stdout.write(self.style.ERROR(f'    ✗ {error_msg}'))
                        errors.append(error_msg)

        # Summary
        self.stdout.write(f'\n{"="*60}')
        self.stdout.write(self.style.SUCCESS('Analysis Complete'))
        self.stdout.write(f'{"="*60}')
        self.stdout.write(f'Decisions created: {decisions_created}')
        if errors:
            self.stdout.write(self.style.WARNING(f'Errors: {len(errors)}'))
            if verbose:
                for error in errors:
                    self.stdout.write(self.style.ERROR(f'  - {error}'))

        self.stdout.write(f'\nView decisions at: http://localhost:8000/admin/oracle/decision/')

    def _get_signal_color(self, signal):
        """Get color function for signal"""
        if signal in ['STRONG_BUY', 'BUY']:
            return self.style.SUCCESS
        elif signal in ['WEAK_BUY']:
            return lambda x: self.style.SUCCESS(x)
        elif signal in ['NEUTRAL']:
            return self.style.WARNING
        elif signal in ['WEAK_SELL']:
            return lambda x: self.style.WARNING(x)
        else:  # SELL, STRONG_SELL
            return self.style.ERROR
