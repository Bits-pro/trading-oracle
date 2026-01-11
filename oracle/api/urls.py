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

router = DefaultRouter()
router.register(r'symbols', SymbolViewSet, basename='symbol')
router.register(r'market-types', MarketTypeViewSet, basename='market-type')
router.register(r'timeframes', TimeframeViewSet, basename='timeframe')
router.register(r'features', FeatureViewSet, basename='feature')
router.register(r'decisions', DecisionViewSet, basename='decision')
router.register(r'market-data', MarketDataViewSet, basename='market-data')
router.register(r'analysis-runs', AnalysisRunViewSet, basename='analysis-run')

urlpatterns = [
    path('', include(router.urls)),
]
