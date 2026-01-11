"""
API Views for Trading Oracle
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import uuid

from oracle.models import (
    Symbol, MarketType, Timeframe, Feature, Decision,
    FeatureContribution, MarketData, AnalysisRun
)
from .serializers import (
    SymbolSerializer, MarketTypeSerializer, TimeframeSerializer,
    FeatureSerializer, DecisionSerializer, DecisionSummarySerializer,
    MarketDataSerializer, AnalysisRunSerializer,
    AnalyzeRequestSerializer, AnalyzeResponseSerializer,
    BulkDecisionSerializer
)


class SymbolViewSet(viewsets.ModelViewSet):
    """
    API endpoint for symbols

    list: Get all symbols
    retrieve: Get specific symbol
    create: Add new symbol
    update: Update symbol
    delete: Delete symbol
    """
    queryset = Symbol.objects.filter(is_active=True)
    serializer_class = SymbolSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['asset_type', 'is_active']
    search_fields = ['symbol', 'name', 'base_currency', 'quote_currency']

    @action(detail=False, methods=['get'])
    def by_asset_type(self, request):
        """Get symbols grouped by asset type"""
        asset_type = request.query_params.get('type')
        if asset_type:
            symbols = self.queryset.filter(asset_type=asset_type)
        else:
            symbols = self.queryset.all()

        serializer = self.get_serializer(symbols, many=True)
        return Response(serializer.data)


class MarketTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for market types (read-only)"""
    queryset = MarketType.objects.all()
    serializer_class = MarketTypeSerializer
    permission_classes = [AllowAny]


class TimeframeViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for timeframes (read-only)"""
    queryset = Timeframe.objects.all()
    serializer_class = TimeframeSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def by_classification(self, request):
        """Get timeframes grouped by classification"""
        classification = request.query_params.get('classification')
        if classification:
            timeframes = self.queryset.filter(classification=classification)
        else:
            timeframes = self.queryset.all()

        serializer = self.get_serializer(timeframes, many=True)
        return Response(serializer.data)


class FeatureViewSet(viewsets.ModelViewSet):
    """API endpoint for features"""
    queryset = Feature.objects.filter(is_active=True)
    serializer_class = FeatureSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['category', 'is_active']
    search_fields = ['name', 'description']

    @action(detail=False, methods=['get'])
    def by_category(self, request):
        """Get features grouped by category"""
        category = request.query_params.get('category')
        if category:
            features = self.queryset.filter(category=category)
        else:
            features = self.queryset.all()

        serializer = self.get_serializer(features, many=True)
        return Response(serializer.data)


class DecisionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API endpoint for decisions (read-only)

    list: Get all recent decisions
    retrieve: Get specific decision with all feature contributions
    latest: Get latest decisions for all symbols
    by_symbol: Get decisions for specific symbol
    analyze: Trigger new analysis
    """
    queryset = Decision.objects.all().select_related(
        'symbol', 'market_type', 'timeframe'
    ).prefetch_related('feature_contributions__feature')
    serializer_class = DecisionSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        """Filter queryset based on query parameters"""
        queryset = super().get_queryset()

        # Filter by symbol
        symbol = self.request.query_params.get('symbol')
        if symbol:
            queryset = queryset.filter(symbol__symbol=symbol)

        # Filter by market type
        market_type = self.request.query_params.get('market_type')
        if market_type:
            queryset = queryset.filter(market_type__name=market_type)

        # Filter by timeframe
        timeframe = self.request.query_params.get('timeframe')
        if timeframe:
            queryset = queryset.filter(timeframe__name=timeframe)

        # Filter by signal
        signal = self.request.query_params.get('signal')
        if signal:
            queryset = queryset.filter(signal=signal)

        # Filter by date range
        start_date = self.request.query_params.get('start_date')
        if start_date:
            queryset = queryset.filter(created_at__gte=start_date)

        end_date = self.request.query_params.get('end_date')
        if end_date:
            queryset = queryset.filter(created_at__lte=end_date)

        return queryset

    def get_serializer_class(self):
        """Use summary serializer for list view"""
        if self.action == 'list':
            return DecisionSummarySerializer
        return DecisionSerializer

    @action(detail=False, methods=['get'])
    def latest(self, request):
        """
        Get latest decisions for all active symbols

        Returns the most recent decision for each symbol/market_type/timeframe combination
        """
        # Get latest decision for each symbol/market/timeframe combo
        from django.db.models import Max

        latest_decisions = []
        symbols = Symbol.objects.filter(is_active=True)

        for symbol in symbols:
            for market_type in MarketType.objects.all():
                for timeframe in Timeframe.objects.all():
                    decision = Decision.objects.filter(
                        symbol=symbol,
                        market_type=market_type,
                        timeframe=timeframe
                    ).order_by('-created_at').first()

                    if decision:
                        latest_decisions.append(decision)

        serializer = DecisionSummarySerializer(latest_decisions, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def by_symbol(self, request):
        """
        Get all decisions for a specific symbol

        Query params:
        - symbol: Symbol code (required)
        - limit: Number of recent decisions per timeframe (default: 1)
        """
        symbol_code = request.query_params.get('symbol')
        if not symbol_code:
            return Response(
                {'error': 'symbol parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            symbol = Symbol.objects.get(symbol=symbol_code)
        except Symbol.DoesNotExist:
            return Response(
                {'error': f'Symbol {symbol_code} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        limit = int(request.query_params.get('limit', 1))

        # Get decisions grouped by market type and timeframe
        result = {
            'symbol': symbol.symbol,
            'name': symbol.name,
            'asset_type': symbol.asset_type,
            'decisions': {}
        }

        for market_type in MarketType.objects.all():
            market_key = market_type.name
            result['decisions'][market_key] = {}

            for timeframe in Timeframe.objects.all():
                decisions = Decision.objects.filter(
                    symbol=symbol,
                    market_type=market_type,
                    timeframe=timeframe
                ).order_by('-created_at')[:limit]

                if decisions:
                    result['decisions'][market_key][timeframe.name] = \
                        DecisionSerializer(decisions, many=True).data

        return Response(result)

    @action(detail=False, methods=['post'])
    def analyze(self, request):
        """
        Trigger new analysis for specified symbols

        Request body:
        {
            "symbols": ["BTCUSDT", "XAUUSD"],  // required
            "market_types": ["SPOT", "PERPETUAL"],  // optional, default: ["SPOT"]
            "timeframes": ["1h", "4h", "1d"]  // optional, default: ["1h", "4h", "1d"]
        }
        """
        # Validate request
        request_serializer = AnalyzeRequestSerializer(data=request.data)
        if not request_serializer.is_valid():
            return Response(
                request_serializer.errors,
                status=status.HTTP_400_BAD_REQUEST
            )

        data = request_serializer.validated_data

        # Create analysis run
        run_id = str(uuid.uuid4())
        analysis_run = AnalysisRun.objects.create(
            run_id=run_id,
            status='PENDING',
            symbols=data['symbols'],
            timeframes=data.get('timeframes', ['1h', '4h', '1d']),
            market_types=data.get('market_types', ['SPOT']),
            started_at=timezone.now()
        )

        # Queue analysis task (Celery)
        # For now, return pending status
        # In production, this would trigger: tasks.run_analysis.delay(run_id)

        return Response({
            'run_id': run_id,
            'status': 'PENDING',
            'message': 'Analysis queued. Use /api/analysis-runs/{run_id}/ to check status.',
            'symbols': data['symbols'],
            'timeframes': data.get('timeframes', ['1h', '4h', '1d']),
            'market_types': data.get('market_types', ['SPOT'])
        }, status=status.HTTP_202_ACCEPTED)

    @action(detail=False, methods=['get'])
    def bulk(self, request):
        """
        Get latest decisions for multiple symbols in one request

        Query params:
        - symbols: Comma-separated list of symbols (e.g., "BTC,ETH,XAUUSD")
        """
        symbols_param = request.query_params.get('symbols', '')
        if not symbols_param:
            return Response(
                {'error': 'symbols parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        symbol_codes = [s.strip() for s in symbols_param.split(',')]

        results = []

        for symbol_code in symbol_codes:
            try:
                symbol = Symbol.objects.get(symbol=symbol_code)
            except Symbol.DoesNotExist:
                continue

            # Get latest decisions for this symbol
            decisions = Decision.objects.filter(
                symbol=symbol
            ).select_related('market_type', 'timeframe').order_by('-created_at')[:20]

            results.append({
                'symbol': symbol.symbol,
                'asset_type': symbol.asset_type,
                'decisions': DecisionSummarySerializer(decisions, many=True).data
            })

        serializer = BulkDecisionSerializer(results, many=True)
        return Response(serializer.data)


class MarketDataViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for market data (OHLCV)"""
    queryset = MarketData.objects.all().select_related('symbol', 'market_type', 'timeframe')
    serializer_class = MarketDataSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = super().get_queryset()

        symbol = self.request.query_params.get('symbol')
        if symbol:
            queryset = queryset.filter(symbol__symbol=symbol)

        timeframe = self.request.query_params.get('timeframe')
        if timeframe:
            queryset = queryset.filter(timeframe__name=timeframe)

        # Limit to recent data
        limit = int(self.request.query_params.get('limit', 100))
        queryset = queryset.order_by('-timestamp')[:limit]

        return queryset


class AnalysisRunViewSet(viewsets.ReadOnlyModelViewSet):
    """API endpoint for analysis runs"""
    queryset = AnalysisRun.objects.all()
    serializer_class = AnalysisRunSerializer
    permission_classes = [AllowAny]
    lookup_field = 'run_id'

    @action(detail=True, methods=['get'])
    def decisions(self, request, run_id=None):
        """Get all decisions from a specific analysis run"""
        try:
            analysis_run = AnalysisRun.objects.get(run_id=run_id)
        except AnalysisRun.DoesNotExist:
            return Response(
                {'error': f'Analysis run {run_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Get decisions created during this run
        # This assumes decisions are timestamped during the run
        decisions = Decision.objects.filter(
            created_at__gte=analysis_run.started_at,
            created_at__lte=analysis_run.completed_at or timezone.now()
        ).select_related('symbol', 'market_type', 'timeframe')

        serializer = DecisionSummarySerializer(decisions, many=True)
        return Response({
            'run_id': run_id,
            'status': analysis_run.status,
            'started_at': analysis_run.started_at,
            'completed_at': analysis_run.completed_at,
            'decisions_count': decisions.count(),
            'decisions': serializer.data
        })
