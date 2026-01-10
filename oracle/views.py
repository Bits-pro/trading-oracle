"""
Web views for performance monitoring dashboard
"""
from django.shortcuts import render
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

from oracle.models import Decision, Symbol, AnalysisRun


def dashboard(request):
    """Main dashboard view"""
    # Get recent decisions
    recent_decisions = Decision.objects.select_related(
        'symbol', 'market_type', 'timeframe'
    ).order_by('-created_at')[:20]

    # Performance metrics (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    recent_decisions_30d = Decision.objects.filter(created_at__gte=thirty_days_ago)

    # Count by signal
    signal_counts = recent_decisions_30d.values('signal').annotate(
        count=Count('id')
    ).order_by('-count')

    # Avg confidence by signal
    avg_confidence = recent_decisions_30d.values('signal').annotate(
        avg_conf=Avg('confidence')
    )

    # Active symbols
    active_symbols = Symbol.objects.filter(is_active=True).order_by('symbol')

    # Recent analysis runs
    recent_runs = AnalysisRun.objects.order_by('-created_at')[:10]

    context = {
        'recent_decisions': recent_decisions,
        'signal_counts': signal_counts,
        'avg_confidence': avg_confidence,
        'active_symbols': active_symbols,
        'recent_runs': recent_runs,
        'total_decisions_30d': recent_decisions_30d.count(),
    }

    return render(request, 'oracle/dashboard.html', context)


def symbol_performance(request, symbol_code):
    """Performance view for specific symbol"""
    try:
        symbol = Symbol.objects.get(symbol=symbol_code)
    except Symbol.DoesNotExist:
        return render(request, '404.html', status=404)

    # Get all decisions for this symbol
    decisions = Decision.objects.filter(
        symbol=symbol
    ).select_related('market_type', 'timeframe').order_by('-created_at')[:100]

    # Group by timeframe
    decisions_by_timeframe = {}
    for decision in decisions:
        tf = decision.timeframe.name
        if tf not in decisions_by_timeframe:
            decisions_by_timeframe[tf] = []
        decisions_by_timeframe[tf].append(decision)

    # Signal distribution
    signal_distribution = decisions.values('signal').annotate(
        count=Count('id')
    ).order_by('-count')

    context = {
        'symbol': symbol,
        'decisions': decisions[:20],  # Latest 20 for display
        'decisions_by_timeframe': decisions_by_timeframe,
        'signal_distribution': signal_distribution,
        'total_decisions': decisions.count(),
    }

    return render(request, 'oracle/symbol_performance.html', context)
