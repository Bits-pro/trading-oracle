"""
2-Layer Decision Engine

Layer 1: Feature Scoring
- Calculate all features
- Apply weights per timeframe
- Compute raw scores

Layer 2: Rules & Conflict Resolution
- Apply regime filters (ADX, volatility, etc.)
- Resolve conflicts between timeframes
- Apply market-type specific rules
- Generate final signal with confidence
"""
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
import pandas as pd
import numpy as np
from decimal import Decimal

from oracle.features.base import registry, FeatureResult


@dataclass
class DecisionOutput:
    """Final decision output"""
    symbol: str
    market_type: str
    timeframe: str

    # Core decision
    signal: str  # STRONG_BUY, BUY, WEAK_BUY, NEUTRAL, WEAK_SELL, SELL, STRONG_SELL
    bias: str  # BULLISH, NEUTRAL, BEARISH
    confidence: int  # 0-100

    # Trade parameters
    entry_price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    risk_reward: Optional[Decimal]

    # Context
    invalidation_conditions: List[str]
    top_drivers: List[Dict[str, Any]]  # Top 5 feature contributors
    raw_score: float
    regime_context: Dict[str, Any]

    # All feature contributions
    all_features: List[FeatureResult]


class Layer1Scorer:
    """
    Layer 1: Feature Scoring
    Calculates weighted scores from all features
    """

    def __init__(self, symbol: str, market_type: str, timeframe: str):
        self.symbol = symbol
        self.market_type = market_type
        self.timeframe = timeframe
        self.feature_results: List[FeatureResult] = []

    def calculate_features(
        self,
        df: pd.DataFrame,
        context: Optional[Dict] = None,
        feature_list: Optional[List[str]] = None
    ) -> List[FeatureResult]:
        """
        Calculate all applicable features

        Args:
            df: OHLCV dataframe
            context: Additional context (macro, sentiment, derivatives)
            feature_list: Specific features to calculate (None = all applicable)

        Returns:
            List of FeatureResults
        """
        if feature_list is None:
            feature_list = registry.list_features()

        results = []

        for feature_name in feature_list:
            try:
                feature = registry.get(feature_name)

                # Check applicability
                if not self._is_applicable(feature):
                    continue

                result = feature.calculate(
                    df=df,
                    symbol=self.symbol,
                    timeframe=self.timeframe,
                    market_type=self.market_type,
                    context=context
                )

                results.append(result)

            except Exception as e:
                print(f"Error calculating {feature_name}: {e}")
                continue

        self.feature_results = results
        return results

    def _is_applicable(self, feature) -> bool:
        """Check if feature is applicable to current market type"""
        if self.market_type == 'SPOT':
            return getattr(feature, 'applicable_spot', True)
        elif self.market_type in ['PERPETUAL', 'FUTURES']:
            return getattr(feature, 'applicable_derivatives', True)
        return True

    def compute_weighted_score(
        self,
        feature_weights: Optional[Dict[str, float]] = None
    ) -> Tuple[float, List[Dict]]:
        """
        Compute weighted score from all features

        Args:
            feature_weights: Custom weights per feature (overrides defaults)

        Returns:
            (total_score, feature_contributions)
        """
        total_score = 0.0
        contributions = []

        for result in self.feature_results:
            # Get weight for this feature
            weight = self._get_weight(result.name, feature_weights)

            # Calculate contribution
            contribution = weight * result.direction * result.strength
            total_score += contribution

            contributions.append({
                'name': result.name,
                'category': result.category,
                'raw_value': result.raw_value,
                'direction': result.direction,
                'strength': result.strength,
                'weight': weight,
                'contribution': contribution,
                'explanation': result.explanation,
                'metadata': result.metadata
            })

        # Sort by absolute contribution
        contributions.sort(key=lambda x: abs(x['contribution']), reverse=True)

        return total_score, contributions

    def _get_weight(self, feature_name: str, custom_weights: Optional[Dict[str, float]]) -> float:
        """Get weight for feature based on timeframe and custom overrides"""
        # Check custom weights first
        if custom_weights and feature_name in custom_weights:
            return custom_weights[feature_name]

        # Get default weight based on timeframe classification
        # This would normally come from the Feature model in DB
        # For now, use hardcoded defaults

        timeframe_weights = self._get_default_timeframe_weights()
        return timeframe_weights.get(feature_name, 1.0)

    def _get_default_timeframe_weights(self) -> Dict[str, float]:
        """Get default feature weights per timeframe"""
        # Short-term: emphasize oscillators, volume, crypto derivatives
        if self.timeframe in ['15m', '1h', '4h']:
            return {
                'RSI': 1.2,
                'Stochastic': 1.1,
                'MACD': 1.0,
                'BollingerBands': 1.1,
                'VWAP': 1.3,
                'VolumeRatio': 1.2,
                'FundingRate': 1.3,
                'Liquidations': 1.4,
                'ADX': 0.8,
                'EMA_20_50': 0.9,
                'Supertrend': 0.9,
                'DXY': 0.5,
                'VIX': 0.6,
                'RealYields': 0.3,
            }

        # Medium-term: balanced
        elif self.timeframe in ['1d']:
            return {
                'RSI': 1.0,
                'MACD': 1.0,
                'ADX': 1.2,
                'EMA_20_50': 1.3,
                'Supertrend': 1.2,
                'BBWidth': 1.1,
                'DXY': 1.0,
                'VIX': 0.9,
                'RealYields': 1.1,
                'FundingRate': 1.0,
                'OpenInterest': 1.1,
                'GoldSilverRatio': 1.0,
            }

        # Long-term: emphasize macro and structure
        else:  # 1w, 1M
            return {
                'ADX': 1.3,
                'EMA_20_50': 1.5,
                'Supertrend': 1.3,
                'DXY': 1.4,
                'RealYields': 1.5,
                'VIX': 1.0,
                'GoldSilverRatio': 1.2,
                'MinersGoldRatio': 1.2,
                'GLDFlow': 1.1,
                'RSI': 0.7,
                'Stochastic': 0.5,
                'VWAP': 0.3,
                'FundingRate': 0.6,
            }


class Layer2Rules:
    """
    Layer 2: Rules and Conflict Resolution
    Applies regime filters and logic gates
    """

    def __init__(
        self,
        symbol: str,
        market_type: str,
        timeframe: str,
        feature_results: List[FeatureResult],
        contributions: List[Dict]
    ):
        self.symbol = symbol
        self.market_type = market_type
        self.timeframe = timeframe
        self.feature_results = {r.name: r for r in feature_results}
        self.contributions = contributions
        self.regime_context = {}

    def apply_rules(self, raw_score: float) -> Tuple[str, str, int, Dict]:
        """
        Apply rule layer to refine raw score into final signal

        Returns:
            (signal, bias, confidence, regime_context)
        """
        # 1. Analyze market regime
        self._analyze_regime()

        # 2. Apply filters
        filtered_score = self._apply_filters(raw_score)

        # 3. Adjust for conflicts
        adjusted_score = self._resolve_conflicts(filtered_score)

        # 4. Convert to signal and confidence
        signal, bias, confidence = self._score_to_signal(adjusted_score)

        return signal, bias, confidence, self.regime_context

    def _analyze_regime(self):
        """Analyze market regime (trending, ranging, volatile)"""
        # Check ADX
        adx_result = self.feature_results.get('ADX')
        if adx_result:
            adx_value = adx_result.raw_value
            if adx_value < 18:
                self.regime_context['trend'] = 'RANGING'
                self.regime_context['trend_strength'] = 'WEAK'
            elif adx_value < 30:
                self.regime_context['trend'] = 'DEVELOPING'
                self.regime_context['trend_strength'] = 'MODERATE'
            else:
                self.regime_context['trend'] = 'TRENDING'
                self.regime_context['trend_strength'] = 'STRONG'
        else:
            self.regime_context['trend'] = 'UNKNOWN'

        # Check volatility regime
        atr_result = self.feature_results.get('ATR')
        bbwidth_result = self.feature_results.get('BBWidth')

        if atr_result and 'percentile' in atr_result.metadata:
            atr_percentile = atr_result.metadata['percentile']
            if atr_percentile > 0.8:
                self.regime_context['volatility'] = 'HIGH'
            elif atr_percentile < 0.2:
                self.regime_context['volatility'] = 'LOW'
            else:
                self.regime_context['volatility'] = 'NORMAL'

        if bbwidth_result and bbwidth_result.metadata.get('is_squeeze'):
            self.regime_context['squeeze'] = True

    def _apply_filters(self, raw_score: float) -> float:
        """Apply regime-based filters"""
        filtered_score = raw_score

        # Rule 1: If ADX < 18, reduce trend-following confidence
        if self.regime_context.get('trend') == 'RANGING':
            # Reduce score magnitude (mean reversion more reliable than trends)
            filtered_score *= 0.6
            self.regime_context['filter_applied'] = 'ADX_LOW_REDUCED_TREND'

        # Rule 2: If volatility is high, increase caution
        if self.regime_context.get('volatility') == 'HIGH':
            filtered_score *= 0.8
            self.regime_context['filter_applied'] = 'HIGH_VOL_CAUTION'

        # Rule 3: If BB squeeze, wait for breakout confirmation
        if self.regime_context.get('squeeze'):
            # Reduce confidence until breakout
            filtered_score *= 0.5
            self.regime_context['filter_applied'] = 'BB_SQUEEZE_WAIT'

        return filtered_score

    def _resolve_conflicts(self, score: float) -> float:
        """Resolve conflicts between indicators"""
        adjusted_score = score

        # Check for macro conflicts
        # Example: Strong bullish technical but bearish macro
        tech_score = sum(c['contribution'] for c in self.contributions
                        if c['category'] == 'TECHNICAL')
        macro_score = sum(c['contribution'] for c in self.contributions
                         if c['category'] == 'MACRO')

        # If technical and macro disagree strongly
        if abs(tech_score) > 2 and abs(macro_score) > 2:
            if (tech_score > 0 and macro_score < 0) or (tech_score < 0 and macro_score > 0):
                # Reduce confidence when conflict exists
                adjusted_score *= 0.7
                self.regime_context['conflict'] = 'TECH_MACRO_DIVERGENCE'

        # Check derivatives vs spot conflict (for crypto)
        if self.market_type in ['PERPETUAL', 'FUTURES']:
            funding_contrib = next((c['contribution'] for c in self.contributions
                                  if c['name'] == 'FundingRate'), None)
            if funding_contrib:
                # If funding extremely crowded opposite to signal
                if (adjusted_score > 0 and funding_contrib < -0.5) or \
                   (adjusted_score < 0 and funding_contrib > 0.5):
                    # This is actually confirmation (contrarian signal)
                    adjusted_score *= 1.2
                    self.regime_context['funding_confirmation'] = True

        return adjusted_score

    def _score_to_signal(self, score: float) -> Tuple[str, str, int]:
        """
        Convert numeric score to signal, bias, and confidence

        Score ranges (after weighting, typical range -10 to +10):
        > 4.0: STRONG_BUY
        2.0 - 4.0: BUY
        0.5 - 2.0: WEAK_BUY
        -0.5 - 0.5: NEUTRAL
        -2.0 - -0.5: WEAK_SELL
        -4.0 - -2.0: SELL
        < -4.0: STRONG_SELL
        """
        # Normalize score to 0-100 confidence
        # Max expected score is around 10 (with many features at max strength)
        confidence_raw = min(100, abs(score) / 10.0 * 100)
        confidence = int(confidence_raw)

        # Determine signal
        if score > 4.0:
            signal = 'STRONG_BUY'
            bias = 'BULLISH'
        elif score > 2.0:
            signal = 'BUY'
            bias = 'BULLISH'
        elif score > 0.5:
            signal = 'WEAK_BUY'
            bias = 'BULLISH'
        elif score > -0.5:
            signal = 'NEUTRAL'
            bias = 'NEUTRAL'
        elif score > -2.0:
            signal = 'WEAK_SELL'
            bias = 'BEARISH'
        elif score > -4.0:
            signal = 'SELL'
            bias = 'BEARISH'
        else:
            signal = 'STRONG_SELL'
            bias = 'BEARISH'

        # Adjust confidence based on regime
        if self.regime_context.get('trend') == 'RANGING' and signal not in ['NEUTRAL']:
            confidence = int(confidence * 0.7)  # Lower confidence in ranging markets

        if self.regime_context.get('conflict'):
            confidence = int(confidence * 0.8)  # Lower confidence when conflicts exist

        confidence = max(0, min(100, confidence))

        return signal, bias, confidence


class DecisionEngine:
    """
    Main decision engine combining Layer 1 and Layer 2
    """

    def __init__(self, symbol: str, market_type: str, timeframe: str):
        self.symbol = symbol
        self.market_type = market_type
        self.timeframe = timeframe

    def generate_decision(
        self,
        df: pd.DataFrame,
        context: Optional[Dict] = None,
        feature_weights: Optional[Dict[str, float]] = None
    ) -> DecisionOutput:
        """
        Generate complete trading decision

        Args:
            df: OHLCV dataframe
            context: Additional context (macro, derivatives, etc.)
            feature_weights: Custom feature weights

        Returns:
            DecisionOutput with complete decision
        """
        # Layer 1: Feature scoring
        layer1 = Layer1Scorer(self.symbol, self.market_type, self.timeframe)
        feature_results = layer1.calculate_features(df, context)
        raw_score, contributions = layer1.compute_weighted_score(feature_weights)

        # Layer 2: Rules and conflict resolution
        layer2 = Layer2Rules(
            self.symbol,
            self.market_type,
            self.timeframe,
            feature_results,
            contributions
        )
        signal, bias, confidence, regime_context = layer2.apply_rules(raw_score)

        # Calculate trade parameters
        current_price = Decimal(str(df['close'].iloc[-1]))
        entry_price, stop_loss, take_profit, risk_reward = self._calculate_trade_params(
            current_price,
            df,
            signal,
            confidence,
            regime_context
        )

        # Generate invalidation conditions
        invalidation_conditions = self._generate_invalidation_conditions(
            df,
            feature_results,
            signal,
            regime_context
        )

        # Select top drivers (top 5)
        top_drivers = contributions[:5]

        return DecisionOutput(
            symbol=self.symbol,
            market_type=self.market_type,
            timeframe=self.timeframe,
            signal=signal,
            bias=bias,
            confidence=confidence,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            risk_reward=risk_reward,
            invalidation_conditions=invalidation_conditions,
            top_drivers=top_drivers,
            raw_score=raw_score,
            regime_context=regime_context,
            all_features=feature_results
        )

    def _calculate_trade_params(
        self,
        current_price: Decimal,
        df: pd.DataFrame,
        signal: str,
        confidence: int,
        regime_context: Dict
    ) -> Tuple[Decimal, Decimal, Decimal, Decimal]:
        """Calculate entry, stop loss, take profit, and risk/reward"""
        # Use ATR for stop loss calculation
        atr_periods = 14
        high_low = df['high'] - df['low']
        high_close = abs(df['high'] - df['close'].shift())
        low_close = abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        atr = tr.rolling(window=atr_periods).mean().iloc[-1]

        atr_decimal = Decimal(str(atr))

        # Stop loss multiplier based on confidence and regime
        if regime_context.get('volatility') == 'HIGH':
            stop_multiplier = Decimal('2.5')
        else:
            stop_multiplier = Decimal('2.0')

        # Risk/reward ratio based on confidence
        if confidence > 80:
            rr_ratio = Decimal('3.0')
        elif confidence > 60:
            rr_ratio = Decimal('2.5')
        else:
            rr_ratio = Decimal('2.0')

        # Calculate stops based on signal
        if signal in ['STRONG_BUY', 'BUY', 'WEAK_BUY']:
            stop_loss = current_price - (atr_decimal * stop_multiplier)
            risk = current_price - stop_loss
            take_profit = current_price + (risk * rr_ratio)
        elif signal in ['STRONG_SELL', 'SELL', 'WEAK_SELL']:
            stop_loss = current_price + (atr_decimal * stop_multiplier)
            risk = stop_loss - current_price
            take_profit = current_price - (risk * rr_ratio)
        else:
            # Neutral - no trade
            return None, None, None, None

        risk_reward = rr_ratio

        return current_price, stop_loss, take_profit, risk_reward

    def _generate_invalidation_conditions(
        self,
        df: pd.DataFrame,
        feature_results: List[FeatureResult],
        signal: str,
        regime_context: Dict
    ) -> List[str]:
        """Generate conditions that would invalidate this signal"""
        conditions = []

        # Based on signal direction
        if signal in ['STRONG_BUY', 'BUY', 'WEAK_BUY']:
            # Bullish signal invalidations

            # MA break
            ema_result = next((r for r in feature_results if 'EMA' in r.name), None)
            if ema_result and 'ema_slow' in ema_result.metadata:
                ema_slow = ema_result.metadata['ema_slow']
                conditions.append(f"Close below EMA50 ({ema_slow:.2f})")

            # ADX drop
            if regime_context.get('trend_strength') in ['STRONG', 'MODERATE']:
                conditions.append("ADX drops below 18 (trend failure)")

            # DXY flip
            dxy_result = next((r for r in feature_results if r.name == 'DXY'), None)
            if dxy_result and dxy_result.direction == 1:  # DXY was supportive
                conditions.append("DXY breaks above recent high (bearish for gold/crypto)")

        elif signal in ['STRONG_SELL', 'SELL', 'WEAK_SELL']:
            # Bearish signal invalidations

            # MA break
            ema_result = next((r for r in feature_results if 'EMA' in r.name), None)
            if ema_result and 'ema_slow' in ema_result.metadata:
                ema_slow = ema_result.metadata['ema_slow']
                conditions.append(f"Close above EMA50 ({ema_slow:.2f})")

            # ADX drop
            if regime_context.get('trend_strength') in ['STRONG', 'MODERATE']:
                conditions.append("ADX drops below 18 (trend failure)")

            # DXY flip
            dxy_result = next((r for r in feature_results if r.name == 'DXY'), None)
            if dxy_result and dxy_result.direction == -1:  # DXY was supportive
                conditions.append("DXY breaks below recent low (bullish for gold/crypto)")

        # Volatility spike
        if regime_context.get('volatility') != 'HIGH':
            conditions.append("Volatility spike >80th percentile (regime change)")

        return conditions
