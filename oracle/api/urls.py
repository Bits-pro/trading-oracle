"""
API URL routing
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    SymbolViewSet, MarketTypeViewSet, TimeframeViewSet,
    FeatureViewSet, DecisionViewSet, MarketDataViewSet,
    AnalysisRunViewSet
)
from .health import health_check, readiness_check, liveness_check

router = DefaultRouter()
router.register(r'symbols', SymbolViewSet, basename='symbol')
router.register(r'market-types', MarketTypeViewSet, basename='market-type')
router.register(r'timeframes', TimeframeViewSet, basename='timeframe')
router.register(r'features', FeatureViewSet, basename='feature')
router.register(r'decisions', DecisionViewSet, basename='decision')
router.register(r'market-data', MarketDataViewSet, basename='market-data')
router.register(r'analysis-runs', AnalysisRunViewSet, basename='analysis-run')

urlpatterns = [
    # Health check endpoints
    path('health/', health_check, name='health-check'),
    path('health/ready/', readiness_check, name='readiness-check'),
    path('health/live/', liveness_check, name='liveness-check'),

    # Router URLs
    path('', include(router.urls)),
]
