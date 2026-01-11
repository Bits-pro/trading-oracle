"""
Django Admin configuration for Trading Oracle
"""
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Symbol, MarketType, Timeframe, Feature, Decision,
    FeatureContribution, MarketData, DerivativesData,
    MacroData, SentimentData, AnalysisRun, FeatureWeight
)


@admin.register(Symbol)
class SymbolAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'name', 'asset_type', 'base_currency', 'quote_currency', 'is_active', 'updated_at']
    list_filter = ['asset_type', 'is_active', 'created_at']
    search_fields = ['symbol', 'name', 'base_currency', 'quote_currency']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('symbol', 'name', 'asset_type', 'base_currency', 'quote_currency', 'description', 'is_active')
        }),
        ('Trading Parameters', {
            'fields': ('min_price', 'max_price', 'tick_size')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(MarketType)
class MarketTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'get_display_name', 'supports_funding', 'supports_open_interest']
    list_filter = ['supports_funding', 'supports_open_interest']

    def get_display_name(self, obj):
        return obj.get_name_display()
    get_display_name.short_description = 'Display Name'


@admin.register(Timeframe)
class TimeframeAdmin(admin.ModelAdmin):
    list_display = ['name', 'minutes', 'classification', 'get_classification_display', 'display_order']
    list_filter = ['classification']
    ordering = ['display_order', 'minutes']

    def get_classification_display(self, obj):
        return obj.get_classification_display()
    get_classification_display.short_description = 'Period'


@admin.register(Feature)
class FeatureAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'weight_short', 'weight_medium', 'weight_long',
        'applicable_spot', 'applicable_derivatives', 'is_active'
    ]
    list_filter = ['category', 'is_active', 'applicable_spot', 'applicable_derivatives', 'requires_crypto']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'category', 'description', 'is_active')
        }),
        ('Parameters', {
            'fields': ('default_params',)
        }),
        ('Weights by Timeframe', {
            'fields': ('weight_short', 'weight_medium', 'weight_long')
        }),
        ('Applicability', {
            'fields': ('applicable_spot', 'applicable_derivatives', 'requires_crypto')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class FeatureContributionInline(admin.TabularInline):
    model = FeatureContribution
    extra = 0
    readonly_fields = ['feature', 'raw_value', 'direction', 'strength', 'weight', 'contribution', 'explanation']
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Decision)
class DecisionAdmin(admin.ModelAdmin):
    list_display = [
        'symbol', 'market_type', 'timeframe', 'signal_badge', 'bias',
        'confidence', 'entry_price', 'risk_reward', 'created_at'
    ]
    list_filter = ['signal', 'bias', 'market_type', 'timeframe', 'symbol__asset_type', 'created_at']
    search_fields = ['symbol__symbol', 'symbol__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'
    inlines = [FeatureContributionInline]

    fieldsets = (
        ('Identification', {
            'fields': ('symbol', 'market_type', 'timeframe')
        }),
        ('Decision', {
            'fields': ('signal', 'bias', 'confidence')
        }),
        ('Trade Parameters', {
            'fields': ('entry_price', 'stop_loss', 'take_profit', 'risk_reward')
        }),
        ('Context', {
            'fields': ('invalidation_conditions', 'top_drivers', 'raw_score', 'regime_context')
        }),
        ('Timestamp', {
            'fields': ('created_at',)
        }),
    )

    def signal_badge(self, obj):
        """Display signal with color badge"""
        colors = {
            'STRONG_BUY': 'green',
            'BUY': 'lightgreen',
            'WEAK_BUY': 'palegreen',
            'NEUTRAL': 'gray',
            'WEAK_SELL': 'lightcoral',
            'SELL': 'red',
            'STRONG_SELL': 'darkred',
        }
        color = colors.get(obj.signal, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px; font-weight: bold;">{}</span>',
            color,
            obj.get_signal_display()
        )
    signal_badge.short_description = 'Signal'


@admin.register(FeatureContribution)
class FeatureContributionAdmin(admin.ModelAdmin):
    list_display = ['decision', 'feature', 'direction', 'strength', 'weight', 'contribution', 'created_at']
    list_filter = ['feature__category', 'direction', 'created_at']
    search_fields = ['decision__symbol__symbol', 'feature__name']
    readonly_fields = ['created_at']
    date_hierarchy = 'created_at'


@admin.register(MarketData)
class MarketDataAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'market_type', 'timeframe', 'timestamp', 'close', 'volume', 'created_at']
    list_filter = ['market_type', 'timeframe', 'symbol__asset_type', 'timestamp']
    search_fields = ['symbol__symbol']
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'


@admin.register(DerivativesData)
class DerivativesDataAdmin(admin.ModelAdmin):
    list_display = [
        'symbol', 'timestamp', 'funding_rate', 'open_interest',
        'mark_price', 'index_price', 'basis', 'created_at'
    ]
    list_filter = ['timestamp', 'created_at']
    search_fields = ['symbol__symbol']
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'


@admin.register(MacroData)
class MacroDataAdmin(admin.ModelAdmin):
    list_display = ['indicator_name', 'timestamp', 'value', 'created_at']
    list_filter = ['indicator_name', 'timestamp']
    search_fields = ['indicator_name']
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'


@admin.register(SentimentData)
class SentimentDataAdmin(admin.ModelAdmin):
    list_display = ['symbol', 'source', 'timestamp', 'score', 'normalized_score', 'created_at']
    list_filter = ['source', 'timestamp']
    search_fields = ['symbol__symbol']
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = ['run_id', 'status_badge', 'decisions_created', 'started_at', 'completed_at', 'duration_seconds']
    list_filter = ['status', 'created_at']
    search_fields = ['run_id']
    readonly_fields = ['created_at', 'started_at', 'completed_at']
    date_hierarchy = 'created_at'

    fieldsets = (
        ('Run Information', {
            'fields': ('run_id', 'status')
        }),
        ('Configuration', {
            'fields': ('symbols', 'timeframes', 'market_types')
        }),
        ('Results', {
            'fields': ('decisions_created', 'errors')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at', 'duration_seconds', 'created_at')
        }),
    )

    def status_badge(self, obj):
        """Display status with color badge"""
        colors = {
            'PENDING': 'orange',
            'RUNNING': 'blue',
            'COMPLETED': 'green',
            'FAILED': 'red',
        }
        color = colors.get(obj.status, 'gray')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 10px; border-radius: 3px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(FeatureWeight)
class FeatureWeightAdmin(admin.ModelAdmin):
    list_display = ['feature', 'symbol', 'market_type', 'timeframe', 'weight', 'is_active', 'updated_at']
    list_filter = ['feature__category', 'is_active', 'created_at']
    search_fields = ['feature__name', 'symbol__symbol']
    readonly_fields = ['created_at', 'updated_at']

    fieldsets = (
        ('Target', {
            'fields': ('feature', 'symbol', 'market_type', 'timeframe')
        }),
        ('Weight', {
            'fields': ('weight', 'is_active')
        }),
        ('Notes', {
            'fields': ('notes',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
