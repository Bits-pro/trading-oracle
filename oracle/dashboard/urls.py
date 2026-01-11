"""
URL configuration for Trading Oracle Dashboard
"""
from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard pages
    path('', views.dashboard_home, name='home'),
    path('features/', views.feature_analysis, name='features'),
    path('history/', views.decision_history, name='history'),
    path('live/', views.live_monitor, name='live'),
    path('decision/<int:decision_id>/', views.decision_detail, name='decision_detail'),

    # API endpoints for charts and live updates
    path('api/chart/decisions/', views.api_decision_chart_data, name='api_decision_chart'),
    path('api/chart/confidence/', views.api_confidence_distribution, name='api_confidence_chart'),
    path('api/chart/feature-power/', views.api_feature_power_chart, name='api_feature_power'),
    path('api/chart/consensus/', views.api_consensus_breakdown, name='api_consensus_chart'),
    path('api/live-updates/', views.api_live_updates, name='api_live_updates'),
    path('api/symbol/<str:symbol>/', views.api_symbol_performance, name='api_symbol_performance'),
]
