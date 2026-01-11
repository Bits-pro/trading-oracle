"""
News Sentiment Provider
Fetches news and analyzes sentiment for trading signals
"""
import requests
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class NewsSentimentProvider:
    """
    Provider for news sentiment analysis

    Uses NewsAPI to fetch relevant news and analyze sentiment
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize news provider

        Args:
            api_key: NewsAPI key (or set NEWS_API_KEY env var)
        """
        self.api_key = api_key or 'a0fc02fcd3f245a2becb35e282702ef4'  # Default API key from config
        self.base_url = 'https://newsapi.org/v2/everything'

    def fetch_sentiment(
        self,
        keywords: List[str] = None,
        lookback_hours: int = 24
    ) -> Dict:
        """
        Fetch news sentiment

        Args:
            keywords: List of keywords to search for
            lookback_hours: Hours to look back

        Returns:
            Dict with sentiment data:
            {
                'fear_index': float (-1 to 1, negative = fear, positive = greed),
                'count': int (number of articles),
                'urgency': float (0 to 1, how urgent/recent the news is)
            }
        """
        if keywords is None:
            keywords = [
                'Gold price',
                'Bitcoin price',
                'Market crash',
                'Federal Reserve rates',
                'US Dollar',
                'Inflation'
            ]

        all_articles = []

        for keyword in keywords:
            try:
                response = requests.get(
                    self.base_url,
                    params={
                        'q': keyword,
                        'apiKey': self.api_key,
                        'language': 'en',
                        'pageSize': 10,
                        'sortBy': 'publishedAt'
                    },
                    timeout=10
                )

                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articles', [])
                    all_articles.extend(articles)
                else:
                    logger.warning(f"NewsAPI returned status {response.status_code} for '{keyword}'")

            except Exception as e:
                logger.error(f"Error fetching news for '{keyword}': {e}")
                continue

        if not all_articles:
            logger.warning("No news articles fetched")
            return {
                'fear_index': 0.0,
                'count': 0,
                'urgency': 0.0
            }

        # Analyze sentiment
        fear_index = self._analyze_sentiment(all_articles)

        # Calculate urgency (more recent = more urgent)
        urgency = self._calculate_urgency(all_articles, lookback_hours)

        return {
            'fear_index': round(fear_index, 4),
            'count': len(all_articles),
            'urgency': round(urgency, 4)
        }

    def _analyze_sentiment(self, articles: List[Dict]) -> float:
        """
        Analyze sentiment of articles

        Returns:
            Fear index (-1 to 1, negative = fear, positive = greed)
        """
        try:
            from textblob import TextBlob
        except ImportError:
            logger.warning("textblob not installed, cannot analyze sentiment")
            return 0.0

        polarities = []
        fear_keywords = [
            'crash', 'plunge', 'collapse', 'crisis', 'panic', 'fear',
            'uncertainty', 'recession', 'downturn', 'sell-off', 'volatility',
            'concern', 'worry', 'risk', 'warning', 'threat'
        ]

        for article in articles[:25]:  # Limit to 25 articles
            title = article.get('title', '')
            description = article.get('description', '')

            if not title:
                continue

            # Combine title and description
            text = f"{title}. {description if description else ''}"

            # Get sentiment polarity
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity

            # Check for fear keywords (boost negative sentiment)
            text_lower = text.lower()
            fear_count = sum(1 for keyword in fear_keywords if keyword in text_lower)

            if fear_count > 0:
                # Amplify negative sentiment when fear keywords present
                polarity = polarity - (fear_count * 0.1)

            polarities.append(polarity)

        if not polarities:
            return 0.0

        # Average polarity, inverted (negative news = positive fear index)
        avg_polarity = sum(polarities) / len(polarities)
        fear_index = -avg_polarity  # Invert: negative news = positive fear

        # Clamp to -1 to 1
        fear_index = max(-1.0, min(1.0, fear_index))

        return fear_index

    def _calculate_urgency(self, articles: List[Dict], lookback_hours: int) -> float:
        """
        Calculate urgency based on recency of news

        Returns:
            Urgency score (0 to 1)
        """
        now = datetime.now()
        cutoff = now - timedelta(hours=lookback_hours)

        recent_count = 0
        total_count = 0

        for article in articles:
            try:
                published_at = article.get('publishedAt', '')
                if not published_at:
                    continue

                # Parse ISO format
                pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))

                total_count += 1
                if pub_date > cutoff:
                    recent_count += 1

            except Exception:
                continue

        if total_count == 0:
            return 0.0

        # Urgency is the proportion of recent articles
        urgency = recent_count / total_count

        return urgency
