"""
Management command to initialize the trading oracle with default data
"""
from django.core.management.base import BaseCommand
from oracle.models import Symbol, MarketType, Timeframe, Feature


class Command(BaseCommand):
    help = 'Initialize trading oracle with default symbols, market types, and timeframes'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Initializing Trading Oracle...'))

        # Create Market Types
        self.stdout.write('Creating market types...')
        market_types_data = [
            {
                'name': 'SPOT',
                'description': 'Spot Market',
                'supports_funding': False,
                'supports_open_interest': False
            },
            {
                'name': 'PERPETUAL',
                'description': 'Perpetual Futures',
                'supports_funding': True,
                'supports_open_interest': True
            },
            {
                'name': 'FUTURES',
                'description': 'Dated Futures',
                'supports_funding': False,
                'supports_open_interest': True
            },
            {
                'name': 'CFD',
                'description': 'Contract for Difference',
                'supports_funding': False,
                'supports_open_interest': False
            },
        ]

        for data in market_types_data:
            mt, created = MarketType.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created market type: {mt.name}'))
            else:
                self.stdout.write(f'  - Market type already exists: {mt.name}')

        # Create Timeframes
        self.stdout.write('\nCreating timeframes...')
        timeframes_data = [
            {'name': '15m', 'minutes': 15, 'classification': 'SHORT', 'display_order': 1},
            {'name': '1h', 'minutes': 60, 'classification': 'SHORT', 'display_order': 2},
            {'name': '4h', 'minutes': 240, 'classification': 'MEDIUM', 'display_order': 3},
            {'name': '1d', 'minutes': 1440, 'classification': 'LONG', 'display_order': 4},
            {'name': '1w', 'minutes': 10080, 'classification': 'LONG', 'display_order': 5},
        ]

        for data in timeframes_data:
            tf, created = Timeframe.objects.get_or_create(
                name=data['name'],
                defaults=data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created timeframe: {tf.name} ({tf.get_classification_display()})'))
            else:
                self.stdout.write(f'  - Timeframe already exists: {tf.name}')

        # Create Symbols - Gold
        self.stdout.write('\nCreating gold symbols...')
        gold_symbols = [
            {
                'symbol': 'XAUUSD',
                'name': 'Gold Spot',
                'asset_type': 'GOLD',
                'base_currency': 'XAU',
                'quote_currency': 'USD',
                'description': 'Gold spot price from traditional FX/commodity feed'
            },
            {
                'symbol': 'PAXGUSDT',
                'name': 'PAX Gold Token',
                'asset_type': 'GOLD',
                'base_currency': 'PAXG',
                'quote_currency': 'USDT',
                'description': 'Tokenized gold on crypto exchanges'
            },
        ]

        for data in gold_symbols:
            symbol, created = Symbol.objects.get_or_create(
                symbol=data['symbol'],
                defaults=data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created symbol: {symbol.symbol} - {symbol.name}'))
            else:
                self.stdout.write(f'  - Symbol already exists: {symbol.symbol}')

        # Create Symbols - Crypto
        self.stdout.write('\nCreating crypto symbols...')
        crypto_symbols = [
            {'symbol': 'BTCUSDT', 'name': 'Bitcoin', 'base': 'BTC', 'quote': 'USDT'},
            {'symbol': 'ETHUSDT', 'name': 'Ethereum', 'base': 'ETH', 'quote': 'USDT'},
            {'symbol': 'SOLUSDT', 'name': 'Solana', 'base': 'SOL', 'quote': 'USDT'},
            {'symbol': 'BNBUSDT', 'name': 'Binance Coin', 'base': 'BNB', 'quote': 'USDT'},
            {'symbol': 'XRPUSDT', 'name': 'Ripple', 'base': 'XRP', 'quote': 'USDT'},
            {'symbol': 'ADAUSDT', 'name': 'Cardano', 'base': 'ADA', 'quote': 'USDT'},
        ]

        for data in crypto_symbols:
            symbol, created = Symbol.objects.get_or_create(
                symbol=data['symbol'],
                defaults={
                    'name': data['name'],
                    'asset_type': 'CRYPTO',
                    'base_currency': data['base'],
                    'quote_currency': data['quote'],
                    'description': f'{data["name"]} cryptocurrency'
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created symbol: {symbol.symbol} - {symbol.name}'))
            else:
                self.stdout.write(f'  - Symbol already exists: {symbol.symbol}')

        # Create Features
        self.stdout.write('\nCreating features...')

        # Import to trigger feature registration
        from oracle.features import technical, macro, crypto
        from oracle.features.base import registry

        feature_categories = {
            'RSI': 'TECHNICAL',
            'MACD': 'TECHNICAL',
            'Stochastic': 'TECHNICAL',
            'BollingerBands': 'TECHNICAL',
            'BBWidth': 'VOLATILITY',
            'ATR': 'VOLATILITY',
            'ADX': 'TECHNICAL',
            'EMA': 'TECHNICAL',
            'Supertrend': 'TECHNICAL',
            'VWAP': 'VOLUME',
            'VolumeRatio': 'VOLUME',
            'DXY': 'MACRO',
            'VIX': 'MACRO',
            'RealYields': 'MACRO',
            'GoldSilverRatio': 'INTERMARKET',
            'CopperGoldRatio': 'INTERMARKET',
            'MinersGoldRatio': 'INTERMARKET',
            'GLDFlow': 'INTERMARKET',
            'BTCDominance': 'INTERMARKET',
            'FundingRate': 'CRYPTO_DERIVATIVES',
            'OpenInterest': 'CRYPTO_DERIVATIVES',
            'Basis': 'CRYPTO_DERIVATIVES',
            'Liquidations': 'CRYPTO_DERIVATIVES',
            'OIVolumeRatio': 'CRYPTO_DERIVATIVES',
        }

        for feature_name, category in feature_categories.items():
            feature, created = Feature.objects.get_or_create(
                name=feature_name,
                defaults={
                    'category': category,
                    'description': f'{feature_name} indicator',
                    'weight_short': 1.0,
                    'weight_medium': 1.0,
                    'weight_long': 1.0,
                    'applicable_spot': True,
                    'applicable_derivatives': True,
                    'requires_crypto': category in ['CRYPTO_DERIVATIVES', 'CRYPTO_SPOT'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'  ✓ Created feature: {feature.name} ({feature.category})'))
            else:
                self.stdout.write(f'  - Feature already exists: {feature.name}')

        self.stdout.write('\n' + '='*60)
        self.stdout.write(self.style.SUCCESS('✓ Initialization complete!'))
        self.stdout.write('='*60)
        self.stdout.write('\nSummary:')
        self.stdout.write(f'  Market Types: {MarketType.objects.count()}')
        self.stdout.write(f'  Timeframes: {Timeframe.objects.count()}')
        self.stdout.write(f'  Symbols: {Symbol.objects.count()}')
        self.stdout.write(f'  Features: {Feature.objects.count()}')
        self.stdout.write('\nNext steps:')
        self.stdout.write('  1. Run: python manage.py runserver')
        self.stdout.write('  2. Start Celery: celery -A trading_oracle worker -l info')
        self.stdout.write('  3. Start Celery Beat: celery -A trading_oracle beat -l info')
        self.stdout.write('  4. Visit admin: http://localhost:8000/admin/')
        self.stdout.write('  5. Trigger analysis: POST to /api/decisions/analyze/')
