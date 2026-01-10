"""
Django models for Trading Oracle
Stores symbols, decisions, features, market data, and audit trails
"""
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.core.validators import MinValueValidator, MaxValueValidator
import json


class Symbol(models.Model):
    """Tradable symbols (BTC, ETH, XAUUSD, PAXGUSDT, etc.)"""

    ASSET_TYPE_CHOICES = [
        ('CRYPTO', 'Cryptocurrency'),
        ('GOLD', 'Gold'),
        ('COMMODITY', 'Commodity'),
        ('FX', 'Foreign Exchange'),
        ('STOCK', 'Stock'),
        ('INDEX', 'Index'),
    ]

    symbol = models.CharField(max_length=50, unique=True, db_index=True)
    name = models.CharField(max_length=200)
    asset_type = models.CharField(max_length=20, choices=ASSET_TYPE_CHOICES)
    base_currency = models.CharField(max_length=10)
    quote_currency = models.CharField(max_length=10)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    # Trading parameters
    min_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    max_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    tick_size = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['symbol']
        indexes = [
            models.Index(fields=['asset_type', 'is_active']),
        ]

    def __str__(self):
        return f"{self.symbol} ({self.asset_type})"


class MarketType(models.Model):
    """Market types: SPOT, PERPETUAL, FUTURES, CFD"""

    MARKET_TYPE_CHOICES = [
        ('SPOT', 'Spot Market'),
        ('PERPETUAL', 'Perpetual Futures'),
        ('FUTURES', 'Dated Futures'),
        ('CFD', 'Contract for Difference'),
    ]

    name = models.CharField(max_length=20, choices=MARKET_TYPE_CHOICES, unique=True)
    description = models.TextField(blank=True)
    supports_funding = models.BooleanField(default=False)  # Perps have funding rates
    supports_open_interest = models.BooleanField(default=False)

    def __str__(self):
        return self.get_name_display()


class Timeframe(models.Model):
    """Trading timeframes with classifications"""

    TIMEFRAME_CLASS_CHOICES = [
        ('SHORT', 'Short-term (intraday to 5 days)'),
        ('MEDIUM', 'Medium-term (days to weeks)'),
        ('LONG', 'Long-term (weeks to months)'),
    ]

    name = models.CharField(max_length=10, unique=True)  # e.g., '15m', '1h', '4h', '1d', '1w'
    minutes = models.IntegerField()  # Duration in minutes
    classification = models.CharField(max_length=10, choices=TIMEFRAME_CLASS_CHOICES)
    display_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['minutes']

    def __str__(self):
        return f"{self.name} ({self.get_classification_display()})"


class Feature(models.Model):
    """Feature registry - all available features"""

    CATEGORY_CHOICES = [
        ('TECHNICAL', 'Technical Indicator'),
        ('MACRO', 'Macro Economic'),
        ('INTERMARKET', 'Intermarket Relationship'),
        ('SENTIMENT', 'Market Sentiment'),
        ('CRYPTO_SPOT', 'Crypto Spot Specific'),
        ('CRYPTO_DERIVATIVES', 'Crypto Derivatives'),
        ('VOLUME', 'Volume Analysis'),
        ('VOLATILITY', 'Volatility Metric'),
        ('STRUCTURE', 'Market Structure'),
    ]

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    description = models.TextField()

    # Parameters (stored as JSON)
    default_params = models.JSONField(default=dict, blank=True)

    # Weight configuration per timeframe
    weight_short = models.FloatField(default=1.0, validators=[MinValueValidator(0.0)])
    weight_medium = models.FloatField(default=1.0, validators=[MinValueValidator(0.0)])
    weight_long = models.FloatField(default=1.0, validators=[MinValueValidator(0.0)])

    # Applicability
    applicable_spot = models.BooleanField(default=True)
    applicable_derivatives = models.BooleanField(default=True)
    requires_crypto = models.BooleanField(default=False)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['category', 'name']
        indexes = [
            models.Index(fields=['category', 'is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.category})"


class Decision(models.Model):
    """Trading decision output"""

    SIGNAL_CHOICES = [
        ('STRONG_BUY', 'Strong Buy'),
        ('BUY', 'Buy'),
        ('WEAK_BUY', 'Weak Buy'),
        ('NEUTRAL', 'Neutral'),
        ('WEAK_SELL', 'Weak Sell'),
        ('SELL', 'Sell'),
        ('STRONG_SELL', 'Strong Sell'),
    ]

    BIAS_CHOICES = [
        ('BULLISH', 'Bullish'),
        ('NEUTRAL', 'Neutral'),
        ('BEARISH', 'Bearish'),
    ]

    # Identification
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name='decisions')
    market_type = models.ForeignKey(MarketType, on_delete=models.CASCADE)
    timeframe = models.ForeignKey(Timeframe, on_delete=models.CASCADE)

    # Decision outputs
    signal = models.CharField(max_length=15, choices=SIGNAL_CHOICES)
    bias = models.CharField(max_length=10, choices=BIAS_CHOICES)
    confidence = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )

    # Trade parameters
    entry_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    stop_loss = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    take_profit = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    risk_reward = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)

    # Invalidation conditions (stored as JSON list)
    invalidation_conditions = models.JSONField(default=list, blank=True)

    # Top feature drivers (stored as JSON)
    top_drivers = models.JSONField(default=list, blank=True)

    # Metadata
    raw_score = models.FloatField(null=True, blank=True)  # Pre-normalization score
    regime_context = models.JSONField(default=dict, blank=True)  # Market regime info

    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['symbol', 'market_type', 'timeframe', '-created_at']),
            models.Index(fields=['signal', '-created_at']),
        ]
        unique_together = [['symbol', 'market_type', 'timeframe', 'created_at']]

    def __str__(self):
        return (f"{self.symbol.symbol} {self.market_type.name} {self.timeframe.name}: "
                f"{self.signal} (conf: {self.confidence}%)")


class FeatureContribution(models.Model):
    """Individual feature contributions to a decision"""

    decision = models.ForeignKey(
        Decision,
        on_delete=models.CASCADE,
        related_name='feature_contributions'
    )
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)

    # Feature values
    raw_value = models.FloatField()  # Raw indicator value
    direction = models.IntegerField(
        validators=[MinValueValidator(-1), MaxValueValidator(1)]
    )  # -1 (bearish), 0 (neutral), 1 (bullish)
    strength = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )  # 0..1
    weight = models.FloatField()  # Applied weight
    contribution = models.FloatField()  # weight * direction * strength

    # Explanation
    explanation = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-contribution']
        indexes = [
            models.Index(fields=['decision', '-contribution']),
        ]

    def __str__(self):
        return f"{self.feature.name}: {self.contribution:.4f}"


class MarketData(models.Model):
    """OHLCV and derived market data"""

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name='market_data')
    market_type = models.ForeignKey(MarketType, on_delete=models.CASCADE)
    timeframe = models.ForeignKey(Timeframe, on_delete=models.CASCADE)

    timestamp = models.DateTimeField(db_index=True)

    # OHLCV
    open = models.DecimalField(max_digits=20, decimal_places=8)
    high = models.DecimalField(max_digits=20, decimal_places=8)
    low = models.DecimalField(max_digits=20, decimal_places=8)
    close = models.DecimalField(max_digits=20, decimal_places=8)
    volume = models.DecimalField(max_digits=30, decimal_places=8)

    # Computed indicators (stored as JSON for flexibility)
    indicators = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['symbol', 'market_type', 'timeframe', '-timestamp']),
        ]
        unique_together = [['symbol', 'market_type', 'timeframe', 'timestamp']]

    def __str__(self):
        return f"{self.symbol.symbol} {self.timeframe.name} @ {self.timestamp}"


class DerivativesData(models.Model):
    """Crypto derivatives-specific data (funding, OI, liquidations)"""

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, related_name='derivatives_data')
    timestamp = models.DateTimeField(db_index=True)

    # Funding rate
    funding_rate = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    funding_rate_8h = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    next_funding_time = models.DateTimeField(null=True, blank=True)

    # Open Interest
    open_interest = models.DecimalField(max_digits=30, decimal_places=8, null=True, blank=True)
    open_interest_value = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)

    # Basis / Premium
    mark_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    index_price = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True)
    basis = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)

    # Liquidations (aggregated)
    liquidations_long = models.DecimalField(max_digits=30, decimal_places=8, default=0)
    liquidations_short = models.DecimalField(max_digits=30, decimal_places=8, default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['symbol', '-timestamp']),
        ]
        unique_together = [['symbol', 'timestamp']]

    def __str__(self):
        return f"{self.symbol.symbol} Derivatives @ {self.timestamp}"


class MacroData(models.Model):
    """Macro economic indicators (DXY, VIX, yields, etc.)"""

    indicator_name = models.CharField(max_length=50, db_index=True)
    timestamp = models.DateTimeField(db_index=True)
    value = models.DecimalField(max_digits=20, decimal_places=8)

    # Optional metadata
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['indicator_name', '-timestamp']),
        ]
        unique_together = [['indicator_name', 'timestamp']]

    def __str__(self):
        return f"{self.indicator_name}: {self.value} @ {self.timestamp}"


class SentimentData(models.Model):
    """Sentiment analysis from news, social media, etc."""

    SOURCE_CHOICES = [
        ('NEWS', 'News Articles'),
        ('TWITTER', 'Twitter/X'),
        ('REDDIT', 'Reddit'),
        ('TELEGRAM', 'Telegram'),
        ('FEAR_GREED', 'Fear & Greed Index'),
        ('OTHER', 'Other Source'),
    ]

    symbol = models.ForeignKey(
        Symbol,
        on_delete=models.CASCADE,
        related_name='sentiment_data',
        null=True,
        blank=True
    )
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    timestamp = models.DateTimeField(db_index=True)

    # Sentiment score (typically -1 to 1 or 0 to 100)
    score = models.FloatField()
    normalized_score = models.FloatField(
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )

    # Raw data
    raw_data = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['symbol', 'source', '-timestamp']),
        ]

    def __str__(self):
        symbol_str = self.symbol.symbol if self.symbol else "MARKET"
        return f"{symbol_str} {self.source}: {self.normalized_score:.2f} @ {self.timestamp}"


class AnalysisRun(models.Model):
    """Audit trail for each analysis execution"""

    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RUNNING', 'Running'),
        ('COMPLETED', 'Completed'),
        ('FAILED', 'Failed'),
    ]

    run_id = models.CharField(max_length=100, unique=True, db_index=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')

    # Configuration
    symbols = models.JSONField(default=list)  # List of symbol IDs analyzed
    timeframes = models.JSONField(default=list)  # List of timeframe IDs
    market_types = models.JSONField(default=list)  # List of market type IDs

    # Results
    decisions_created = models.IntegerField(default=0)
    errors = models.JSONField(default=list, blank=True)

    # Timing
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at', 'status']),
        ]

    def __str__(self):
        return f"Run {self.run_id}: {self.status}"


class FeatureWeight(models.Model):
    """Custom feature weights per symbol/market type/timeframe combination"""

    feature = models.ForeignKey(Feature, on_delete=models.CASCADE)
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE, null=True, blank=True)
    market_type = models.ForeignKey(MarketType, on_delete=models.CASCADE, null=True, blank=True)
    timeframe = models.ForeignKey(Timeframe, on_delete=models.CASCADE, null=True, blank=True)

    weight = models.FloatField(validators=[MinValueValidator(0.0)])

    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['feature', 'symbol', 'market_type', 'timeframe']),
        ]
        unique_together = [['feature', 'symbol', 'market_type', 'timeframe']]

    def __str__(self):
        parts = [self.feature.name]
        if self.symbol:
            parts.append(self.symbol.symbol)
        if self.market_type:
            parts.append(self.market_type.name)
        if self.timeframe:
            parts.append(self.timeframe.name)
        return f"{' - '.join(parts)}: {self.weight}"
