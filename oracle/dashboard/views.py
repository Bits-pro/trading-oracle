"""
Dashboard views for Trading Oracle
Provides comprehensive visualization of decisions, features, and performance
"""
from django.shortcuts import render
from django.http import JsonResponse
from django.db.models import Count, Avg, Q, F, Sum
from django.db.models.functions import TruncDate, TruncHour
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
import json

from oracle.models import (
    Decision, Symbol, Timeframe, Feature, MarketType,
    MarketData, FeatureContribution
)


def dashboard_home(request):
    """
    Main dashboard overview
    Shows key metrics, recent decisions, and system health
    """
    # Get time ranges
    now = timezone.now()
    last_24h = now - timedelta(hours=24)
    last_7d = now - timedelta(days=7)
    last_30d = now - timedelta(days=30)

    # Overall statistics
    total_decisions = Decision.objects.count()
    decisions_24h = Decision.objects.filter(created_at__gte=last_24h).count()

    # Active symbols
    active_symbols = Symbol.objects.filter(is_active=True).count()

    # Average confidence
    avg_confidence = Decision.objects.aggregate(
        avg=Avg('confidence')
    )['avg'] or 0

    # Signal distribution (last 7 days)
    signal_distribution = Decision.objects.filter(
        created_at__gte=last_7d
    ).values('signal').annotate(count=Count('id')).order_by('-count')

    # Recent decisions
    recent_decisions = Decision.objects.select_related(
        'symbol', 'timeframe', 'market_type'
    ).order_by('-created_at')[:20]

    # Performance by timeframe
    performance_by_tf = Decision.objects.values(
        'timeframe__name'
    ).annotate(
        count=Count('id'),
        avg_confidence=Avg('confidence')
    ).order_by('-count')

    # Top performing symbols (by number of decisions)
    top_symbols = Decision.objects.filter(
        created_at__gte=last_7d
    ).values('symbol__symbol').annotate(
        count=Count('id'),
        avg_confidence=Avg('confidence')
    ).order_by('-count')[:10]

    context = {
        'total_decisions': total_decisions,
        'decisions_24h': decisions_24h,
        'active_symbols': active_symbols,
        'avg_confidence': round(avg_confidence, 2),
        'signal_distribution': signal_distribution,
        'recent_decisions': recent_decisions,
        'performance_by_tf': performance_by_tf,
        'top_symbols': top_symbols,
    }

    return render(request, 'dashboard/home.html', context)


def feature_analysis(request):
    """
    Feature analysis dashboard
    Shows power, effect, and accuracy for each feature
    """
    # Get all features
    features = Feature.objects.filter(is_active=True)

    # Calculate statistics for each feature
    feature_stats = []

    for feature in features:
        # Get recent contributions
        contributions = FeatureContribution.objects.filter(
            feature=feature,
            decision__created_at__gte=timezone.now() - timedelta(days=30)
        )

        if contributions.exists():
            # Calculate average contribution (power)
            avg_contribution = contributions.aggregate(
                avg=Avg('contribution')
            )['avg'] or 0

            # Calculate effect direction (positive/negative/neutral)
            positive_count = contributions.filter(contribution__gt=0).count()
            negative_count = contributions.filter(contribution__lt=0).count()
            total_count = contributions.count()

            positive_pct = (positive_count / total_count * 100) if total_count > 0 else 0
            negative_pct = (negative_count / total_count * 100) if total_count > 0 else 0

            # Determine dominant effect
            if positive_pct > 60:
                effect = 'BULLISH'
                effect_strength = positive_pct
            elif negative_pct > 60:
                effect = 'BEARISH'
                effect_strength = negative_pct
            else:
                effect = 'NEUTRAL'
                effect_strength = max(positive_pct, negative_pct)

            # Calculate power (absolute average contribution)
            power = abs(avg_contribution)

            # Get decisions using this feature
            decisions_with_feature = Decision.objects.filter(
                featurecontribution__feature=feature,
                created_at__gte=timezone.now() - timedelta(days=30)
            ).distinct()

            feature_stats.append({
                'feature': feature,
                'power': round(power, 4),
                'effect': effect,
                'effect_strength': round(effect_strength, 1),
                'avg_contribution': round(avg_contribution, 4),
                'usage_count': total_count,
                'decisions_count': decisions_with_feature.count(),
                'positive_count': positive_count,
                'negative_count': negative_count,
                'neutral_count': total_count - positive_count - negative_count,
            })

    # Sort by power (descending)
    feature_stats.sort(key=lambda x: x['power'], reverse=True)

    # Get top features by category
    categories = {}
    for stat in feature_stats:
        cat = stat['feature'].category
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(stat)

    context = {
        'feature_stats': feature_stats,
        'categories': categories,
        'total_features': len(feature_stats),
    }

    return render(request, 'dashboard/features.html', context)


def decision_history(request):
    """
    Decision history with filtering and search
    """
    # Get filter parameters
    symbol_filter = request.GET.get('symbol')
    timeframe_filter = request.GET.get('timeframe')
    signal_filter = request.GET.get('signal')
    days = int(request.GET.get('days', 7))

    # Base query
    decisions = Decision.objects.select_related(
        'symbol', 'timeframe', 'market_type'
    ).order_by('-created_at')

    # Apply filters
    if symbol_filter:
        decisions = decisions.filter(symbol__symbol=symbol_filter)
    if timeframe_filter:
        decisions = decisions.filter(timeframe__name=timeframe_filter)
    if signal_filter:
        decisions = decisions.filter(signal=signal_filter)

    # Time filter
    decisions = decisions.filter(
        created_at__gte=timezone.now() - timedelta(days=days)
    )

    # Pagination
    page = int(request.GET.get('page', 1))
    per_page = 50
    start = (page - 1) * per_page
    end = start + per_page

    total_count = decisions.count()
    decisions = decisions[start:end]

    # Get filter options
    symbols = Symbol.objects.filter(is_active=True).order_by('symbol')
    timeframes = Timeframe.objects.filter(is_active=True).order_by('sort_order')
    signals = Decision.SIGNAL_CHOICES

    # Calculate statistics for filtered results
    all_filtered = Decision.objects.filter(
        created_at__gte=timezone.now() - timedelta(days=days)
    )
    if symbol_filter:
        all_filtered = all_filtered.filter(symbol__symbol=symbol_filter)
    if timeframe_filter:
        all_filtered = all_filtered.filter(timeframe__name=timeframe_filter)
    if signal_filter:
        all_filtered = all_filtered.filter(signal=signal_filter)

    stats = {
        'total': all_filtered.count(),
        'avg_confidence': round(all_filtered.aggregate(avg=Avg('confidence'))['avg'] or 0, 2),
        'signals': all_filtered.values('signal').annotate(count=Count('id')),
    }

    context = {
        'decisions': decisions,
        'symbols': symbols,
        'timeframes': timeframes,
        'signals': signals,
        'current_filters': {
            'symbol': symbol_filter,
            'timeframe': timeframe_filter,
            'signal': signal_filter,
            'days': days,
        },
        'stats': stats,
        'total_count': total_count,
        'page': page,
        'per_page': per_page,
        'has_next': total_count > end,
        'has_prev': page > 1,
    }

    return render(request, 'dashboard/history.html', context)


def live_monitor(request):
    """
    Live monitoring dashboard with real-time updates
    """
    # Get latest decisions
    latest_decisions = Decision.objects.select_related(
        'symbol', 'timeframe', 'market_type'
    ).order_by('-created_at')[:10]

    # Active symbols with latest prices
    active_symbols = Symbol.objects.filter(is_active=True)

    # System status
    last_decision = Decision.objects.order_by('-created_at').first()
    last_update = last_decision.created_at if last_decision else None

    # Get latest market data
    latest_market_data = {}
    for symbol in active_symbols:
        latest = MarketData.objects.filter(symbol=symbol).order_by('-created_at').first()
        if latest:
            latest_market_data[symbol.symbol] = {
                'close': float(latest.close),
                'volume': float(latest.volume),
                'timestamp': latest.timestamp,
            }

    context = {
        'latest_decisions': latest_decisions,
        'active_symbols': active_symbols,
        'last_update': last_update,
        'latest_market_data': latest_market_data,
    }

    return render(request, 'dashboard/live.html', context)


def decision_detail(request, decision_id):
    """
    Detailed view of a single decision
    Shows all features, contributions, regime context, consensus
    """
    decision = Decision.objects.select_related(
        'symbol', 'timeframe', 'market_type'
    ).get(id=decision_id)

    # Get feature contributions
    contributions = FeatureContribution.objects.filter(
        decision=decision
    ).select_related('feature').order_by('-contribution')

    # Parse regime context
    regime_context = decision.regime_context or {}

    # Parse top drivers
    top_drivers = decision.top_drivers or []

    # Parse invalidation conditions
    invalidation_conditions = decision.invalidation_conditions or []

    # Get consensus data from regime context
    consensus_data = {
        'percentage': regime_context.get('consensus_percentage', 0),
        'level': regime_context.get('consensus_level', 'UNKNOWN'),
        'explanation': regime_context.get('consensus_explanation', ''),
        'conflicts': regime_context.get('consensus_conflicts', []),
    }

    # Calculate category breakdown
    category_breakdown = {}
    for contrib in contributions:
        cat = contrib.feature.category
        if cat not in category_breakdown:
            category_breakdown[cat] = {
                'total_contribution': 0,
                'features': [],
            }
        category_breakdown[cat]['total_contribution'] += float(contrib.contribution)
        category_breakdown[cat]['features'].append(contrib)

    context = {
        'decision': decision,
        'contributions': contributions,
        'regime_context': regime_context,
        'top_drivers': top_drivers,
        'invalidation_conditions': invalidation_conditions,
        'consensus_data': consensus_data,
        'category_breakdown': category_breakdown,
    }

    return render(request, 'dashboard/decision_detail.html', context)


# API Endpoints for AJAX/Charts

def api_decision_chart_data(request):
    """
    API endpoint for decision timeline chart
    Returns daily decision counts by signal type
    """
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    # Get decisions grouped by date and signal
    decisions = Decision.objects.filter(
        created_at__gte=start_date
    ).annotate(
        date=TruncDate('created_at')
    ).values('date', 'signal').annotate(
        count=Count('id')
    ).order_by('date', 'signal')

    # Organize data for charts
    dates = set()
    signal_data = {}

    for item in decisions:
        date_str = item['date'].strftime('%Y-%m-%d')
        dates.add(date_str)
        signal = item['signal']

        if signal not in signal_data:
            signal_data[signal] = {}

        signal_data[signal][date_str] = item['count']

    # Fill missing dates with 0
    dates = sorted(dates)
    for signal in signal_data:
        for date in dates:
            if date not in signal_data[signal]:
                signal_data[signal][date] = 0

    # Format for Chart.js
    datasets = []
    for signal, data in signal_data.items():
        datasets.append({
            'label': signal,
            'data': [data.get(date, 0) for date in dates],
        })

    return JsonResponse({
        'labels': dates,
        'datasets': datasets,
    })


def api_confidence_distribution(request):
    """
    API endpoint for confidence distribution histogram
    """
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    decisions = Decision.objects.filter(created_at__gte=start_date)

    # Create bins: 0-50, 50-60, 60-70, 70-80, 80-90, 90-100
    bins = [
        (0, 50, '0-50%'),
        (50, 60, '50-60%'),
        (60, 70, '60-70%'),
        (70, 80, '70-80%'),
        (80, 90, '80-90%'),
        (90, 100, '90-100%'),
    ]

    data = []
    for low, high, label in bins:
        count = decisions.filter(
            confidence__gte=low,
            confidence__lt=high
        ).count()
        data.append(count)

    return JsonResponse({
        'labels': [b[2] for b in bins],
        'data': data,
    })


def api_feature_power_chart(request):
    """
    API endpoint for feature power comparison
    Returns top N features by power
    """
    limit = int(request.GET.get('limit', 15))
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    # Get feature contributions
    feature_power = FeatureContribution.objects.filter(
        decision__created_at__gte=start_date
    ).values('feature__name', 'feature__category').annotate(
        avg_contribution=Avg('contribution'),
        total_usage=Count('id')
    ).order_by('-total_usage')[:limit]

    labels = []
    positive_data = []
    negative_data = []
    categories = []

    for item in feature_power:
        labels.append(item['feature__name'])
        categories.append(item['feature__category'])

        contrib = float(item['avg_contribution'])
        if contrib > 0:
            positive_data.append(abs(contrib))
            negative_data.append(0)
        else:
            positive_data.append(0)
            negative_data.append(abs(contrib))

    return JsonResponse({
        'labels': labels,
        'datasets': [
            {
                'label': 'Bullish Power',
                'data': positive_data,
                'backgroundColor': 'rgba(34, 197, 94, 0.7)',
            },
            {
                'label': 'Bearish Power',
                'data': negative_data,
                'backgroundColor': 'rgba(239, 68, 68, 0.7)',
            }
        ],
        'categories': categories,
    })


def api_consensus_breakdown(request):
    """
    API endpoint for consensus level breakdown
    """
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    decisions = Decision.objects.filter(created_at__gte=start_date)

    # Extract consensus level from regime_context
    consensus_levels = {
        'STRONG_CONSENSUS': 0,
        'MODERATE_CONSENSUS': 0,
        'WEAK_CONSENSUS': 0,
        'NO_CONSENSUS': 0,
        'UNKNOWN': 0,
    }

    for decision in decisions:
        regime_context = decision.regime_context or {}
        level = regime_context.get('consensus_level', 'UNKNOWN')
        if level in consensus_levels:
            consensus_levels[level] += 1
        else:
            consensus_levels['UNKNOWN'] += 1

    return JsonResponse({
        'labels': list(consensus_levels.keys()),
        'data': list(consensus_levels.values()),
    })


def api_live_updates(request):
    """
    API endpoint for live updates
    Returns latest decisions since last_id
    """
    last_id = int(request.GET.get('last_id', 0))

    new_decisions = Decision.objects.filter(
        id__gt=last_id
    ).select_related(
        'symbol', 'timeframe', 'market_type'
    ).order_by('created_at')[:20]

    data = []
    for decision in new_decisions:
        data.append({
            'id': decision.id,
            'timestamp': decision.created_at.isoformat(),
            'symbol': decision.symbol.symbol,
            'timeframe': decision.timeframe.name,
            'signal': decision.signal,
            'bias': decision.bias,
            'confidence': decision.confidence,
            'entry_price': str(decision.entry_price) if decision.entry_price else None,
        })

    return JsonResponse({
        'decisions': data,
        'latest_id': new_decisions.last().id if new_decisions.exists() else last_id,
    })


def api_symbol_performance(request, symbol):
    """
    API endpoint for individual symbol performance
    """
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    decisions = Decision.objects.filter(
        symbol__symbol=symbol,
        created_at__gte=start_date
    ).order_by('created_at')

    # Get market data
    market_data = MarketData.objects.filter(
        symbol__symbol=symbol,
        created_at__gte=start_date
    ).order_by('created_at')

    # Format data
    decision_data = []
    for d in decisions:
        decision_data.append({
            'timestamp': d.created_at.isoformat(),
            'signal': d.signal,
            'confidence': d.confidence,
            'entry_price': str(d.entry_price) if d.entry_price else None,
        })

    price_data = []
    for md in market_data:
        price_data.append({
            'timestamp': md.timestamp.isoformat(),
            'close': float(md.close),
            'volume': float(md.volume),
        })

    return JsonResponse({
        'decisions': decision_data,
        'prices': price_data,
    })
