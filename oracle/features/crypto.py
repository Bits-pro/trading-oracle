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


class OrderBookImbalanceFeature(BaseFeature):
    """
    Analyzes order book bid/ask imbalance for directional bias

    Inspired by 3Commas' real-time order book analysis.
    Tracks depth imbalance and spread to gauge immediate buying/selling pressure.
    """
    category = 'CRYPTO_DERIVATIVES'

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(params)
        self.depth_levels = params.get('depth_levels', 20) if params else 20

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        """
        Calculate order book imbalance

        Args:
            context: Should contain 'orderbook' with bids/asks data
                    context['orderbook'] = {
                        'bids': [[price, volume], ...],
                        'asks': [[price, volume], ...]
                    }
        """
        # Check if orderbook data available
        if not context or 'orderbook' not in context:
            return FeatureResult(
                name='OrderBookImbalance',
                category=self.category,
                raw_value=0.5,  # Neutral
                direction=0,
                strength=0.0,
                explanation="Order book data not available",
                metadata={'data_available': 'NO'}
            )

        orderbook = context['orderbook']
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])

        if not bids or not asks:
            return FeatureResult(
                name='OrderBookImbalance',
                category=self.category,
                raw_value=0.5,
                direction=0,
                strength=0.0,
                explanation="Order book empty"
            )

        # Calculate bid/ask volume for top N levels
        depth_to_check = min(self.depth_levels, len(bids), len(asks))

        bid_volume = sum([float(bid[1]) for bid in bids[:depth_to_check]])
        ask_volume = sum([float(ask[1]) for ask in asks[:depth_to_check]])

        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            bid_ratio = 0.5
        else:
            bid_ratio = bid_volume / total_volume

        # Calculate spread
        best_bid = float(bids[0][0]) if bids else 0
        best_ask = float(asks[0][0]) if asks else 0

        if best_bid > 0:
            spread_pct = (best_ask - best_bid) / best_bid * 100
        else:
            spread_pct = 0

        # Analyze imbalance
        # bid_ratio > 0.6 = Strong buying pressure (bullish)
        # bid_ratio < 0.4 = Strong selling pressure (bearish)
        # Wide spread = Low liquidity / high volatility (caution)

        if bid_ratio > 0.60:
            # Strong buying pressure
            direction = 1
            strength = min(1.0, (bid_ratio - 0.5) / 0.3)  # Scale 0.5-0.8 to 0-1

            if spread_pct > 0.1:  # Wide spread
                strength *= 0.7  # Reduce strength if liquidity is low
                explanation = f"Order book bullish: {bid_ratio:.1%} bids (⚠️ wide spread: {spread_pct:.3f}%)"
            else:
                explanation = f"Order book bullish: {bid_ratio:.1%} bids, tight spread ({spread_pct:.3f}%)"

        elif bid_ratio < 0.40:
            # Strong selling pressure
            direction = -1
            strength = min(1.0, (0.5 - bid_ratio) / 0.3)  # Scale 0.2-0.5 to 0-1

            if spread_pct > 0.1:
                strength *= 0.7
                explanation = f"Order book bearish: {(1-bid_ratio):.1%} asks (⚠️ wide spread: {spread_pct:.3f}%)"
            else:
                explanation = f"Order book bearish: {(1-bid_ratio):.1%} asks, tight spread ({spread_pct:.3f}%)"

        else:
            # Balanced order book
            direction = 0
            strength = 0.0
            explanation = f"Order book balanced: {bid_ratio:.1%} bids / {(1-bid_ratio):.1%} asks (spread: {spread_pct:.3f}%)"

        # Additional penalty for very wide spreads (low liquidity)
        if spread_pct > 0.5:
            strength *= 0.5
            explanation += " | Very low liquidity"

        return FeatureResult(
            name='OrderBookImbalance',
            category=self.category,
            raw_value=bid_ratio,
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={
                'bid_volume': bid_volume,
                'ask_volume': ask_volume,
                'bid_ratio': bid_ratio,
                'spread_pct': spread_pct,
                'depth_levels': depth_to_check,
                'best_bid': best_bid,
                'best_ask': best_ask
            }
        )


class OrderBookWallFeature(BaseFeature):
    """
    Detects large buy/sell walls in the order book

    Walls can act as support/resistance and indicate whale positioning.
    """
    category = 'CRYPTO_DERIVATIVES'

    def __init__(self, params: Optional[Dict] = None):
        super().__init__(params)
        self.wall_threshold_multiplier = params.get('wall_threshold', 3.0) if params else 3.0

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        """
        Detect buy/sell walls in order book

        A "wall" is an order significantly larger than average depth at that level
        """
        if not context or 'orderbook' not in context:
            return FeatureResult(
                name='OrderBookWall',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Order book data not available"
            )

        orderbook = context['orderbook']
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])

        if len(bids) < 20 or len(asks) < 20:
            return FeatureResult(
                name='OrderBookWall',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Insufficient order book depth"
            )

        # Analyze top 20 levels
        bid_volumes = [float(bid[1]) for bid in bids[:20]]
        ask_volumes = [float(ask[1]) for ask in asks[:20]]

        # Calculate average and identify walls
        avg_bid_volume = np.mean(bid_volumes)
        avg_ask_volume = np.mean(ask_volumes)

        # Find largest orders
        max_bid = max(bid_volumes)
        max_ask = max(ask_volumes)

        # Determine if there are walls
        has_buy_wall = max_bid > (avg_bid_volume * self.wall_threshold_multiplier)
        has_sell_wall = max_ask > (avg_ask_volume * self.wall_threshold_multiplier)

        if has_buy_wall and not has_sell_wall:
            # Buy wall without sell wall = Support / bullish
            direction = 1
            strength = min(1.0, max_bid / (avg_bid_volume * 5))
            explanation = f"Large buy wall detected: {max_bid:.1f} ({max_bid/avg_bid_volume:.1f}x avg) - potential support"

        elif has_sell_wall and not has_buy_wall:
            # Sell wall without buy wall = Resistance / bearish
            direction = -1
            strength = min(1.0, max_ask / (avg_ask_volume * 5))
            explanation = f"Large sell wall detected: {max_ask:.1f} ({max_ask/avg_ask_volume:.1f}x avg) - potential resistance"

        elif has_buy_wall and has_sell_wall:
            # Both walls = Range-bound / neutral
            direction = 0
            strength = 0.0
            explanation = f"Buy & sell walls: range-bound between {max_bid:.1f} and {max_ask:.1f}"

        else:
            # No significant walls
            direction = 0
            strength = 0.0
            explanation = "No significant order book walls detected"

        return FeatureResult(
            name='OrderBookWall',
            category=self.category,
            raw_value=max_bid - max_ask if has_buy_wall or has_sell_wall else 0.0,
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={
                'max_bid': max_bid,
                'max_ask': max_ask,
                'avg_bid': avg_bid_volume,
                'avg_ask': avg_ask_volume,
                'has_buy_wall': has_buy_wall,
                'has_sell_wall': has_sell_wall
            }
        )


# Register crypto features
registry.register('FundingRate', FundingRateFeature)
registry.register('OpenInterest', OpenInterestFeature)
registry.register('Basis', BasisFeature)
registry.register('Liquidations', LiquidationsFeature)
registry.register('OIVolumeRatio', OIVolumeRatioFeature)
registry.register('ExchangeFlow', ExchangeFlowFeature)
registry.register('OrderBookImbalance', OrderBookImbalanceFeature)
registry.register('OrderBookWall', OrderBookWallFeature)
