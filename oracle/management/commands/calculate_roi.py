"""
Management command to calculate and store ROI metrics for all active symbols
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from oracle.models import Symbol, MarketType, SymbolPerformance, MarketData
from oracle.providers import BinanceProvider, YFinanceProvider
from datetime import timedelta
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Calculate and store ROI metrics for all active symbols'

    def add_arguments(self, parser):
        parser.add_argument(
            '--symbols',
            nargs='+',
            help='Specific symbols to calculate (default: all active)'
        )

    def handle(self, *args, **options):
        symbols_input = options.get('symbols')

        if symbols_input:
            symbols = Symbol.objects.filter(symbol__in=symbols_input, is_active=True)
        else:
            symbols = Symbol.objects.filter(is_active=True)

        if not symbols.exists():
            self.stdout.write(self.style.ERROR('No active symbols found!'))
            return

        self.stdout.write(self.style.SUCCESS(f'Calculating ROI for {symbols.count()} symbols...'))

        # Initialize providers
        crypto_provider = BinanceProvider()
        traditional_provider = YFinanceProvider()

        market_type_spot = MarketType.objects.get_or_create(name='SPOT')[0]

        for symbol in symbols:
            self.stdout.write(f'\n{symbol.symbol} ({symbol.asset_type})...')

            try:
                # Determine provider
                if symbol.asset_type == 'CRYPTO':
                    provider = crypto_provider
                    provider_symbol = f"{symbol.base_currency}/{symbol.quote_currency}"
                else:
                    provider = traditional_provider
                    provider_symbol = symbol.symbol

                # Fetch historical data for ROI calculation
                # Need at least 1 year of data for yearly ROI
                df = provider.fetch_ohlcv(
                    symbol=provider_symbol,
                    timeframe='1h',
                    limit=8760  # 1 year of hourly data
                )

                if df.empty:
                    self.stdout.write(self.style.WARNING(f'  No data available'))
                    continue

                current_price = df['close'].iloc[-1]
                self.stdout.write(f'  Current price: ${current_price:,.2f}')

                # Calculate ROI for different periods
                roi_metrics = self._calculate_roi(df)

                # Calculate 24h metrics
                metrics_24h = self._calculate_24h_metrics(df)

                # Create performance record
                perf = SymbolPerformance.objects.create(
                    symbol=symbol,
                    market_type=market_type_spot,
                    current_price=Decimal(str(current_price)),
                    roi_1h=Decimal(str(roi_metrics['roi_1h'])) if roi_metrics['roi_1h'] is not None else None,
                    roi_1d=Decimal(str(roi_metrics['roi_1d'])) if roi_metrics['roi_1d'] is not None else None,
                    roi_1w=Decimal(str(roi_metrics['roi_1w'])) if roi_metrics['roi_1w'] is not None else None,
                    roi_1m=Decimal(str(roi_metrics['roi_1m'])) if roi_metrics['roi_1m'] is not None else None,
                    roi_1y=Decimal(str(roi_metrics['roi_1y'])) if roi_metrics['roi_1y'] is not None else None,
                    volume_24h=Decimal(str(metrics_24h['volume_24h'])) if metrics_24h['volume_24h'] is not None else None,
                    volatility_24h=Decimal(str(metrics_24h['volatility_24h'])) if metrics_24h['volatility_24h'] is not None else None,
                    high_24h=Decimal(str(metrics_24h['high_24h'])) if metrics_24h['high_24h'] is not None else None,
                    low_24h=Decimal(str(metrics_24h['low_24h'])) if metrics_24h['low_24h'] is not None else None,
                )

                # Display ROI
                self.stdout.write(self.style.SUCCESS(
                    f'  ROI: 1h={roi_metrics["roi_1h"]:+.2f}% | '
                    f'1d={roi_metrics["roi_1d"]:+.2f}% | '
                    f'1w={roi_metrics["roi_1w"]:+.2f}% | '
                    f'1m={roi_metrics["roi_1m"]:+.2f}% | '
                    f'1y={roi_metrics["roi_1y"]:+.2f}%' if roi_metrics['roi_1y'] is not None else f'1y=N/A'
                ))

            except Exception as e:
                self.stdout.write(self.style.ERROR(f'  Error: {e}'))
                logger.exception(f"Error calculating ROI for {symbol.symbol}")

        self.stdout.write(self.style.SUCCESS('\nROI calculation complete!'))

    def _calculate_roi(self, df):
        """Calculate ROI for different time periods"""
        current_price = df['close'].iloc[-1]

        # Define periods in hours
        periods = {
            'roi_1h': 1,
            'roi_1d': 24,
            'roi_1w': 24 * 7,
            'roi_1m': 24 * 30,
            'roi_1y': 24 * 365,
        }

        roi = {}
        for key, hours in periods.items():
            if len(df) > hours:
                past_price = df['close'].iloc[-(hours + 1)]
                roi[key] = ((current_price - past_price) / past_price) * 100
            else:
                roi[key] = None

        return roi

    def _calculate_24h_metrics(self, df):
        """Calculate 24h trading metrics"""
        # Last 24 hours of data
        df_24h = df.tail(24)

        metrics = {
            'volume_24h': df_24h['volume'].sum() if 'volume' in df_24h.columns else None,
            'volatility_24h': df_24h['close'].std() / df_24h['close'].mean() * 100 if len(df_24h) > 1 else None,
            'high_24h': df_24h['high'].max() if 'high' in df_24h.columns else None,
            'low_24h': df_24h['low'].min() if 'low' in df_24h.columns else None,
        }

        return metrics
