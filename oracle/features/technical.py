"""
Technical indicator features
RSI, MACD, Bollinger Bands, ATR, ADX, Stochastic, EMAs, Supertrend, Ichimoku, VWAP, etc.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base import BaseFeature, FeatureResult, registry


class RSIFeature(BaseFeature):
    """Relative Strength Index"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'period': 14}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        period = self.params.get('period', 14)

        # Calculate RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        current_rsi = rsi.iloc[-1]

        direction, strength = self._rsi_to_direction_strength(current_rsi)

        if current_rsi >= 70:
            explanation = f"RSI at {current_rsi:.2f} - overbought, bearish signal"
        elif current_rsi <= 30:
            explanation = f"RSI at {current_rsi:.2f} - oversold, bullish signal"
        else:
            explanation = f"RSI at {current_rsi:.2f} - neutral zone"

        return FeatureResult(
            name='RSI',
            category=self.category,
            raw_value=float(current_rsi),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'period': period}
        )


class MACDFeature(BaseFeature):
    """Moving Average Convergence Divergence"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'fast': 12, 'slow': 26, 'signal': 9}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        fast = self.params.get('fast', 12)
        slow = self.params.get('slow', 26)
        signal_period = self.params.get('signal', 9)

        # Calculate MACD
        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        histogram = macd_line - signal_line

        current_hist = histogram.iloc[-1]
        prev_hist = histogram.iloc[-2] if len(histogram) > 1 else 0

        direction, strength = self._macd_signal(
            macd_line.iloc[-1],
            signal_line.iloc[-1],
            current_hist,
            prev_hist
        )

        crossed_up = prev_hist <= 0 and current_hist > 0
        crossed_down = prev_hist >= 0 and current_hist < 0

        if crossed_up:
            explanation = f"MACD crossed above signal - bullish"
        elif crossed_down:
            explanation = f"MACD crossed below signal - bearish"
        else:
            explanation = f"MACD histogram: {current_hist:.4f}"

        return FeatureResult(
            name='MACD',
            category=self.category,
            raw_value=float(current_hist),
            direction=direction,
            strength=strength,
            explanation=explanation
        )


class StochasticFeature(BaseFeature):
    """Stochastic Oscillator (%K and %D)"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'k_period': 14, 'd_period': 3}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        k_period = self.params.get('k_period', 14)
        d_period = self.params.get('d_period', 3)

        # Calculate %K
        low_min = df['low'].rolling(window=k_period).min()
        high_max = df['high'].rolling(window=k_period).max()
        k = 100 * (df['close'] - low_min) / (high_max - low_min)

        # Calculate %D (smoothed %K)
        d = k.rolling(window=d_period).mean()

        current_k = k.iloc[-1]
        current_d = d.iloc[-1]

        # Similar logic to RSI
        if current_k >= 80:
            direction = -1
            strength = min(1.0, (current_k - 80) / 20)
            explanation = f"Stochastic %K at {current_k:.2f} - overbought"
        elif current_k <= 20:
            direction = 1
            strength = min(1.0, (20 - current_k) / 20)
            explanation = f"Stochastic %K at {current_k:.2f} - oversold"
        else:
            if current_k > current_d:
                direction = 1
                strength = 0.3
                explanation = f"Stochastic %K above %D - mildly bullish"
            else:
                direction = -1
                strength = 0.3
                explanation = f"Stochastic %K below %D - mildly bearish"

        return FeatureResult(
            name='Stochastic',
            category=self.category,
            raw_value=float(current_k),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'k': float(current_k), 'd': float(current_d)}
        )


class BollingerBandsFeature(BaseFeature):
    """Bollinger Bands and %B"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'period': 20, 'std': 2}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        period = self.params.get('period', 20)
        std_dev = self.params.get('std', 2)

        # Calculate Bollinger Bands
        middle = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        current_price = df['close'].iloc[-1]
        current_upper = upper.iloc[-1]
        current_middle = middle.iloc[-1]
        current_lower = lower.iloc[-1]

        direction, strength = self._bollinger_position_signal(
            current_price,
            current_upper,
            current_middle,
            current_lower
        )

        # Calculate %B
        bb_range = current_upper - current_lower
        pct_b = (current_price - current_lower) / bb_range if bb_range > 0 else 0.5

        if pct_b > 1.0:
            explanation = f"Price above upper BB (%B={pct_b:.2f}) - bearish"
        elif pct_b < 0.0:
            explanation = f"Price below lower BB (%B={pct_b:.2f}) - bullish"
        else:
            explanation = f"Price within bands (%B={pct_b:.2f})"

        return FeatureResult(
            name='BollingerBands',
            category=self.category,
            raw_value=float(pct_b),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'upper': float(current_upper), 'middle': float(current_middle),
                     'lower': float(current_lower)}
        )


class BollingerBandWidthFeature(BaseFeature):
    """Bollinger Band Width - volatility regime detection"""
    category = 'VOLATILITY'

    def get_default_params(self) -> Dict[str, Any]:
        return {'period': 20, 'std': 2}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        period = self.params.get('period', 20)
        std_dev = self.params.get('std', 2)

        middle = df['close'].rolling(window=period).mean()
        std = df['close'].rolling(window=period).std()
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)

        # BB Width as percentage of middle
        bb_width = ((upper - lower) / middle) * 100

        current_width = bb_width.iloc[-1]
        avg_width = bb_width.rolling(window=50).mean().iloc[-1]

        # Squeeze detection: width < 80% of average
        is_squeeze = current_width < avg_width * 0.8

        if is_squeeze:
            direction = 0  # Squeeze is neutral, but signals potential breakout
            strength = 0.7
            explanation = f"BB squeeze detected (width: {current_width:.2f}%) - breakout likely"
        elif current_width > avg_width * 1.5:
            direction = 0  # High volatility - trend may be ending
            strength = 0.5
            explanation = f"BB expansion (width: {current_width:.2f}%) - high volatility"
        else:
            direction = 0
            strength = 0.2
            explanation = f"Normal BB width: {current_width:.2f}%"

        return FeatureResult(
            name='BBWidth',
            category=self.category,
            raw_value=float(current_width),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'avg_width': float(avg_width), 'is_squeeze': 'YES' if is_squeeze else 'NO'}
        )


class ATRFeature(BaseFeature):
    """Average True Range"""
    category = 'VOLATILITY'

    def get_default_params(self) -> Dict[str, Any]:
        return {'period': 14}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        period = self.params.get('period', 14)

        # Calculate True Range
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # ATR
        atr = tr.rolling(window=period).mean()
        current_atr = atr.iloc[-1]
        current_price = df['close'].iloc[-1]

        # ATR as percentage of price
        atr_pct = (current_atr / current_price) * 100

        # Compare to historical ATR
        atr_percentile = (atr.iloc[-1] > atr.iloc[-50:]).sum() / 50 if len(atr) >= 50 else 0.5

        if atr_percentile > 0.8:
            explanation = f"ATR at {atr_pct:.2f}% (high volatility) - caution"
            direction = 0
            strength = 0.3  # High volatility = caution
        elif atr_percentile < 0.2:
            explanation = f"ATR at {atr_pct:.2f}% (low volatility) - potential breakout"
            direction = 0
            strength = 0.5
        else:
            explanation = f"ATR at {atr_pct:.2f}% (normal volatility)"
            direction = 0
            strength = 0.2

        return FeatureResult(
            name='ATR',
            category=self.category,
            raw_value=float(current_atr),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'atr_pct': float(atr_pct), 'percentile': float(atr_percentile)}
        )


class ADXFeature(BaseFeature):
    """Average Directional Index with +DI and -DI"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'period': 14}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        period = self.params.get('period', 14)

        # Calculate True Range
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)

        # +DM and -DM
        high_diff = df['high'].diff()
        low_diff = -df['low'].diff()

        plus_dm = high_diff.where((high_diff > low_diff) & (high_diff > 0), 0)
        minus_dm = low_diff.where((low_diff > high_diff) & (low_diff > 0), 0)

        # Smooth with Wilder's smoothing
        atr = tr.ewm(alpha=1/period, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)
        minus_di = 100 * (minus_dm.ewm(alpha=1/period, adjust=False).mean() / atr)

        # ADX
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
        adx = dx.ewm(alpha=1/period, adjust=False).mean()

        current_adx = adx.iloc[-1]
        current_plus_di = plus_di.iloc[-1]
        current_minus_di = minus_di.iloc[-1]

        direction, strength = self._adx_trend_strength(
            current_adx,
            current_plus_di,
            current_minus_di
        )

        if current_adx < 18:
            explanation = f"ADX at {current_adx:.2f} - no clear trend"
        elif current_adx >= 40:
            trend_dir = "up" if current_plus_di > current_minus_di else "down"
            explanation = f"ADX at {current_adx:.2f} - strong {trend_dir}trend"
        else:
            trend_dir = "up" if current_plus_di > current_minus_di else "down"
            explanation = f"ADX at {current_adx:.2f} - developing {trend_dir}trend"

        return FeatureResult(
            name='ADX',
            category=self.category,
            raw_value=float(current_adx),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'plus_di': float(current_plus_di), 'minus_di': float(current_minus_di)}
        )


class EMAFeature(BaseFeature):
    """Exponential Moving Average with trend detection"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'fast': 20, 'slow': 50}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        fast = self.params.get('fast', 20)
        slow = self.params.get('slow', 50)

        ema_fast = df['close'].ewm(span=fast, adjust=False).mean()
        ema_slow = df['close'].ewm(span=slow, adjust=False).mean()

        current_price = df['close'].iloc[-1]
        current_fast = ema_fast.iloc[-1]
        current_slow = ema_slow.iloc[-1]
        prev_fast = ema_fast.iloc[-2] if len(ema_fast) > 1 else current_fast
        prev_slow = ema_slow.iloc[-2] if len(ema_slow) > 1 else current_slow

        direction, strength = self._ma_cross_signal(
            current_fast, current_slow, current_price,
            prev_fast, prev_slow
        )

        # Calculate slope of fast EMA (trend direction)
        ema_slope = (current_fast - ema_fast.iloc[-5]) / ema_fast.iloc[-5] * 100 if len(ema_fast) >= 5 else 0

        if direction == 1:
            explanation = f"EMA{fast} above EMA{slow}, price above both - bullish"
        elif direction == -1:
            explanation = f"EMA{fast} below EMA{slow}, price below both - bearish"
        else:
            explanation = f"Mixed EMA signals"

        return FeatureResult(
            name=f'EMA_{fast}_{slow}',
            category=self.category,
            raw_value=float(current_fast - current_slow),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'ema_fast': float(current_fast), 'ema_slow': float(current_slow),
                     'slope': float(ema_slope)}
        )


class SupertrendFeature(BaseFeature):
    """Supertrend indicator"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'period': 10, 'multiplier': 3}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        period = self.params.get('period', 10)
        multiplier = self.params.get('multiplier', 3)

        # Calculate ATR
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()

        # Basic bands
        hl_avg = (df['high'] + df['low']) / 2
        upper_band = hl_avg + (multiplier * atr)
        lower_band = hl_avg - (multiplier * atr)

        # Supertrend calculation
        supertrend = pd.Series(index=df.index, dtype=float)
        direction = pd.Series(index=df.index, dtype=int)

        for i in range(period, len(df)):
            if df['close'].iloc[i] > upper_band.iloc[i-1]:
                supertrend.iloc[i] = lower_band.iloc[i]
                direction.iloc[i] = 1
            elif df['close'].iloc[i] < lower_band.iloc[i-1]:
                supertrend.iloc[i] = upper_band.iloc[i]
                direction.iloc[i] = -1
            else:
                supertrend.iloc[i] = supertrend.iloc[i-1]
                direction.iloc[i] = direction.iloc[i-1]

        current_direction = int(direction.iloc[-1]) if not pd.isna(direction.iloc[-1]) else 0
        current_supertrend = supertrend.iloc[-1]
        current_price = df['close'].iloc[-1]

        # Distance from supertrend as strength indicator
        distance_pct = abs(current_price - current_supertrend) / current_price * 100
        strength = min(1.0, distance_pct / 5.0)  # 5% distance = max strength

        if current_direction == 1:
            explanation = f"Supertrend bullish - price above {current_supertrend:.2f}"
        elif current_direction == -1:
            explanation = f"Supertrend bearish - price below {current_supertrend:.2f}"
        else:
            explanation = "Supertrend neutral"

        return FeatureResult(
            name='Supertrend',
            category=self.category,
            raw_value=float(current_supertrend),
            direction=current_direction,
            strength=strength,
            explanation=explanation
        )


class VWAPFeature(BaseFeature):
    """Volume Weighted Average Price - intraday fairness price"""
    category = 'VOLUME'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        # Calculate VWAP
        typical_price = (df['high'] + df['low'] + df['close']) / 3
        vwap = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()

        current_price = df['close'].iloc[-1]
        current_vwap = vwap.iloc[-1]

        # Distance from VWAP
        distance_pct = ((current_price - current_vwap) / current_vwap) * 100

        if distance_pct > 1.0:
            direction = -1  # Price above VWAP - potential mean reversion down
            strength = min(1.0, abs(distance_pct) / 3.0)
            explanation = f"Price {distance_pct:.2f}% above VWAP - overbought"
        elif distance_pct < -1.0:
            direction = 1  # Price below VWAP - potential mean reversion up
            strength = min(1.0, abs(distance_pct) / 3.0)
            explanation = f"Price {distance_pct:.2f}% below VWAP - oversold"
        else:
            direction = 0
            strength = 0.2
            explanation = f"Price near VWAP ({distance_pct:+.2f}%)"

        return FeatureResult(
            name='VWAP',
            category=self.category,
            raw_value=float(current_vwap),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'distance_pct': float(distance_pct)}
        )


class VolumeRatioFeature(BaseFeature):
    """Volume ratio vs average"""
    category = 'VOLUME'

    def get_default_params(self) -> Dict[str, Any]:
        return {'period': 20}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        period = self.params.get('period', 20)

        avg_volume = df['volume'].rolling(window=period).mean()
        current_volume = df['volume'].iloc[-1]
        avg_vol = avg_volume.iloc[-1]

        volume_ratio = current_volume / avg_vol if avg_vol > 0 else 1.0

        # Price change
        price_change_pct = ((df['close'].iloc[-1] - df['close'].iloc[-2]) / df['close'].iloc[-2]) * 100

        direction, strength = self._volume_signal(current_volume, avg_vol, price_change_pct)

        if volume_ratio > 2.0:
            explanation = f"Volume spike {volume_ratio:.2f}x average"
        elif volume_ratio < 0.5:
            explanation = f"Low volume {volume_ratio:.2f}x average - low conviction"
        else:
            explanation = f"Normal volume {volume_ratio:.2f}x average"

        return FeatureResult(
            name='VolumeRatio',
            category=self.category,
            raw_value=float(volume_ratio),
            direction=direction,
            strength=strength,
            explanation=explanation
        )


class SMAFeature(BaseFeature):
    """Simple Moving Average"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'period': 20}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        period = self.params.get('period', 20)

        sma = df['close'].rolling(window=period).mean()
        current_price = df['close'].iloc[-1]
        current_sma = sma.iloc[-1]

        # Distance from SMA
        distance_pct = ((current_price - current_sma) / current_sma) * 100

        # Direction based on price position relative to SMA
        if distance_pct > 2:
            direction = 1  # Price well above SMA - bullish
            strength = min(1.0, abs(distance_pct) / 5)
            explanation = f"Price {distance_pct:.2f}% above SMA({period}) - bullish"
        elif distance_pct < -2:
            direction = -1  # Price well below SMA - bearish
            strength = min(1.0, abs(distance_pct) / 5)
            explanation = f"Price {distance_pct:.2f}% below SMA({period}) - bearish"
        else:
            direction = 0
            strength = 0.3
            explanation = f"Price near SMA({period})"

        return FeatureResult(
            name=f'SMA{period}',
            category=self.category,
            raw_value=float(current_sma),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'period': period, 'distance_pct': float(distance_pct)}
        )


class MACrossoverFeature(BaseFeature):
    """Moving Average Crossover (Golden/Death Cross)"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'fast_period': 50, 'slow_period': 200}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        fast_period = self.params.get('fast_period', 50)
        slow_period = self.params.get('slow_period', 200)

        # Need enough data
        if len(df) < slow_period + 1:
            return FeatureResult(
                name=f'MACross{fast_period}_{slow_period}',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Insufficient data for MA crossover"
            )

        fast_ma = df['close'].rolling(window=fast_period).mean()
        slow_ma = df['close'].rolling(window=slow_period).mean()

        current_fast = fast_ma.iloc[-1]
        current_slow = slow_ma.iloc[-1]
        prev_fast = fast_ma.iloc[-2]
        prev_slow = slow_ma.iloc[-2]

        # Calculate distance between MAs
        distance_pct = ((current_fast - current_slow) / current_slow) * 100

        # Detect crossovers
        golden_cross = (prev_fast <= prev_slow) and (current_fast > current_slow)
        death_cross = (prev_fast >= prev_slow) and (current_fast < current_slow)

        if golden_cross:
            direction = 1
            strength = 1.0
            explanation = f"Golden Cross! MA{fast_period} crossed above MA{slow_period} - strong bullish"
        elif death_cross:
            direction = -1
            strength = 1.0
            explanation = f"Death Cross! MA{fast_period} crossed below MA{slow_period} - strong bearish"
        elif current_fast > current_slow:
            direction = 1
            strength = min(1.0, abs(distance_pct) / 5)
            explanation = f"MA{fast_period} above MA{slow_period} ({distance_pct:+.2f}%) - bullish"
        elif current_fast < current_slow:
            direction = -1
            strength = min(1.0, abs(distance_pct) / 5)
            explanation = f"MA{fast_period} below MA{slow_period} ({distance_pct:+.2f}%) - bearish"
        else:
            direction = 0
            strength = 0.2
            explanation = f"MAs aligned"

        return FeatureResult(
            name=f'MACross{fast_period}_{slow_period}',
            category=self.category,
            raw_value=float(distance_pct),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={
                'fast_period': fast_period,
                'slow_period': slow_period,
                'golden_cross': golden_cross,
                'death_cross': death_cross
            }
        )


class PriceMomentumFeature(BaseFeature):
    """Rate of change in price over multiple periods"""
    category = 'TECHNICAL'

    def get_default_params(self) -> Dict[str, Any]:
        return {'periods': [5, 10, 20]}

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        periods = self.params.get('periods', [5, 10, 20])

        current_price = df['close'].iloc[-1]
        momentum_scores = []

        for period in periods:
            if len(df) > period:
                past_price = df['close'].iloc[-(period + 1)]
                change_pct = ((current_price - past_price) / past_price) * 100
                momentum_scores.append(change_pct)

        if not momentum_scores:
            return FeatureResult(
                name='PriceMomentum',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Insufficient data"
            )

        avg_momentum = np.mean(momentum_scores)

        # Direction based on average momentum
        if avg_momentum > 2:
            direction = 1
            strength = min(1.0, abs(avg_momentum) / 10)
            explanation = f"Strong upward momentum (+{avg_momentum:.2f}%)"
        elif avg_momentum < -2:
            direction = -1
            strength = min(1.0, abs(avg_momentum) / 10)
            explanation = f"Strong downward momentum ({avg_momentum:.2f}%)"
        else:
            direction = 0
            strength = 0.3
            explanation = f"Weak momentum ({avg_momentum:+.2f}%)"

        return FeatureResult(
            name='PriceMomentum',
            category=self.category,
            raw_value=float(avg_momentum),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'momentum_scores': [float(x) for x in momentum_scores]}
        )


# Register all technical features
registry.register('RSI', RSIFeature)
registry.register('MACD', MACDFeature)
registry.register('Stochastic', StochasticFeature)
registry.register('BollingerBands', BollingerBandsFeature)
registry.register('BBWidth', BollingerBandWidthFeature)
registry.register('ATR', ATRFeature)
registry.register('ADX', ADXFeature)
registry.register('EMA', EMAFeature)
registry.register('SMA', SMAFeature)
registry.register('MACrossover', MACrossoverFeature)
registry.register('PriceMomentum', PriceMomentumFeature)
registry.register('Supertrend', SupertrendFeature)
registry.register('VWAP', VWAPFeature)
registry.register('VolumeRatio', VolumeRatioFeature)
