"""
Macro economic and intermarket features
DXY, VIX, Yields, Gold/Silver ratio, Copper/Gold, Miners/Gold, etc.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base import BaseFeature, FeatureResult, registry


def _has_macro_series(context: Optional[Dict], key: str, min_rows: int = 5) -> bool:
    if not context or 'macro' not in context:
        return False
    series = context['macro'].get(key)
    if series is None or series.empty:
        return False
    return len(series) >= min_rows


class DXYFeature(BaseFeature):
    """US Dollar Index - inverse correlation with gold and crypto"""
    category = 'MACRO'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        # DXY data should be in context['macro']['DXY']
        if not _has_macro_series(context, 'DXY', min_rows=50):
            return FeatureResult(
                name='DXY',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="DXY data not available"
            )

        dxy_data = context['macro']['DXY']

        # Check if dataframe has enough data
        if dxy_data.empty or len(dxy_data) < 5:
            return FeatureResult(
                name='DXY',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Insufficient DXY data"
            )

        current_dxy = dxy_data['close'].iloc[-1]
        lookback_idx = min(5, len(dxy_data) - 1)
        dxy_change_pct = ((current_dxy - dxy_data['close'].iloc[-lookback_idx]) / dxy_data['close'].iloc[-lookback_idx]) * 100

        # Calculate DXY trend
        dxy_sma_20 = dxy_data['close'].rolling(20).mean().iloc[-1]
        dxy_sma_50 = dxy_data['close'].rolling(50).mean().iloc[-1]

        # Strong DXY = bearish for gold/crypto
        # Weak DXY = bullish for gold/crypto
        if dxy_change_pct > 1.0 and current_dxy > dxy_sma_20:
            direction = -1  # Bearish for gold/crypto
            strength = min(1.0, abs(dxy_change_pct) / 3.0)
            explanation = f"DXY rising {dxy_change_pct:.2f}% - bearish for gold/crypto"
        elif dxy_change_pct < -1.0 and current_dxy < dxy_sma_20:
            direction = 1  # Bullish for gold/crypto
            strength = min(1.0, abs(dxy_change_pct) / 3.0)
            explanation = f"DXY falling {dxy_change_pct:.2f}% - bullish for gold/crypto"
        else:
            direction = 0
            strength = 0.3
            explanation = f"DXY stable at {current_dxy:.2f}"

        return FeatureResult(
            name='DXY',
            category=self.category,
            raw_value=float(current_dxy),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'change_pct': float(dxy_change_pct)}
        )


class VIXFeature(BaseFeature):
    """VIX - fear gauge, affects risk assets"""
    category = 'MACRO'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not _has_macro_series(context, 'VIX'):
            return FeatureResult(
                name='VIX',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="VIX data not available"
            )

        vix_data = context['macro']['VIX']

        # Check if dataframe has enough data
        if vix_data.empty or len(vix_data) < 5:
            return FeatureResult(
                name='VIX',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Insufficient VIX data"
            )

        current_vix = vix_data['close'].iloc[-1]
        lookback_idx = min(5, len(vix_data) - 1)
        vix_change_pct = ((current_vix - vix_data['close'].iloc[-lookback_idx]) / vix_data['close'].iloc[-lookback_idx]) * 100

        # VIX thresholds
        # < 15: low fear, bullish
        # 15-25: normal
        # > 25: elevated fear, bearish for risk assets
        # > 35: extreme fear, potential bottom

        if current_vix > 35:
            # Extreme fear - contrarian bullish
            direction = 1
            strength = min(1.0, (current_vix - 35) / 30)
            explanation = f"VIX at {current_vix:.2f} - extreme fear, contrarian bullish"
        elif current_vix > 25:
            # Elevated fear - bearish
            direction = -1
            strength = (current_vix - 25) / 15
            explanation = f"VIX at {current_vix:.2f} - elevated fear, bearish"
        elif current_vix < 15:
            # Low fear - complacency, potential reversal
            direction = -1
            strength = 0.3
            explanation = f"VIX at {current_vix:.2f} - complacency, caution"
        else:
            # Normal range
            direction = 0
            strength = 0.2
            explanation = f"VIX at {current_vix:.2f} - normal levels"

        return FeatureResult(
            name='VIX',
            category=self.category,
            raw_value=float(current_vix),
            direction=direction,
            strength=strength,
            explanation=explanation
        )


class RealYieldsFeature(BaseFeature):
    """Real yields (10Y - inflation expectations) - key driver for gold"""
    category = 'MACRO'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'macro' not in context:
            return FeatureResult(
                name='RealYields',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Real yields data not available"
            )

        # Try to get real yields directly, or calculate from nominal - inflation
        if _has_macro_series(context, 'REAL_YIELDS', min_rows=10):
            real_yields_data = context['macro']['REAL_YIELDS']
            current_real_yield = real_yields_data['close'].iloc[-1]
        elif _has_macro_series(context, 'TNX', min_rows=1) and _has_macro_series(context, 'INFLATION_EXP', min_rows=1):
            nominal_yield = context['macro']['TNX']['close'].iloc[-1]
            inflation_exp = context['macro']['INFLATION_EXP']['close'].iloc[-1]
            current_real_yield = nominal_yield - inflation_exp
        else:
            return FeatureResult(
                name='RealYields',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Insufficient data for real yields"
            )

        # Get historical context
        if _has_macro_series(context, 'REAL_YIELDS', min_rows=10):
            prev_real_yield = real_yields_data['close'].iloc[-10]
            change = current_real_yield - prev_real_yield
        else:
            change = 0

        # Rising real yields = bearish for gold
        # Falling real yields = bullish for gold
        if change > 0.1:
            direction = -1
            strength = min(1.0, abs(change) / 0.5)
            explanation = f"Real yields rising to {current_real_yield:.2f}% - bearish for gold"
        elif change < -0.1:
            direction = 1
            strength = min(1.0, abs(change) / 0.5)
            explanation = f"Real yields falling to {current_real_yield:.2f}% - bullish for gold"
        else:
            direction = 0
            strength = 0.3
            explanation = f"Real yields stable at {current_real_yield:.2f}%"

        return FeatureResult(
            name='RealYields',
            category=self.category,
            raw_value=float(current_real_yield),
            direction=direction,
            strength=strength,
            explanation=explanation
        )


class GoldSilverRatioFeature(BaseFeature):
    """Gold/Silver ratio - intermarket relationship"""
    category = 'INTERMARKET'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'intermarket' not in context or 'XAGUSD' not in context['intermarket']:
            return FeatureResult(
                name='GoldSilverRatio',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Silver data not available"
            )

        # Get gold and silver prices
        gold_price = df['close'].iloc[-1]  # Current symbol is gold
        silver_data = context['intermarket']['XAGUSD']
        silver_price = silver_data['close'].iloc[-1]

        ratio = gold_price / silver_price
        ratio_sma_50 = (context['intermarket'].get('GOLD_SILVER_RATIO_SMA50', ratio))

        # Historical range: typically 60-80
        # High ratio (>80): silver undervalued vs gold - potential silver outperformance
        # Low ratio (<60): gold undervalued vs silver

        if ratio > 85:
            direction = -1  # High ratio - risk of mean reversion (bearish for gold vs silver)
            strength = min(1.0, (ratio - 85) / 20)
            explanation = f"Gold/Silver ratio high at {ratio:.1f} - potential reversion"
        elif ratio < 60:
            direction = 1  # Low ratio - gold may outperform
            strength = min(1.0, (60 - ratio) / 20)
            explanation = f"Gold/Silver ratio low at {ratio:.1f} - gold may outperform"
        elif ratio > ratio_sma_50 * 1.05:
            direction = -1
            strength = 0.4
            explanation = f"Gold/Silver ratio above MA50 at {ratio:.1f}"
        elif ratio < ratio_sma_50 * 0.95:
            direction = 1
            strength = 0.4
            explanation = f"Gold/Silver ratio below MA50 at {ratio:.1f}"
        else:
            direction = 0
            strength = 0.2
            explanation = f"Gold/Silver ratio normal at {ratio:.1f}"

        return FeatureResult(
            name='GoldSilverRatio',
            category=self.category,
            raw_value=float(ratio),
            direction=direction,
            strength=strength,
            explanation=explanation
        )


class CopperGoldRatioFeature(BaseFeature):
    """Copper/Gold ratio - economic growth proxy"""
    category = 'INTERMARKET'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'intermarket' not in context or 'COPPER' not in context['intermarket']:
            return FeatureResult(
                name='CopperGoldRatio',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Copper data not available"
            )

        copper_data = context['intermarket']['COPPER']
        copper_price = copper_data['close'].iloc[-1]
        gold_price = df['close'].iloc[-1]

        ratio = copper_price / gold_price
        ratio_change_pct = ((ratio - context['intermarket'].get('COPPER_GOLD_PREV', ratio)) /
                           context['intermarket'].get('COPPER_GOLD_PREV', ratio)) * 100

        # Rising copper/gold = growth expectations, risk-on
        # Falling copper/gold = slowdown fears, risk-off (bullish for gold)

        if ratio_change_pct > 2.0:
            direction = -1  # Risk-on, bearish for gold
            strength = min(1.0, abs(ratio_change_pct) / 5.0)
            explanation = f"Copper/Gold rising {ratio_change_pct:.2f}% - risk-on, bearish for gold"
        elif ratio_change_pct < -2.0:
            direction = 1  # Risk-off, bullish for gold
            strength = min(1.0, abs(ratio_change_pct) / 5.0)
            explanation = f"Copper/Gold falling {ratio_change_pct:.2f}% - risk-off, bullish for gold"
        else:
            direction = 0
            strength = 0.2
            explanation = f"Copper/Gold ratio stable"

        return FeatureResult(
            name='CopperGoldRatio',
            category=self.category,
            raw_value=float(ratio),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'change_pct': float(ratio_change_pct)}
        )


class MinersGoldRatioFeature(BaseFeature):
    """GDX/GLD ratio - gold miners vs gold"""
    category = 'INTERMARKET'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'intermarket' not in context or 'GDX' not in context['intermarket']:
            return FeatureResult(
                name='MinersGoldRatio',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Miners data not available"
            )

        gdx_data = context['intermarket']['GDX']
        gdx_price = gdx_data['close'].iloc[-1]

        # Get GLD price (gold ETF)
        if 'GLD' in context['intermarket']:
            gld_price = context['intermarket']['GLD']['close'].iloc[-1]
        else:
            gld_price = df['close'].iloc[-1] / 10  # Approximate GLD from gold price

        ratio = gdx_price / gld_price
        ratio_sma_20 = context['intermarket'].get('GDX_GLD_SMA20', ratio)

        # Miners typically lead gold
        # Rising ratio = miners outperforming, bullish for gold
        # Falling ratio = miners underperforming, bearish for gold

        if ratio > ratio_sma_20 * 1.05:
            direction = 1
            strength = min(1.0, (ratio / ratio_sma_20 - 1) / 0.1)
            explanation = f"Miners outperforming gold - bullish signal"
        elif ratio < ratio_sma_20 * 0.95:
            direction = -1
            strength = min(1.0, (1 - ratio / ratio_sma_20) / 0.1)
            explanation = f"Miners underperforming gold - bearish signal"
        else:
            direction = 0
            strength = 0.2
            explanation = f"Miners in line with gold"

        return FeatureResult(
            name='MinersGoldRatio',
            category=self.category,
            raw_value=float(ratio),
            direction=direction,
            strength=strength,
            explanation=explanation
        )


class GLDFlowFeature(BaseFeature):
    """GLD holdings change - institutional gold flow proxy"""
    category = 'INTERMARKET'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'intermarket' not in context or 'GLD_HOLDINGS' not in context['intermarket']:
            return FeatureResult(
                name='GLDFlow',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="GLD holdings data not available"
            )

        holdings_data = context['intermarket']['GLD_HOLDINGS']
        current_holdings = holdings_data['value'].iloc[-1]
        prev_holdings = holdings_data['value'].iloc[-5]

        holdings_change_pct = ((current_holdings - prev_holdings) / prev_holdings) * 100

        # Rising holdings = institutional buying, bullish
        # Falling holdings = institutional selling, bearish

        if holdings_change_pct > 0.5:
            direction = 1
            strength = min(1.0, abs(holdings_change_pct) / 2.0)
            explanation = f"GLD holdings rising {holdings_change_pct:.2f}% - institutional buying"
        elif holdings_change_pct < -0.5:
            direction = -1
            strength = min(1.0, abs(holdings_change_pct) / 2.0)
            explanation = f"GLD holdings falling {holdings_change_pct:.2f}% - institutional selling"
        else:
            direction = 0
            strength = 0.2
            explanation = f"GLD holdings stable ({holdings_change_pct:+.2f}%)"

        return FeatureResult(
            name='GLDFlow',
            category=self.category,
            raw_value=float(current_holdings),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'change_pct': float(holdings_change_pct)}
        )


class BTCDominanceFeature(BaseFeature):
    """BTC market dominance - crypto market health indicator"""
    category = 'INTERMARKET'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'intermarket' not in context or 'BTC_DOMINANCE' not in context['intermarket']:
            return FeatureResult(
                name='BTCDominance',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="BTC dominance data not available"
            )

        dominance_data = context['intermarket']['BTC_DOMINANCE']
        current_dominance = dominance_data['value'].iloc[-1]
        prev_dominance = dominance_data['value'].iloc[-5]

        dominance_change = current_dominance - prev_dominance

        # For BTC: rising dominance = bullish
        # For alts: rising dominance = bearish

        is_btc = 'BTC' in symbol.upper()

        if dominance_change > 1.0:
            direction = 1 if is_btc else -1
            strength = min(1.0, abs(dominance_change) / 3.0)
            explanation = f"BTC dominance rising to {current_dominance:.1f}%"
        elif dominance_change < -1.0:
            direction = -1 if is_btc else 1
            strength = min(1.0, abs(dominance_change) / 3.0)
            explanation = f"BTC dominance falling to {current_dominance:.1f}%"
        else:
            direction = 0
            strength = 0.2
            explanation = f"BTC dominance stable at {current_dominance:.1f}%"

        return FeatureResult(
            name='BTCDominance',
            category=self.category,
            raw_value=float(current_dominance),
            direction=direction,
            strength=strength,
            explanation=explanation
        )


class Treasury10YFeature(BaseFeature):
    """10-Year Treasury Yield - key risk-free rate benchmark"""
    category = 'MACRO'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'macro' not in context or 'TNX' not in context['macro']:
            return FeatureResult(
                name='Treasury10Y',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Treasury data not available"
            )

        tnx_data = context['macro']['TNX']

        # Check if dataframe has enough data
        if tnx_data.empty or len(tnx_data) < 5:
            return FeatureResult(
                name='Treasury10Y',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Insufficient Treasury data"
            )

        current_yield = tnx_data['close'].iloc[-1]
        lookback_idx = min(10, len(tnx_data) - 1)
        prev_yield = tnx_data['close'].iloc[-lookback_idx]
        yield_change = current_yield - prev_yield

        # Rising yields = bearish for gold (opportunity cost)
        # Falling yields = bullish for gold
        if yield_change > 0.1:
            direction = -1
            strength = min(1.0, abs(yield_change) / 0.5)
            explanation = f"10Y Treasury rising to {current_yield:.2f}% (+{yield_change:.2f}%) - bearish for gold"
        elif yield_change < -0.1:
            direction = 1
            strength = min(1.0, abs(yield_change) / 0.5)
            explanation = f"10Y Treasury falling to {current_yield:.2f}% ({yield_change:.2f}%) - bullish for gold"
        else:
            direction = 0
            strength = 0.3
            explanation = f"10Y Treasury stable at {current_yield:.2f}%"

        return FeatureResult(
            name='Treasury10Y',
            category=self.category,
            raw_value=float(current_yield),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'change': float(yield_change)}
        )


class GoldOilRatioFeature(BaseFeature):
    """Gold/Oil ratio - flight to safety indicator"""
    category = 'INTERMARKET'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'intermarket' not in context or 'CRUDE' not in context['intermarket']:
            return FeatureResult(
                name='GoldOilRatio',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Oil data not available"
            )

        oil_data = context['intermarket']['CRUDE']

        # Check if dataframe has enough data
        if oil_data.empty or len(oil_data) < 5:
            return FeatureResult(
                name='GoldOilRatio',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Insufficient oil data"
            )

        gold_price = df['close'].iloc[-1]
        oil_price = oil_data['close'].iloc[-1]

        ratio = gold_price / oil_price

        # Get historical ratio for comparison
        lookback_idx = min(20, len(oil_data) - 1)
        gold_past = df['close'].iloc[-lookback_idx]
        oil_past = oil_data['close'].iloc[-lookback_idx]
        ratio_past = gold_past / oil_past

        ratio_change_pct = ((ratio - ratio_past) / ratio_past) * 100

        # Historical average: around 15-25
        # Rising ratio = gold strength or oil weakness (risk-off, bullish for gold)
        # Falling ratio = gold weakness or oil strength (risk-on, bearish for gold)

        if ratio > 30:
            direction = 1  # Extremely high ratio - gold very strong
            strength = min(1.0, (ratio - 30) / 10)
            explanation = f"Gold/Oil ratio high at {ratio:.1f} - strong safe haven demand"
        elif ratio < 15:
            direction = -1  # Low ratio - gold relatively weak
            strength = min(1.0, (15 - ratio) / 5)
            explanation = f"Gold/Oil ratio low at {ratio:.1f} - weak gold demand"
        elif ratio_change_pct > 5:
            direction = 1
            strength = min(1.0, ratio_change_pct / 10)
            explanation = f"Gold/Oil ratio rising ({ratio:.1f}, +{ratio_change_pct:.1f}%) - risk-off"
        elif ratio_change_pct < -5:
            direction = -1
            strength = min(1.0, abs(ratio_change_pct) / 10)
            explanation = f"Gold/Oil ratio falling ({ratio:.1f}, {ratio_change_pct:.1f}%) - risk-on"
        else:
            direction = 0
            strength = 0.2
            explanation = f"Gold/Oil ratio normal at {ratio:.1f}"

        return FeatureResult(
            name='GoldOilRatio',
            category=self.category,
            raw_value=float(ratio),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'change_pct': float(ratio_change_pct)}
        )


class InflationExpectationsFeature(BaseFeature):
    """Inflation expectations - derived from Treasury yields and TIPS"""
    category = 'MACRO'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'macro' not in context:
            return FeatureResult(
                name='InflationExpectations',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Macro data not available"
            )

        # Calculate breakeven inflation from TNX and TIP
        if 'TNX' not in context['macro'] or 'TIP' not in context['macro']:
            return FeatureResult(
                name='InflationExpectations',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Treasury/TIPS data not available"
            )

        tnx_data = context['macro']['TNX']
        tip_data = context['macro']['TIP']

        if tnx_data.empty or tip_data.empty or len(tnx_data) < 10 or len(tip_data) < 10:
            return FeatureResult(
                name='InflationExpectations',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Insufficient data for inflation expectations"
            )

        # Approximate inflation expectations
        # (This is simplified - real implementation would use actual TIPS yield)
        nominal_yield = tnx_data['close'].iloc[-1]

        # TIP ETF price movement as proxy for real yields direction
        tip_price_change = ((tip_data['close'].iloc[-1] - tip_data['close'].iloc[-10]) /
                           tip_data['close'].iloc[-10]) * 100

        # Rising TIP price = falling real yields = bullish for gold
        # Also consider if inflation expectations are rising

        if tip_price_change > 0.5:
            direction = 1  # Falling real yields / rising inflation expectations
            strength = min(1.0, abs(tip_price_change) / 2)
            explanation = f"Inflation expectations rising - bullish for gold"
        elif tip_price_change < -0.5:
            direction = -1  # Rising real yields / falling inflation expectations
            strength = min(1.0, abs(tip_price_change) / 2)
            explanation = f"Inflation expectations falling - bearish for gold"
        else:
            direction = 0
            strength = 0.3
            explanation = f"Inflation expectations stable"

        return FeatureResult(
            name='InflationExpectations',
            category=self.category,
            raw_value=float(nominal_yield),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'tip_price_change': float(tip_price_change)}
        )


# Register macro and intermarket features
registry.register('DXY', DXYFeature)
registry.register('VIX', VIXFeature)
registry.register('RealYields', RealYieldsFeature)
registry.register('Treasury10Y', Treasury10YFeature)
registry.register('InflationExpectations', InflationExpectationsFeature)
registry.register('GoldSilverRatio', GoldSilverRatioFeature)
registry.register('CopperGoldRatio', CopperGoldRatioFeature)
registry.register('GoldOilRatio', GoldOilRatioFeature)
registry.register('MinersGoldRatio', MinersGoldRatioFeature)
registry.register('GLDFlow', GLDFlowFeature)
registry.register('BTCDominance', BTCDominanceFeature)
