"""
Base classes for feature calculation system
All features inherit from BaseFeature and implement calculate() method
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Tuple
from dataclasses import dataclass
import pandas as pd
import numpy as np


@dataclass
class FeatureResult:
    """Result from feature calculation"""
    name: str
    category: str
    raw_value: float
    direction: int  # -1 (bearish), 0 (neutral), 1 (bullish)
    strength: float  # 0..1
    explanation: str
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

        # Validate
        assert self.direction in [-1, 0, 1], "Direction must be -1, 0, or 1"
        assert 0 <= self.strength <= 1, "Strength must be between 0 and 1"


class BaseFeature(ABC):
    """
    Base class for all features

    Subclasses must implement:
    - calculate(): compute the feature and return FeatureResult
    """

    def __init__(self, params: Optional[Dict[str, Any]] = None):
        """
        Initialize feature with parameters

        Args:
            params: Dictionary of feature-specific parameters
        """
        self.params = params or {}
        self.name = self.__class__.__name__
        self.category = 'UNKNOWN'

    @abstractmethod
    def calculate(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        market_type: str,
        context: Optional[Dict[str, Any]] = None
    ) -> FeatureResult:
        """
        Calculate the feature

        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume, timestamp)
            symbol: Symbol being analyzed
            timeframe: Timeframe being analyzed
            market_type: Market type (SPOT, PERPETUAL, etc.)
            context: Additional context data (macro, sentiment, etc.)

        Returns:
            FeatureResult with computed values
        """
        pass

    def get_default_params(self) -> Dict[str, Any]:
        """Return default parameters for this feature"""
        return {}

    def _normalize_to_direction(self, value: float, threshold_positive: float = 0.0,
                                threshold_negative: float = 0.0) -> int:
        """
        Normalize a value to direction (-1, 0, 1)

        Args:
            value: Raw value to normalize
            threshold_positive: Threshold above which direction is 1
            threshold_negative: Threshold below which direction is -1

        Returns:
            -1, 0, or 1
        """
        if value > threshold_positive:
            return 1
        elif value < threshold_negative:
            return -1
        else:
            return 0

    def _calculate_strength(self, value: float, min_val: float, max_val: float,
                           invert: bool = False) -> float:
        """
        Calculate strength (0..1) from a value within a range

        Args:
            value: Current value
            min_val: Minimum value in range
            max_val: Maximum value in range
            invert: If True, invert the strength (1 becomes 0, 0 becomes 1)

        Returns:
            Strength between 0 and 1
        """
        if max_val == min_val:
            return 0.5

        strength = (value - min_val) / (max_val - min_val)
        strength = max(0.0, min(1.0, strength))  # Clamp to [0, 1]

        if invert:
            strength = 1.0 - strength

        return strength

    def _rsi_to_direction_strength(self, rsi: float) -> Tuple[int, float]:
        """
        Convert RSI to direction and strength

        Returns:
            (direction, strength) tuple
        """
        if rsi >= 70:
            # Overbought - bearish
            strength = min(1.0, (rsi - 70) / 30)  # 70-100 maps to 0-1
            return -1, strength
        elif rsi <= 30:
            # Oversold - bullish
            strength = min(1.0, (30 - rsi) / 30)  # 30-0 maps to 0-1
            return 1, strength
        else:
            # Neutral zone - weak signal
            if rsi > 50:
                strength = (rsi - 50) / 20  # 50-70 maps to 0-1
                return -1, strength * 0.3  # Reduced strength in neutral zone
            else:
                strength = (50 - rsi) / 20  # 30-50 maps to 1-0
                return 1, strength * 0.3  # Reduced strength in neutral zone

    def _ma_cross_signal(self, fast_ma: float, slow_ma: float, price: float,
                        prev_fast: float, prev_slow: float) -> Tuple[int, float]:
        """
        Detect moving average crossover and calculate signal strength

        Returns:
            (direction, strength) tuple
        """
        # Check for crossover
        crossed_up = prev_fast <= prev_slow and fast_ma > slow_ma
        crossed_down = prev_fast >= prev_slow and fast_ma < slow_ma

        # Calculate distance between MAs as percentage
        ma_distance_pct = abs(fast_ma - slow_ma) / slow_ma * 100

        # Price position relative to MAs
        above_both = price > fast_ma and price > slow_ma
        below_both = price < fast_ma and price < slow_ma

        if crossed_up or (fast_ma > slow_ma and above_both):
            # Bullish signal
            strength = min(1.0, ma_distance_pct / 5.0)  # 5% distance = max strength
            if crossed_up:
                strength = min(1.0, strength * 1.5)  # Boost on fresh cross
            return 1, strength
        elif crossed_down or (fast_ma < slow_ma and below_both):
            # Bearish signal
            strength = min(1.0, ma_distance_pct / 5.0)
            if crossed_down:
                strength = min(1.0, strength * 1.5)
            return -1, strength
        else:
            # Mixed - price between MAs
            return 0, 0.0

    def _bollinger_position_signal(self, price: float, bb_upper: float,
                                   bb_middle: float, bb_lower: float) -> Tuple[int, float]:
        """
        Calculate signal from Bollinger Band position

        Returns:
            (direction, strength) tuple
        """
        bb_range = bb_upper - bb_lower
        if bb_range == 0:
            return 0, 0.0

        # Calculate %B: (price - lower) / (upper - lower)
        pct_b = (price - bb_lower) / bb_range

        if pct_b > 1.0:
            # Above upper band - bearish (overbought)
            strength = min(1.0, (pct_b - 1.0) * 10)  # 10% above = max strength
            return -1, strength
        elif pct_b < 0.0:
            # Below lower band - bullish (oversold)
            strength = min(1.0, abs(pct_b) * 10)
            return 1, strength
        elif pct_b > 0.8:
            # Near upper band - moderately bearish
            strength = (pct_b - 0.8) / 0.2 * 0.5
            return -1, strength
        elif pct_b < 0.2:
            # Near lower band - moderately bullish
            strength = (0.2 - pct_b) / 0.2 * 0.5
            return 1, strength
        else:
            # Middle zone - neutral
            return 0, 0.0

    def _volume_signal(self, current_volume: float, avg_volume: float,
                      price_change_pct: float) -> Tuple[int, float]:
        """
        Calculate signal from volume analysis

        Returns:
            (direction, strength) tuple
        """
        if avg_volume == 0:
            return 0, 0.0

        volume_ratio = current_volume / avg_volume

        # Volume spike (>2x average)
        if volume_ratio > 2.0:
            strength = min(1.0, (volume_ratio - 2.0) / 3.0)  # 5x volume = max strength

            # High volume + price up = bullish
            if price_change_pct > 1.0:
                return 1, strength
            # High volume + price down = bearish
            elif price_change_pct < -1.0:
                return -1, strength
            else:
                # High volume, no clear direction
                return 0, strength * 0.3

        # Below average volume
        elif volume_ratio < 0.5:
            # Low conviction - reduce any signal
            return 0, 0.1
        else:
            # Normal volume
            return 0, 0.0

    def _adx_trend_strength(self, adx: float, di_plus: float,
                           di_minus: float) -> Tuple[int, float]:
        """
        Calculate trend direction and strength from ADX and DI

        Returns:
            (direction, strength) tuple
        """
        # ADX < 20: weak/no trend
        # ADX 20-40: developing trend
        # ADX > 40: strong trend

        if adx < 18:
            return 0, 0.0  # No trend

        # Determine direction from DI
        if di_plus > di_minus:
            direction = 1  # Bullish
        elif di_minus > di_plus:
            direction = -1  # Bearish
        else:
            return 0, 0.0

        # Calculate strength from ADX
        if adx >= 40:
            strength = min(1.0, (adx - 40) / 40)  # 40-80 maps to 0-1
        else:
            strength = (adx - 18) / 22  # 18-40 maps to 0-1

        # Boost strength if DI spread is large
        di_spread = abs(di_plus - di_minus)
        if di_spread > 20:
            strength = min(1.0, strength * 1.2)

        return direction, strength

    def _macd_signal(self, macd_line: float, signal_line: float,
                    histogram: float, prev_histogram: float) -> Tuple[int, float]:
        """
        Calculate signal from MACD

        Returns:
            (direction, strength) tuple
        """
        # Check for crossover
        crossed_up = prev_histogram <= 0 and histogram > 0
        crossed_down = prev_histogram >= 0 and histogram < 0

        # Calculate strength from histogram magnitude
        strength = min(1.0, abs(histogram) / 5.0)  # Normalize based on typical range

        if crossed_up or (macd_line > signal_line and histogram > 0):
            if crossed_up:
                strength = min(1.0, strength * 1.5)  # Boost on fresh cross
            return 1, strength
        elif crossed_down or (macd_line < signal_line and histogram < 0):
            if crossed_down:
                strength = min(1.0, strength * 1.5)
            return -1, strength
        else:
            return 0, 0.0


class FeatureRegistry:
    """
    Registry for all available features
    Manages feature instantiation and retrieval
    """

    def __init__(self):
        self._features: Dict[str, type] = {}

    def register(self, name: str, feature_class: type):
        """Register a feature class"""
        if not issubclass(feature_class, BaseFeature):
            raise ValueError(f"{feature_class} must inherit from BaseFeature")
        self._features[name] = feature_class

    def get(self, name: str, params: Optional[Dict[str, Any]] = None) -> BaseFeature:
        """Get an instance of a feature"""
        if name not in self._features:
            raise ValueError(f"Feature '{name}' not found in registry")
        return self._features[name](params)

    def list_features(self) -> list:
        """List all registered features"""
        return list(self._features.keys())

    def get_features_by_category(self, category: str) -> list:
        """Get all features in a category"""
        return [
            name for name, cls in self._features.items()
            if hasattr(cls, 'category') and cls.category == category
        ]


# Global registry instance
registry = FeatureRegistry()
