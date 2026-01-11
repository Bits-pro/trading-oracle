"""
DRF Serializers for API endpoints
"""
from rest_framework import serializers
from oracle.models import (
    Symbol, MarketType, Timeframe, Feature, Decision,
    FeatureContribution, MarketData, DerivativesData,
    MacroData, SentimentData, AnalysisRun
)


class SymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symbol
        fields = '__all__'


class MarketTypeSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(source='get_name_display', read_only=True)

    class Meta:
        model = MarketType
        fields = '__all__'


class TimeframeSerializer(serializers.ModelSerializer):
    classification_display = serializers.CharField(
        source='get_classification_display',
        read_only=True
    )

    class Meta:
        model = Timeframe
        fields = '__all__'


class FeatureSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source='get_category_display', read_only=True)

    class Meta:
        model = Feature
        fields = '__all__'


class FeatureContributionSerializer(serializers.ModelSerializer):
    feature_name = serializers.CharField(source='feature.name', read_only=True)
    feature_category = serializers.CharField(source='feature.category', read_only=True)

    class Meta:
        model = FeatureContribution
        fields = [
            'id', 'feature', 'feature_name', 'feature_category',
            'raw_value', 'direction', 'strength', 'weight',
            'contribution', 'explanation', 'created_at'
        ]


class DecisionSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True)
    market_type_name = serializers.CharField(source='market_type.name', read_only=True)
    timeframe_name = serializers.CharField(source='timeframe.name', read_only=True)
    signal_display = serializers.CharField(source='get_signal_display', read_only=True)
    bias_display = serializers.CharField(source='get_bias_display', read_only=True)
    feature_contributions = FeatureContributionSerializer(many=True, read_only=True)

    class Meta:
        model = Decision
        fields = [
            'id', 'symbol', 'symbol_name', 'market_type', 'market_type_name',
            'timeframe', 'timeframe_name', 'signal', 'signal_display',
            'bias', 'bias_display', 'confidence', 'entry_price',
            'stop_loss', 'take_profit', 'risk_reward',
            'invalidation_conditions', 'top_drivers', 'raw_score',
            'regime_context', 'feature_contributions', 'created_at'
        ]


class DecisionSummarySerializer(serializers.ModelSerializer):
    """Lightweight decision serializer without feature contributions"""
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True)
    market_type_name = serializers.CharField(source='market_type.name', read_only=True)
    timeframe_name = serializers.CharField(source='timeframe.name', read_only=True)

    class Meta:
        model = Decision
        fields = [
            'id', 'symbol_name', 'market_type_name', 'timeframe_name',
            'signal', 'bias', 'confidence', 'entry_price',
            'stop_loss', 'take_profit', 'risk_reward', 'created_at'
        ]


class MarketDataSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True)

    class Meta:
        model = MarketData
        fields = '__all__'


class DerivativesDataSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True)

    class Meta:
        model = DerivativesData
        fields = '__all__'


class MacroDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = MacroData
        fields = '__all__'


class SentimentDataSerializer(serializers.ModelSerializer):
    symbol_name = serializers.CharField(source='symbol.symbol', read_only=True, allow_null=True)
    source_display = serializers.CharField(source='get_source_display', read_only=True)

    class Meta:
        model = SentimentData
        fields = '__all__'


class AnalysisRunSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source='get_status_display', read_only=True)

    class Meta:
        model = AnalysisRun
        fields = '__all__'


class AnalyzeRequestSerializer(serializers.Serializer):
    """Request serializer for analysis endpoint"""
    symbols = serializers.ListField(
        child=serializers.CharField(),
        help_text="List of symbol codes to analyze (e.g., ['BTCUSDT', 'XAUUSD'])"
    )
    market_types = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=['SPOT'],
        help_text="List of market types (e.g., ['SPOT', 'PERPETUAL'])"
    )
    timeframes = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=['1h', '4h', '1d'],
        help_text="List of timeframes (e.g., ['1h', '4h', '1d'])"
    )


class AnalyzeResponseSerializer(serializers.Serializer):
    """Response serializer for analysis endpoint"""
    run_id = serializers.CharField()
    status = serializers.CharField()
    decisions = DecisionSerializer(many=True)
    summary = serializers.DictField()


class BulkDecisionSerializer(serializers.Serializer):
    """Serializer for bulk decision responses grouped by symbol"""
    symbol = serializers.CharField()
    asset_type = serializers.CharField()
    decisions = serializers.SerializerMethodField()

    def get_decisions(self, obj):
        """Group decisions by market type and timeframe"""
        decisions_by_market = {}

        for decision in obj.get('decisions', []):
            market_key = f"{decision['market_type_name']}"

            if market_key not in decisions_by_market:
                decisions_by_market[market_key] = {}

            timeframe = decision['timeframe_name']
            decisions_by_market[market_key][timeframe] = decision

        return decisions_by_market
