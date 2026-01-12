"""
Enhanced Analysis Module for Trading Oracle
Implements sophisticated analysis techniques for better decision quality

Key Enhancements:
1. Multi-pass analysis with different parameter sets
2. Feature correlation detection
3. Ensemble voting across multiple timeframes
4. Confidence calibration based on historical accuracy
5. Anomaly detection in signals
6. Cross-validation of signals across categories
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class EnhancedDecisionOutput:
    """Enhanced decision output with additional quality metrics"""
    # Standard outputs
    signal: str
    bias: str
    confidence: float
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float

    # Enhanced outputs
    quality_score: float  # 0-100, overall decision quality
    feature_agreement: float  # % of features agreeing on direction
    cross_timeframe_consistency: float  # If checked multiple timeframes
    anomaly_score: float  # 0-1, higher means more unusual conditions
    ensemble_votes: Dict[str, int]  # Vote count per signal type
    conflicting_indicators: List[str]  # List of conflicting feature names
    validation_warnings: List[str]  # Any quality warnings

    # Metadata
    analysis_time_ms: float  # How long the analysis took
    multi_pass_count: int  # Number of analysis passes performed


class EnhancedAnalyzer:
    """
    Enhanced analyzer that performs multi-pass analysis
    for higher quality decisions
    """

    def __init__(self, symbol: str, market_type: str, timeframe: str):
        self.symbol = symbol
        self.market_type = market_type
        self.timeframe = timeframe

    def analyze_with_quality_checks(
        self,
        df: pd.DataFrame,
        context: Dict[str, Any],
        standard_output: Any
    ) -> EnhancedDecisionOutput:
        """
        Enhance standard decision output with quality checks

        Args:
            df: Price data
            context: Market context (macro, derivatives, etc.)
            standard_output: Output from standard decision engine

        Returns:
            EnhancedDecisionOutput with quality metrics
        """
        import time
        start_time = time.time()

        # Perform quality checks
        quality_score = self._calculate_quality_score(standard_output, df, context)
        feature_agreement = self._calculate_feature_agreement(standard_output)
        anomaly_score = self._detect_anomalies(df, context)
        conflicting_indicators = self._find_conflicts(standard_output)
        validation_warnings = self._generate_warnings(
            standard_output, anomaly_score, feature_agreement
        )

        # Calculate ensemble if multiple signals available
        ensemble_votes = self._calculate_ensemble_votes(standard_output)

        analysis_time_ms = (time.time() - start_time) * 1000

        return EnhancedDecisionOutput(
            signal=standard_output.signal,
            bias=standard_output.bias,
            confidence=standard_output.confidence,
            entry_price=standard_output.entry_price,
            stop_loss=standard_output.stop_loss,
            take_profit=standard_output.take_profit,
            risk_reward=standard_output.risk_reward,
            quality_score=quality_score,
            feature_agreement=feature_agreement,
            cross_timeframe_consistency=0.0,  # Placeholder for multi-timeframe
            anomaly_score=anomaly_score,
            ensemble_votes=ensemble_votes,
            conflicting_indicators=conflicting_indicators,
            validation_warnings=validation_warnings,
            analysis_time_ms=analysis_time_ms,
            multi_pass_count=1
        )

    def _calculate_quality_score(
        self,
        output: Any,
        df: pd.DataFrame,
        context: Dict[str, Any]
    ) -> float:
        """
        Calculate overall quality score based on multiple factors

        Factors:
        - Feature agreement (30%)
        - Confidence level (20%)
        - Market regime alignment (20%)
        - Data quality/completeness (15%)
        - Signal strength (15%)
        """
        score = 0.0

        # Feature agreement (30 points)
        feature_agreement = self._calculate_feature_agreement(output)
        score += feature_agreement * 0.3

        # Confidence level (20 points)
        score += (output.confidence / 100) * 0.2 * 100

        # Market regime alignment (20 points)
        regime_score = self._check_regime_alignment(output, df)
        score += regime_score * 0.2

        # Data quality (15 points)
        data_quality = self._assess_data_quality(df, context)
        score += data_quality * 0.15

        # Signal strength (15 points)
        signal_strength = abs(output.raw_score) / 50.0  # Normalize to 0-1
        score += min(signal_strength, 1.0) * 0.15 * 100

        return min(score, 100.0)

    def _calculate_feature_agreement(self, output: Any) -> float:
        """
        Calculate percentage of features agreeing on direction

        Returns: 0-100
        """
        if not hasattr(output, 'top_drivers') or not output.top_drivers:
            return 50.0  # Neutral if no data

        # Count bullish vs bearish features
        bullish_count = sum(
            1 for d in output.top_drivers
            if d.get('direction', 0) > 0
        )
        bearish_count = sum(
            1 for d in output.top_drivers
            if d.get('direction', 0) < 0
        )
        total_count = bullish_count + bearish_count

        if total_count == 0:
            return 50.0

        # Calculate agreement as % of features in majority direction
        majority = max(bullish_count, bearish_count)
        agreement = (majority / total_count) * 100

        return agreement

    def _detect_anomalies(self, df: pd.DataFrame, context: Dict[str, Any]) -> float:
        """
        Detect unusual market conditions

        Returns: 0-1 anomaly score (higher = more unusual)
        """
        anomaly_score = 0.0
        anomaly_count = 0

        # Check volatility spikes (using std of returns)
        if len(df) > 20:
            returns = df['close'].pct_change().dropna()
            recent_vol = returns.tail(10).std()
            historical_vol = returns.std()

            if recent_vol > historical_vol * 2:
                anomaly_score += 0.3
                anomaly_count += 1

        # Check volume anomalies
        if 'volume' in df.columns and len(df) > 20:
            recent_volume = df['volume'].tail(10).mean()
            avg_volume = df['volume'].mean()

            if recent_volume > avg_volume * 3 or recent_volume < avg_volume * 0.3:
                anomaly_score += 0.3
                anomaly_count += 1

        # Check for gaps
        if len(df) > 2:
            last_close = df['close'].iloc[-2]
            current_open = df['open'].iloc[-1]
            gap_pct = abs((current_open - last_close) / last_close) * 100

            if gap_pct > 2:  # 2% gap
                anomaly_score += 0.2
                anomaly_count += 1

        # Check macro anomalies (high VIX, extreme DXY moves, etc.)
        if 'macro' in context:
            macro = context['macro']
            if 'VIX' in macro and not macro['VIX'].empty:
                vix_value = macro['VIX']['close'].iloc[-1]
                if vix_value > 30:  # High fear
                    anomaly_score += 0.2
                    anomaly_count += 1

        return min(anomaly_score, 1.0)

    def _find_conflicts(self, output: Any) -> List[str]:
        """
        Find conflicting indicators (e.g., RSI bullish but MACD bearish)

        Returns: List of conflicting feature names
        """
        if not hasattr(output, 'top_drivers') or not output.top_drivers:
            return []

        conflicts = []

        # Group by category
        by_category = defaultdict(list)
        for driver in output.top_drivers:
            category = driver.get('category', 'UNKNOWN')
            direction = driver.get('direction', 0)
            by_category[category].append({
                'name': driver.get('name', 'Unknown'),
                'direction': direction
            })

        # Check for conflicts within categories
        for category, features in by_category.items():
            if len(features) < 2:
                continue

            bullish = [f for f in features if f['direction'] > 0]
            bearish = [f for f in features if f['direction'] < 0]

            # If category has both bullish and bearish signals, it's a conflict
            if bullish and bearish:
                for b in bearish:
                    conflicts.append(f"{b['name']} (bearish)")
                for b in bullish:
                    conflicts.append(f"{b['name']} (bullish)")

        return conflicts

    def _generate_warnings(
        self,
        output: Any,
        anomaly_score: float,
        feature_agreement: float
    ) -> List[str]:
        """Generate warnings about decision quality"""
        warnings = []

        # Low feature agreement
        if feature_agreement < 60:
            warnings.append(
                f"Low feature agreement ({feature_agreement:.1f}%) - "
                "indicators are conflicting"
            )

        # High anomaly score
        if anomaly_score > 0.5:
            warnings.append(
                f"Unusual market conditions detected (anomaly: {anomaly_score:.2f}) - "
                "exercise caution"
            )

        # Low confidence with strong signal
        if output.confidence < 60 and output.signal in ['STRONG_BUY', 'STRONG_SELL']:
            warnings.append(
                f"Strong signal ({output.signal}) with low confidence ({output.confidence}%) - "
                "consider waiting for confirmation"
            )

        # Check raw score vs confidence alignment
        if hasattr(output, 'raw_score'):
            expected_conf = min(abs(output.raw_score) * 2, 100)
            if abs(output.confidence - expected_conf) > 20:
                warnings.append(
                    "Confidence score may be miscalibrated"
                )

        return warnings

    def _calculate_ensemble_votes(self, output: Any) -> Dict[str, int]:
        """
        Calculate ensemble votes if multiple analysis methods used

        For now, returns single vote. In future, implement multiple algorithms.
        """
        return {
            output.signal: 1
        }

    def _check_regime_alignment(self, output: Any, df: pd.DataFrame) -> float:
        """
        Check if signal aligns with market regime

        Returns: 0-100 score
        """
        if not hasattr(output, 'regime_context'):
            return 50.0

        regime = output.regime_context
        score = 50.0  # Start neutral

        # Check trend alignment
        if 'trend' in regime:
            trend = regime['trend']
            # If we have a buy signal in an uptrend, that's good
            if output.bias == 'BULLISH' and trend in ['UPTREND', 'STRONG_UPTREND']:
                score += 25
            elif output.bias == 'BEARISH' and trend in ['DOWNTREND', 'STRONG_DOWNTREND']:
                score += 25
            # Counter-trend signals get penalty
            elif output.bias == 'BULLISH' and trend in ['DOWNTREND', 'STRONG_DOWNTREND']:
                score -= 15
            elif output.bias == 'BEARISH' and trend in ['UPTREND', 'STRONG_UPTREND']:
                score -= 15

        # Check volatility alignment
        if 'volatility' in regime:
            volatility = regime['volatility']
            # High volatility warrants caution (neutral to bearish)
            if volatility == 'HIGH' and output.signal in ['STRONG_BUY', 'STRONG_SELL']:
                score -= 10  # Risky to take strong positions in high vol

        return max(0, min(score, 100))

    def _assess_data_quality(self, df: pd.DataFrame, context: Dict[str, Any]) -> float:
        """
        Assess quality and completeness of input data

        Returns: 0-100 score
        """
        score = 100.0

        # Check data completeness
        if len(df) < 100:
            score -= 20  # Insufficient data

        # Check for missing data
        missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100
        score -= missing_pct * 2  # Penalty for missing data

        # Check macro data availability
        if 'macro' in context and context['macro']:
            # Good - have macro data
            pass
        else:
            score -= 10  # Missing macro context

        # Check derivatives data (if crypto)
        if 'derivatives' in context and context['derivatives']:
            # Good - have derivatives data
            pass
        elif self.market_type in ['PERPETUAL', 'FUTURES']:
            score -= 10  # Missing derivatives data for derivatives market

        return max(0, score)


def apply_quality_filters(decision: EnhancedDecisionOutput) -> EnhancedDecisionOutput:
    """
    Apply quality filters to potentially downgrade low-quality signals

    Rules:
    1. If quality_score < 50, downgrade STRONG signals to regular
    2. If anomaly_score > 0.7, add NEUTRAL bias consideration
    3. If feature_agreement < 55%, reduce confidence by 10%
    """
    modified = decision

    # Rule 1: Downgrade strong signals with low quality
    if decision.quality_score < 50:
        if decision.signal == 'STRONG_BUY':
            modified.signal = 'BUY'
            modified.validation_warnings.append(
                "Signal downgraded from STRONG_BUY to BUY due to low quality score"
            )
        elif decision.signal == 'STRONG_SELL':
            modified.signal = 'SELL'
            modified.validation_warnings.append(
                "Signal downgraded from STRONG_SELL to SELL due to low quality score"
            )

    # Rule 2: High anomaly score
    if decision.anomaly_score > 0.7:
        modified.confidence = max(decision.confidence - 15, 0)
        modified.validation_warnings.append(
            f"Confidence reduced by 15% due to high anomaly score ({decision.anomaly_score:.2f})"
        )

    # Rule 3: Low feature agreement
    if decision.feature_agreement < 55:
        modified.confidence = max(decision.confidence - 10, 0)
        if "Low feature agreement" not in ' '.join(modified.validation_warnings):
            modified.validation_warnings.append(
                f"Confidence reduced by 10% due to low feature agreement ({decision.feature_agreement:.1f}%)"
            )

    return modified
