"""
Sentiment and news-based features
News sentiment, fear index, social media sentiment, etc.
"""
import pandas as pd
import numpy as np
from typing import Dict, Any, Optional
from .base import BaseFeature, FeatureResult, registry


class NewsSentimentFeature(BaseFeature):
    """News sentiment analysis - fear/greed for gold and markets"""
    category = 'SENTIMENT'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        """
        Calculate news sentiment from context

        Context should contain: {'sentiment': {'fear_index': float, 'count': int, 'urgency': float}}
        """
        if not context or 'sentiment' not in context:
            return FeatureResult(
                name='NewsSentiment',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="News sentiment data not available"
            )

        sentiment_data = context['sentiment']
        fear_index = sentiment_data.get('fear_index', 0.0)
        news_count = sentiment_data.get('count', 0)
        urgency = sentiment_data.get('urgency', 0.0)

        # Fear index ranges from -1 to 1
        # Negative = market fear (bullish for gold)
        # Positive = market greed (bearish for gold)

        # For gold: fear = bullish, greed = bearish
        if fear_index > 0.1:
            direction = 1  # High fear -> bullish for gold
            strength = min(1.0, abs(fear_index) * 2)
            explanation = f"High market fear ({fear_index:.3f}) - bullish for gold"
        elif fear_index < -0.1:
            direction = -1  # Low fear/greed -> bearish for gold
            strength = min(1.0, abs(fear_index) * 2)
            explanation = f"Market complacency ({fear_index:.3f}) - bearish for gold"
        else:
            direction = 0
            strength = 0.3
            explanation = f"Neutral sentiment ({fear_index:.3f})"

        # Adjust strength by urgency for short-term
        if urgency > 0.5:
            strength = min(1.0, strength * 1.3)

        return FeatureResult(
            name='NewsSentiment',
            category=self.category,
            raw_value=float(fear_index),
            direction=direction,
            strength=strength,
            explanation=explanation,
            metadata={
                'fear_index': float(fear_index),
                'news_count': news_count,
                'urgency': float(urgency)
            }
        )


class MarketFearGaugeFeature(BaseFeature):
    """Combined fear gauge using VIX + news sentiment"""
    category = 'SENTIMENT'

    def calculate(self, df: pd.DataFrame, symbol: str, timeframe: str,
                  market_type: str, context: Optional[Dict] = None) -> FeatureResult:
        """
        Calculate combined fear gauge

        Combines VIX and news sentiment for a comprehensive fear reading
        """
        if not context:
            return FeatureResult(
                name='MarketFearGauge',
                category=self.category,
                raw_value=0.0,
                direction=0,
                strength=0.0,
                explanation="Context data not available"
            )

        fear_score = 0.0
        components = []

        # VIX component
        if 'macro' in context and 'VIX' in context['macro']:
            vix_data = context['macro']['VIX']
            if not vix_data.empty:
                current_vix = vix_data['close'].iloc[-1]
                vix_score = (current_vix - 15) / 20  # Normalize around 15-35 range
                fear_score += vix_score * 0.6  # 60% weight
                components.append(f"VIX: {current_vix:.1f}")

        # News sentiment component
        if 'sentiment' in context:
            sentiment_data = context['sentiment']
            fear_index = sentiment_data.get('fear_index', 0.0)
            fear_score += fear_index * 0.4  # 40% weight
            components.append(f"News: {fear_index:.3f}")

        # Determine direction and strength
        if fear_score > 0.3:
            direction = 1  # High fear -> bullish for gold
            strength = min(1.0, abs(fear_score))
            explanation = f"Elevated fear ({fear_score:.3f}) - bullish for gold. {', '.join(components)}"
        elif fear_score < -0.3:
            direction = -1  # Low fear -> bearish for gold
            strength = min(1.0, abs(fear_score))
            explanation = f"Low fear ({fear_score:.3f}) - bearish for gold. {', '.join(components)}"
        else:
            direction = 0
            strength = 0.3
            explanation = f"Normal fear levels ({fear_score:.3f}). {', '.join(components)}"

        return FeatureResult(
            name='MarketFearGauge',
            category=self.category,
            raw_value=float(fear_score),
            direction=direction,
            strength=strength,
            explanation=explanation
        )


# Register sentiment features
registry.register('NewsSentiment', NewsSentimentFeature)
registry.register('MarketFearGauge', MarketFearGaugeFeature)
