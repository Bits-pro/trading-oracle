"""
Unit tests for Trading Oracle
"""
from django.test import TestCase
from django.utils import timezone
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

from oracle.models import Symbol, MarketType, Timeframe, Feature, Decision
from oracle.engine import DecisionEngine
from oracle.features.base import BaseFeature, FeatureResult, registry


class SymbolModelTest(TestCase):
    """Test Symbol model"""

    def setUp(self):
        self.symbol = Symbol.objects.create(
            symbol='BTCUSDT',
            name='Bitcoin',
            asset_type='CRYPTO',
            base_currency='BTC',
            quote_currency='USDT'
        )

    def test_symbol_creation(self):
        """Test symbol is created correctly"""
        self.assertEqual(self.symbol.symbol, 'BTCUSDT')
        self.assertEqual(self.symbol.asset_type, 'CRYPTO')
        self.assertTrue(self.symbol.is_active)

    def test_symbol_string_representation(self):
        """Test __str__ method"""
        self.assertEqual(str(self.symbol), 'BTCUSDT (CRYPTO)')


class DecisionModelTest(TestCase):
    """Test Decision model"""

    def setUp(self):
        self.symbol = Symbol.objects.create(
            symbol='BTCUSDT',
            name='Bitcoin',
            asset_type='CRYPTO',
            base_currency='BTC',
            quote_currency='USDT'
        )
        self.market_type = MarketType.objects.create(
            name='SPOT',
            description='Spot Market'
        )
        self.timeframe = Timeframe.objects.create(
            name='1h',
            minutes=60,
            classification='SHORT'
        )

    def test_decision_creation(self):
        """Test decision is created with correct values"""
        decision = Decision.objects.create(
            symbol=self.symbol,
            market_type=self.market_type,
            timeframe=self.timeframe,
            signal='BUY',
            bias='BULLISH',
            confidence=75,
            entry_price=45000,
            stop_loss=44000,
            take_profit=48000,
            risk_reward=3.0
        )

        self.assertEqual(decision.signal, 'BUY')
        self.assertEqual(decision.confidence, 75)
        self.assertIsNotNone(decision.created_at)


class FeatureBaseTest(TestCase):
    """Test base feature functionality"""

    def test_direction_normalization(self):
        """Test _normalize_to_direction helper"""
        feature = MockFeature()

        self.assertEqual(feature._normalize_to_direction(5, 2, -2), 1)
        self.assertEqual(feature._normalize_to_direction(-5, 2, -2), -1)
        self.assertEqual(feature._normalize_to_direction(0, 2, -2), 0)

    def test_strength_calculation(self):
        """Test _calculate_strength helper"""
        feature = MockFeature()

        strength = feature._calculate_strength(50, 0, 100)
        self.assertEqual(strength, 0.5)

        strength = feature._calculate_strength(100, 0, 100)
        self.assertEqual(strength, 1.0)

        strength = feature._calculate_strength(0, 0, 100)
        self.assertEqual(strength, 0.0)

    def test_rsi_to_direction_strength(self):
        """Test RSI conversion"""
        feature = MockFeature()

        # Overbought
        direction, strength = feature._rsi_to_direction_strength(75)
        self.assertEqual(direction, -1)
        self.assertGreater(strength, 0)

        # Oversold
        direction, strength = feature._rsi_to_direction_strength(25)
        self.assertEqual(direction, 1)
        self.assertGreater(strength, 0)

        # Neutral
        direction, strength = feature._rsi_to_direction_strength(50)
        self.assertLessEqual(strength, 0.3)


class DecisionEngineTest(TestCase):
    """Test decision engine"""

    def setUp(self):
        self.symbol = Symbol.objects.create(
            symbol='BTCUSDT',
            name='Bitcoin',
            asset_type='CRYPTO',
            base_currency='BTC',
            quote_currency='USDT'
        )
        self.market_type = MarketType.objects.create(name='SPOT')
        self.timeframe = Timeframe.objects.create(
            name='1h',
            minutes=60,
            classification='SHORT'
        )

        # Create test data
        self.df = self._create_test_dataframe()

    def _create_test_dataframe(self):
        """Create sample OHLCV data for testing"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')

        # Create trending price data
        base_price = 45000
        trend = np.linspace(0, 5000, 100)
        noise = np.random.normal(0, 200, 100)
        close_prices = base_price + trend + noise

        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices - np.random.uniform(50, 200, 100),
            'high': close_prices + np.random.uniform(50, 300, 100),
            'low': close_prices - np.random.uniform(50, 300, 100),
            'close': close_prices,
            'volume': np.random.uniform(1000000, 5000000, 100)
        })

        return df

    def test_decision_engine_initialization(self):
        """Test engine initializes correctly"""
        engine = DecisionEngine('BTCUSDT', 'SPOT', '1h')

        self.assertEqual(engine.symbol, 'BTCUSDT')
        self.assertEqual(engine.market_type, 'SPOT')
        self.assertEqual(engine.timeframe, '1h')

    def test_decision_generation(self):
        """Test decision generation produces valid output"""
        engine = DecisionEngine('BTCUSDT', 'SPOT', '1h')

        decision = engine.generate_decision(self.df, context={})

        # Check decision has required fields
        self.assertIsNotNone(decision.signal)
        self.assertIsNotNone(decision.bias)
        self.assertIsNotNone(decision.confidence)
        self.assertIn(decision.signal, [
            'STRONG_BUY', 'BUY', 'WEAK_BUY', 'NEUTRAL',
            'WEAK_SELL', 'SELL', 'STRONG_SELL'
        ])
        self.assertIn(decision.bias, ['BULLISH', 'NEUTRAL', 'BEARISH'])
        self.assertGreaterEqual(decision.confidence, 0)
        self.assertLessEqual(decision.confidence, 100)

    def test_trade_parameters_calculation(self):
        """Test entry, stop, target are calculated"""
        engine = DecisionEngine('BTCUSDT', 'SPOT', '1h')
        decision = engine.generate_decision(self.df, context={})

        if decision.signal != 'NEUTRAL':
            self.assertIsNotNone(decision.entry_price)
            self.assertIsNotNone(decision.stop_loss)
            self.assertIsNotNone(decision.take_profit)
            self.assertIsNotNone(decision.risk_reward)

            # Check stops make sense
            if decision.bias == 'BULLISH':
                self.assertLess(decision.stop_loss, decision.entry_price)
                self.assertGreater(decision.take_profit, decision.entry_price)
            elif decision.bias == 'BEARISH':
                self.assertGreater(decision.stop_loss, decision.entry_price)
                self.assertLess(decision.take_profit, decision.entry_price)


class BacktestingTest(TestCase):
    """Test backtesting functionality"""

    def setUp(self):
        from oracle.backtesting import Backtester, TradeOutcome
        self.backtester = Backtester()

        # Create sample outcome
        self.sample_outcome = TradeOutcome(
            decision_id=1,
            symbol='BTCUSDT',
            timeframe='1h',
            signal='BUY',
            confidence=75,
            entry_price=45000,
            stop_loss=44000,
            take_profit=48000,
            max_favorable_excursion=48500,
            max_adverse_excursion=44800,
            exit_price=48000,
            exit_reason='TAKE_PROFIT',
            pnl_percent=6.67,
            pnl_r=3.0,
            duration_hours=12,
            was_profitable=True,
            hit_target=True,
            hit_stop=False
        )

    def test_metrics_calculation(self):
        """Test performance metrics are calculated correctly"""
        # Add sample outcomes
        self.backtester.results = [self.sample_outcome] * 10

        metrics = self.backtester._calculate_metrics()

        self.assertEqual(metrics.total_trades, 10)
        self.assertEqual(metrics.profitable_trades, 10)
        self.assertEqual(metrics.win_rate, 100.0)
        self.assertGreater(metrics.profit_factor, 1.0)


class IntegrationTest(TestCase):
    """Integration tests"""

    def setUp(self):
        # Create complete setup
        self.symbol = Symbol.objects.create(
            symbol='BTCUSDT',
            name='Bitcoin',
            asset_type='CRYPTO',
            base_currency='BTC',
            quote_currency='USDT'
        )
        self.market_type = MarketType.objects.create(name='SPOT')
        self.timeframe = Timeframe.objects.create(
            name='1h',
            minutes=60,
            classification='SHORT'
        )

        # Create features
        Feature.objects.create(
            name='RSI',
            category='TECHNICAL',
            description='Relative Strength Index',
            weight_short=1.2
        )
        Feature.objects.create(
            name='MACD',
            category='TECHNICAL',
            description='MACD',
            weight_short=1.0
        )

    def test_complete_analysis_flow(self):
        """Test complete flow: engine -> decision -> database"""
        # Create test data
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(44000, 46000, 100),
            'high': np.random.uniform(45000, 47000, 100),
            'low': np.random.uniform(43000, 45000, 100),
            'close': np.random.uniform(44000, 46000, 100),
            'volume': np.random.uniform(1000000, 5000000, 100)
        })

        # Run engine
        engine = DecisionEngine('BTCUSDT', 'SPOT', '1h')
        decision_output = engine.generate_decision(df, context={})

        # Save to database
        decision = Decision.objects.create(
            symbol=self.symbol,
            market_type=self.market_type,
            timeframe=self.timeframe,
            signal=decision_output.signal,
            bias=decision_output.bias,
            confidence=decision_output.confidence,
            entry_price=decision_output.entry_price,
            stop_loss=decision_output.stop_loss,
            take_profit=decision_output.take_profit,
            risk_reward=decision_output.risk_reward,
            invalidation_conditions=decision_output.invalidation_conditions,
            top_drivers=[],
            raw_score=decision_output.raw_score,
            regime_context=decision_output.regime_context
        )

        # Verify
        self.assertIsNotNone(decision.id)
        retrieved_decision = Decision.objects.get(id=decision.id)
        self.assertEqual(retrieved_decision.symbol.symbol, 'BTCUSDT')
        self.assertEqual(retrieved_decision.signal, decision_output.signal)


# Mock feature for testing
class MockFeature(BaseFeature):
    category = 'TECHNICAL'

    def calculate(self, df, symbol, timeframe, market_type, context=None):
        return FeatureResult(
            name='MockFeature',
            category=self.category,
            raw_value=50.0,
            direction=1,
            strength=0.5,
            explanation='Mock feature for testing'
        )


class APITest(TestCase):
    """Test API endpoints"""

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user('testuser', 'test@test.com', 'testpass')

        self.symbol = Symbol.objects.create(
            symbol='BTCUSDT',
            name='Bitcoin',
            asset_type='CRYPTO',
            base_currency='BTC',
            quote_currency='USDT'
        )

    def test_symbols_endpoint(self):
        """Test GET /api/symbols/"""
        from django.test import Client
        client = Client()

        response = client.get('/api/symbols/')
        self.assertEqual(response.status_code, 200)

    def test_decisions_endpoint(self):
        """Test GET /api/decisions/"""
        from django.test import Client
        client = Client()

        response = client.get('/api/decisions/')
        self.assertEqual(response.status_code, 200)
