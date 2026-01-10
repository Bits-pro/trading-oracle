"""
Crypto-specific features for derivatives markets
Funding rates, open interest, liquidations, basis/premium
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base import BaseFeature, FeatureResult, registry


class FundingRateFeature(BaseFeature):
    """Perpetual funding rate - shows long/short bias"""
    category = 'CRYPTO_DERIVATIVES'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        # Funding rate data should be in context['derivatives']
        if not context or 'derivatives' not in context or 'funding_rate' not in context['derivatives']:
            return FeatureResult(
                name='FundingRate',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Funding rate data not available"
            )

        funding_data = context['derivatives']['funding_rate']
        current_funding = funding_data['rate'].iloc[-1]

        # Convert to annualized % (assuming 8h funding)
        funding_annual_pct = current_funding * 3 * 365 * 100

        # Calculate percentile (is funding extreme?)
        funding_percentile = (current_funding > funding_data['rate'].iloc[-30:]).sum() / 30

        # Extremely positive funding = too many longs, potential long squeeze (bearish short-term)
        # Extremely negative funding = too many shorts, potential short squeeze (bullish short-term)

        if current_funding > 0.05 and funding_percentile > 0.8:  # 5%+ for 8h, top 20%
            direction = -1  # Bearish - crowded longs
            strength = min(1.0, (current_funding - 0.05) / 0.05)
            explanation = f"Funding extremely positive ({funding_annual_pct:.1f}% annual) - crowded longs, risk of squeeze"
        elif current_funding < -0.02 and funding_percentile < 0.2:  # Negative funding, bottom 20%
            direction = 1  # Bullish - crowded shorts
            strength = min(1.0, abs(current_funding) / 0.05)
            explanation = f"Funding negative ({funding_annual_pct:.1f}% annual) - crowded shorts, risk of squeeze"
        elif current_funding > 0.01:
            direction = -1
            strength = 0.3
            explanation = f"Funding moderately positive ({funding_annual_pct:.1f}% annual)"
        elif current_funding < -0.01:
            direction = 1
            strength = 0.3
            explanation = f"Funding moderately negative ({funding_annual_pct:.1f}% annual)"
        else:
            direction = 0
            strength = 0.1
            explanation = f"Funding neutral ({funding_annual_pct:.1f}% annual)"

        return FeatureResult(
            name='FundingRate',
            category=self.category,
            raw_value=float(current_funding),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'annual_pct': float(funding_annual_pct), 'percentile': float(funding_percentile)}
        )


class OpenInterestFeature(BaseFeature):
    """Open Interest change - leverage buildup indicator"""
    category = 'CRYPTO_DERIVATIVES'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'derivatives' not in context or 'open_interest' not in context['derivatives']:
            return FeatureResult(
                name='OpenInterest',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Open interest data not available"
            )

        oi_data = context['derivatives']['open_interest']
        current_oi = oi_data['value'].iloc[-1]
        prev_oi = oi_data['value'].iloc[-5]

        oi_change_pct = ((current_oi - prev_oi) / prev_oi) * 100

        # Get price change
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-5]
        price_change_pct = ((current_price - prev_price) / prev_price) * 100

        # Interpretation:
        # OI rising + price rising = bullish (new longs entering)
        # OI rising + price falling = bearish (new shorts entering)
        # OI falling + price rising = bullish but weak (shorts covering, not new longs)
        # OI falling + price falling = bearish but weak (longs closing, not new shorts)

        if oi_change_pct > 5.0:  # Significant OI increase
            if price_change_pct > 2.0:
                direction = 1  # Bullish - new longs
                strength = min(1.0, oi_change_pct / 15.0)
                explanation = f"OI rising {oi_change_pct:.1f}% with price - new longs entering"
            elif price_change_pct < -2.0:
                direction = -1  # Bearish - new shorts
                strength = min(1.0, oi_change_pct / 15.0)
                explanation = f"OI rising {oi_change_pct:.1f}% against price - new shorts entering"
            else:
                direction = 0
                strength = 0.4
                explanation = f"OI rising {oi_change_pct:.1f}% - leverage building"

        elif oi_change_pct < -5.0:  # Significant OI decrease
            if price_change_pct > 2.0:
                direction = 1
                strength = 0.5  # Weaker signal
                explanation = f"OI falling {oi_change_pct:.1f}% with price up - short covering"
            elif price_change_pct < -2.0:
                direction = -1
                strength = 0.5
                explanation = f"OI falling {oi_change_pct:.1f}% with price down - long unwinding"
            else:
                direction = 0
                strength = 0.3
                explanation = f"OI falling {oi_change_pct:.1f}% - delevering"
        else:
            direction = 0
            strength = 0.2
            explanation = f"OI stable ({oi_change_pct:+.1f}%)"

        return FeatureResult(
            name='OpenInterest',
            category=self.category,
            raw_value=float(current_oi),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'change_pct': float(oi_change_pct), 'price_change_pct': float(price_change_pct)}
        )


class BasisFeature(BaseFeature):
    """Perpetual premium/discount vs spot"""
    category = 'CRYPTO_DERIVATIVES'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'derivatives' not in context:
            return FeatureResult(
                name='Basis',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Derivatives data not available"
            )

        # Get mark price and index price
        if 'mark_price' in context['derivatives'] and 'index_price' in context['derivatives']:
            mark_price = context['derivatives']['mark_price']
            index_price = context['derivatives']['index_price']
        else:
            return FeatureResult(
                name='Basis',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Mark/index price not available"
            )

        # Calculate basis
        basis_pct = ((mark_price - index_price) / index_price) * 100

        # Large premium = bullish sentiment
        # Discount = bearish sentiment

        if basis_pct > 0.5:
            direction = 1
            strength = min(1.0, basis_pct / 2.0)
            explanation = f"Perp trading at {basis_pct:.2f}% premium - bullish sentiment"
        elif basis_pct < -0.2:
            direction = -1
            strength = min(1.0, abs(basis_pct) / 1.0)
            explanation = f"Perp trading at {basis_pct:.2f}% discount - bearish sentiment"
        else:
            direction = 0
            strength = 0.2
            explanation = f"Basis near parity ({basis_pct:+.2f}%)"

        return FeatureResult(
            name='Basis',
            category=self.category,
            raw_value=float(basis_pct),
            direction=direction,
            strength=strength,
            explanation=explanation
        )


class LiquidationsFeature(BaseFeature):
    """Liquidation spikes - strong short-term reversal signals"""
    category = 'CRYPTO_DERIVATIVES'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'derivatives' not in context or 'liquidations' not in context['derivatives']:
            return FeatureResult(
                name='Liquidations',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Liquidation data not available"
            )

        liq_data = context['derivatives']['liquidations']
        liq_long = liq_data['long'].iloc[-1]  # Recent long liquidations
        liq_short = liq_data['short'].iloc[-1]  # Recent short liquidations

        total_liq = liq_long + liq_short
        avg_liq = liq_data['total'].rolling(20).mean().iloc[-1] if 'total' in liq_data else total_liq

        # Calculate imbalance
        if total_liq > 0:
            long_pct = liq_long / total_liq
            short_pct = liq_short / total_liq
        else:
            long_pct = short_pct = 0.5

        # Large long liquidations = cascading sell pressure, but often marks bottom (contrarian bullish)
        # Large short liquidations = cascading buy pressure, but often marks top (contrarian bearish)

        liq_ratio = total_liq / avg_liq if avg_liq > 0 else 1.0

        if liq_ratio > 3.0:  # Liquidation spike
            if long_pct > 0.7:  # Mostly longs liquidated
                direction = 1  # Contrarian bullish - longs flushed, potential bottom
                strength = min(1.0, (liq_ratio - 3.0) / 5.0)
                explanation = f"Large long liquidations ({liq_ratio:.1f}x avg) - potential bottom"
            elif short_pct > 0.7:  # Mostly shorts liquidated
                direction = -1  # Contrarian bearish - shorts flushed, potential top
                strength = min(1.0, (liq_ratio - 3.0) / 5.0)
                explanation = f"Large short liquidations ({liq_ratio:.1f}x avg) - potential top"
            else:
                direction = 0
                strength = 0.5
                explanation = f"Mixed liquidations ({liq_ratio:.1f}x avg)"
        else:
            direction = 0
            strength = 0.1
            explanation = f"Normal liquidation levels"

        return FeatureResult(
            name='Liquidations',
            category=self.category,
            raw_value=float(total_liq),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'long_pct': float(long_pct), 'short_pct': float(short_pct),
                     'ratio_vs_avg': float(liq_ratio)}
        )


class OIVolumeRatioFeature(BaseFeature):
    """Open Interest / Volume ratio - leverage intensity"""
    category = 'CRYPTO_DERIVATIVES'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        if not context or 'derivatives' not in context or 'open_interest' not in context['derivatives']:
            return FeatureResult(
                name='OIVolumeRatio',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="OI data not available"
            )

        oi_data = context['derivatives']['open_interest']
        current_oi = oi_data['value'].iloc[-1]
        current_volume = df['volume'].iloc[-1]

        if current_volume == 0:
            return FeatureResult(
                name='OIVolumeRatio',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="No volume data"
            )

        oi_vol_ratio = current_oi / current_volume

        # Calculate historical percentile
        historical_ratios = []
        for i in range(max(0, len(oi_data) - 30), len(oi_data)):
            hist_oi = oi_data['value'].iloc[i]
            hist_vol = df['volume'].iloc[i] if i < len(df) else current_volume
            if hist_vol > 0:
                historical_ratios.append(hist_oi / hist_vol)

        if historical_ratios:
            percentile = sum(1 for r in historical_ratios if oi_vol_ratio > r) / len(historical_ratios)
        else:
            percentile = 0.5

        # High OI/Volume = high leverage, potential for sharp moves
        if percentile > 0.8:
            direction = 0  # High leverage is not directional but increases risk
            strength = 0.7
            explanation = f"High OI/Vol ratio - elevated leverage, expect volatility"
        elif percentile < 0.2:
            direction = 0
            strength = 0.3
            explanation = f"Low OI/Vol ratio - low leverage, stable conditions"
        else:
            direction = 0
            strength = 0.2
            explanation = f"Normal OI/Vol ratio"

        return FeatureResult(
            name='OIVolumeRatio',
            category=self.category,
            raw_value=float(oi_vol_ratio),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={'percentile': float(percentile)}
        )


class ExchangeFlowFeature(BaseFeature):
    """Exchange inflow/outflow - sell pressure proxy (Phase 2)"""
    category = 'CRYPTO_SPOT'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        # Placeholder for phase 2
        # Would track net exchange flows (inflow = sell pressure, outflow = accumulation)
        return FeatureResult(
            name='ExchangeFlow',
            category=self.category,
            raw_value=0.0,
            direction=0,
            strength=0.0,
            explanation="Exchange flow data not implemented yet (Phase 2)"
        )


# Register crypto features
registry.register('FundingRate', FundingRateFeature)
registry.register('OpenInterest', OpenInterestFeature)
registry.register('Basis', BasisFeature)
registry.register('Liquidations', LiquidationsFeature)
registry.register('OIVolumeRatio', OIVolumeRatioFeature)
registry.register('ExchangeFlow', ExchangeFlowFeature)
