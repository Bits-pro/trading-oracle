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
    MarketData, FeatureContribution, SymbolPerformance
)
from oracle.providers import BinanceProvider, YFinanceProvider


def sanitize_for_json(data):
    """
    Recursively convert all boolean and numpy values to JSON-serializable types
    Django JSONField cannot serialize Python bool objects or numpy types
    """
    import numpy as np

    # Handle numpy boolean types (np.bool_, np.True_, np.False_)
    if isinstance(data, (bool, np.bool_)):
        return 'YES' if data else 'NO'
    # Handle numpy numeric types (np.int64, np.float64, etc.)
    elif isinstance(data, (np.integer, np.floating)):
        return float(data)
    elif isinstance(data, dict):
        return {key: sanitize_for_json(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [sanitize_for_json(item) for item in data]
    else:
        return data


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

    # Get latest ROI data for active symbols
    symbol_performance = []
    for symbol in Symbol.objects.filter(is_active=True):
        latest_perf = SymbolPerformance.objects.filter(symbol=symbol).order_by('-timestamp').first()
        if latest_perf:
            symbol_performance.append({
                'symbol': symbol.symbol,
                'asset_type': symbol.asset_type,
                'current_price': latest_perf.current_price,
                'roi_1h': latest_perf.roi_1h,
                'roi_1d': latest_perf.roi_1d,
                'roi_1w': latest_perf.roi_1w,
                'roi_1m': latest_perf.roi_1m,
                'roi_1y': latest_perf.roi_1y,
                'volume_24h': latest_perf.volume_24h,
                'volatility_24h': latest_perf.volatility_24h,
            })

    context = {
        'total_decisions': total_decisions,
        'decisions_24h': decisions_24h,
        'active_symbols': active_symbols,
        'avg_confidence': round(avg_confidence, 2),
        'signal_distribution': signal_distribution,
        'recent_decisions': recent_decisions,
        'performance_by_tf': performance_by_tf,
        'top_symbols': top_symbols,
        'symbol_performance': symbol_performance,
    }

    return render(request, 'dashboard/home.html', context)


def feature_analysis(request):
    """
    Feature analysis dashboard
    Shows power, effect, and accuracy for each feature
    """
    # Get filter parameters
    category_filter = request.GET.get('category', '')
    show_all = request.GET.get('show_all', '0') == '1'

    # Get time range
    days = int(request.GET.get('days', 30))
    start_date = timezone.now() - timedelta(days=days)

    # Get all features
    features = Feature.objects.filter(is_active=True)

    if category_filter:
        features = features.filter(category=category_filter)

    # Calculate statistics for each feature
    feature_stats = []

    for feature in features:
        # Get recent contributions - use select_related for performance
        contributions = FeatureContribution.objects.filter(
            feature=feature,
            decision__created_at__gte=start_date
        ).select_related('decision')

        # Skip features with no contributions unless show_all is True
        if not contributions.exists() and not show_all:
            continue

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

            # Get decisions using this feature (optimized count)
            decisions_count = Decision.objects.filter(
                feature_contributions__feature=feature,
                created_at__gte=start_date
            ).distinct().count()

            # Get latest raw value
            latest_contribution = contributions.order_by('-decision__created_at').first()
            latest_value = latest_contribution.raw_value if latest_contribution else None
            latest_explanation = latest_contribution.explanation if latest_contribution else None

            feature_stats.append({
                'feature': feature,
                'power': round(power, 4),
                'effect': effect,
                'effect_strength': round(effect_strength, 1),
                'avg_contribution': round(avg_contribution, 4),
                'latest_value': latest_value,
                'latest_explanation': latest_explanation,
                'usage_count': total_count,
                'decisions_count': decisions_count,
                'positive_count': positive_count,
                'negative_count': negative_count,
                'neutral_count': total_count - positive_count - negative_count,
            })
        else:
            # Feature with no contributions (only if show_all)
            feature_stats.append({
                'feature': feature,
                'power': 0,
                'effect': 'N/A',
                'effect_strength': 0,
                'avg_contribution': 0,
                'latest_value': None,
                'latest_explanation': 'No data available',
                'usage_count': 0,
                'decisions_count': 0,
                'positive_count': 0,
                'negative_count': 0,
                'neutral_count': 0,
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

    # Get available categories for filter
    all_categories = Feature.objects.filter(is_active=True).values_list('category', flat=True).distinct()

    context = {
        'feature_stats': feature_stats,
        'categories': categories,
        'total_features': len(feature_stats),
        'all_categories': sorted(all_categories),
        'category_filter': category_filter,
        'days': days,
        'show_all': show_all,
        'has_data': len(feature_stats) > 0,
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
    timeframes = Timeframe.objects.all().order_by('display_order', 'minutes')
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


def _build_latest_market_data(symbols, include_provider=False):
    latest_market_data = {}
    crypto_provider = BinanceProvider() if include_provider else None
    traditional_provider = YFinanceProvider() if include_provider else None

    for symbol in symbols:
        latest = MarketData.objects.filter(symbol=symbol).order_by('-created_at').first()
        if latest:
            latest_market_data[symbol.symbol] = {
                'close': float(latest.close),
                'volume': float(latest.volume),
                'timestamp': latest.timestamp,
                'source': 'market',
            }
            continue

        if include_provider:
            try:
                if symbol.asset_type == 'CRYPTO' or symbol.quote_currency == 'USDT':
                    provider_symbol = f"{symbol.base_currency}/{symbol.quote_currency}"
                    ticker = crypto_provider.fetch_ticker(provider_symbol)
                    if ticker.get('last_price') is not None:
                        latest_market_data[symbol.symbol] = {
                            'close': float(ticker['last_price']),
                            'volume': float(ticker['volume_24h']) if ticker.get('volume_24h') else None,
                            'timestamp': ticker.get('timestamp'),
                            'source': 'provider',
                        }
                        continue
                else:
                    df = traditional_provider.fetch_ohlcv(symbol.symbol, '1d', limit=1)
                    if not df.empty:
                        latest_row = df.iloc[-1]
                        latest_market_data[symbol.symbol] = {
                            'close': float(latest_row['close']),
                            'volume': float(latest_row['volume']) if latest_row.get('volume') else None,
                            'timestamp': latest_row['timestamp'],
                            'source': 'provider',
                        }
                        continue
            except Exception:
                pass

        latest_decision = Decision.objects.filter(symbol=symbol).order_by('-created_at').first()
        if latest_decision and latest_decision.entry_price is not None:
            latest_market_data[symbol.symbol] = {
                'close': float(latest_decision.entry_price),
                'volume': None,
                'timestamp': latest_decision.created_at,
                'source': 'decision',
            }

    return latest_market_data


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
    latest_market_data = _build_latest_market_data(active_symbols, include_provider=False)

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


def api_live_market_data(request):
    """
    API endpoint for live market card updates
    """
    symbols_param = request.GET.get('symbols')
    active_symbols = Symbol.objects.filter(is_active=True)
    if symbols_param:
        symbols_list = [s.strip() for s in symbols_param.split(',') if s.strip()]
        active_symbols = active_symbols.filter(symbol__in=symbols_list)

    latest_market_data = _build_latest_market_data(active_symbols, include_provider=True)

    payload = {}
    for symbol, data in latest_market_data.items():
        payload[symbol] = {
            'close': data.get('close'),
            'volume': data.get('volume'),
            'timestamp': data.get('timestamp').isoformat() if data.get('timestamp') else None,
            'source': data.get('source'),
        }

    return JsonResponse({
        'data': payload,
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


def api_run_analysis(request):
    """
    API endpoint to trigger analysis
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)

    # Get parameters
    symbols = request.POST.getlist('symbols[]')
    timeframes = request.POST.getlist('timeframes[]')
    market_types = request.POST.getlist('market_types[]')

    # Default values if not provided
    if not symbols:
        symbols = ['BTCUSDT', 'XAUUSD']
    if not timeframes:
        timeframes = ['1h', '4h', '1d']
    if not market_types:
        market_types = ['SPOT']

    # Import here to avoid circular imports
    from oracle.providers import BinanceProvider, YFinanceProvider, MacroDataProvider
    from oracle.providers.news_provider import NewsSentimentProvider
    from oracle.engine import DecisionEngine
    import logging

    logger = logging.getLogger(__name__)

    # Get database objects
    symbol_objects = Symbol.objects.filter(symbol__in=symbols, is_active=True)
    if not symbol_objects.exists():
        return JsonResponse({'error': 'No active symbols found'}, status=400)

    timeframe_objects = Timeframe.objects.filter(name__in=timeframes)
    if not timeframe_objects.exists():
        return JsonResponse({'error': 'No timeframes found'}, status=400)

    market_type_objects = MarketType.objects.filter(name__in=market_types)
    if not market_type_objects.exists():
        return JsonResponse({'error': 'No market types found'}, status=400)

    try:
        # Initialize providers
        crypto_provider = BinanceProvider()
        traditional_provider = YFinanceProvider()
        macro_provider = MacroDataProvider()
        news_provider = NewsSentimentProvider()

        # Fetch macro data
        logger.info("Fetching macro data...")
        try:
            macro_context = macro_provider.fetch_all_macro_indicators()
        except Exception as e:
            logger.warning(f"Error fetching macro data: {e}")
            macro_context = {}

        # Fetch intermarket data
        logger.info("Fetching intermarket data...")
        intermarket_context = {}
        intermarket_symbols = ['XAGUSD', 'COPPER', 'CRUDE', 'GLD', 'GDX']
        for sym in intermarket_symbols:
            try:
                df = traditional_provider.fetch_ohlcv(symbol=sym, timeframe='1d', limit=100)
                if not df.empty:
                    intermarket_context[sym] = df
            except Exception as e:
                logger.warning(f"Error fetching {sym}: {e}")

        # Fetch news sentiment
        logger.info("Fetching news sentiment...")
        try:
            sentiment_data = news_provider.fetch_sentiment(lookback_hours=24)
        except Exception as e:
            logger.warning(f"Error fetching news sentiment: {e}")
            sentiment_data = {'fear_index': 0.0, 'count': 0, 'urgency': 0.0}

        decisions_created = 0
        errors = []

        # Analyze each symbol
        for symbol in symbol_objects:
            # Determine provider
            if symbol.asset_type == 'CRYPTO':
                provider = crypto_provider
                provider_symbol = f"{symbol.base_currency}/{symbol.quote_currency}"
            else:
                provider = traditional_provider
                provider_symbol = symbol.symbol

            # Track if we should try fallback provider for gold
            fallback_provider = None
            fallback_symbol = None
            if symbol.asset_type == 'GOLD' and symbol.symbol == 'XAUUSD':
                # If YFinance fails for gold, we'll fallback to Binance PAXG/USDT
                fallback_provider = crypto_provider
                fallback_symbol = 'PAXG/USDT'

            for market_type in market_type_objects:
                for timeframe in timeframe_objects:
                    try:
                        # Fetch market data
                        df = provider.fetch_ohlcv(
                            symbol=provider_symbol,
                            timeframe=timeframe.name,
                            limit=500
                        )

                        # Try fallback provider if primary fails for gold
                        if df.empty and fallback_provider and fallback_symbol:
                            logger.info(f"YFinance failed for {symbol.symbol}, trying Binance {fallback_symbol} as fallback...")
                            try:
                                df = fallback_provider.fetch_ohlcv(
                                    symbol=fallback_symbol,
                                    timeframe=timeframe.name,
                                    limit=500
                                )
                                if not df.empty:
                                    logger.info(f"Fallback successful! Using {fallback_symbol} data for {symbol.symbol}")
                            except Exception as fallback_error:
                                logger.warning(f"Fallback also failed: {fallback_error}")

                        if df.empty:
                            continue

                        # Build context
                        context = {
                            'macro': macro_context,
                            'intermarket': intermarket_context,
                            'sentiment': sentiment_data
                        }

                        # Add derivatives data if applicable
                        if market_type.name in ['PERPETUAL', 'FUTURES'] and symbol.asset_type == 'CRYPTO':
                            try:
                                funding = provider.fetch_funding_rate(provider_symbol)
                                oi = provider.fetch_open_interest(provider_symbol)

                                import pandas as pd
                                context['derivatives'] = {
                                    'funding_rate': pd.DataFrame([{
                                        'timestamp': funding['next_funding_time'] or timezone.now(),
                                        'rate': funding['rate']
                                    }]),
                                    'open_interest': pd.DataFrame([{
                                        'timestamp': oi['timestamp'],
                                        'value': oi['open_interest']
                                    }]),
                                    'mark_price': funding.get('mark_price'),
                                    'index_price': funding.get('index_price'),
                                }
                            except Exception as e:
                                logger.warning(f"Error fetching derivatives: {e}")

                        # Run decision engine
                        engine = DecisionEngine(
                            symbol=symbol.symbol,
                            market_type=market_type.name,
                            timeframe=timeframe.name
                        )

                        decision_output = engine.generate_decision(df, context)

                        # Prepare sanitized data
                        sanitized_invalidation = sanitize_for_json(decision_output.invalidation_conditions)
                        sanitized_top_drivers = sanitize_for_json([d for d in decision_output.top_drivers])
                        sanitized_regime = sanitize_for_json(decision_output.regime_context)

                        # Debug: Check for any remaining booleans
                        import json as json_lib
                        try:
                            json_lib.dumps(sanitized_invalidation)
                            json_lib.dumps(sanitized_top_drivers)
                            json_lib.dumps(sanitized_regime)
                        except TypeError as je:
                            logger.error(f"JSON serialization test failed: {je}")
                            logger.error(f"invalidation: {sanitized_invalidation}")
                            logger.error(f"top_drivers: {sanitized_top_drivers}")
                            logger.error(f"regime: {sanitized_regime}")
                            raise

                        # Save decision (using pre-sanitized data)
                        decision = Decision.objects.create(
                            symbol=symbol,
                            market_type=market_type,
                            timeframe=timeframe,
                            signal=decision_output.signal,
                            bias=decision_output.bias,
                            confidence=decision_output.confidence,
                            entry_price=decision_output.entry_price,
                            stop_loss=decision_output.stop_loss,
                            take_profit=decision_output.take_profit,
                            risk_reward=decision_output.risk_reward,
                            invalidation_conditions=sanitized_invalidation,
                            top_drivers=sanitized_top_drivers,
                            raw_score=decision_output.raw_score,
                            regime_context=sanitized_regime
                        )

                        # Create FeatureContribution records for all features
                        for feature_result in decision_output.all_features:
                            # Get or create the Feature record
                            feature, _ = Feature.objects.get_or_create(
                                name=feature_result.name,
                                defaults={
                                    'category': feature_result.category,
                                    'description': feature_result.explanation[:200] if feature_result.explanation else '',
                                }
                            )

                            # Find this feature's contribution from top_drivers
                            contribution_data = next(
                                (d for d in sanitized_top_drivers if d['name'] == feature_result.name),
                                None
                            )

                            if contribution_data:
                                FeatureContribution.objects.create(
                                    decision=decision,
                                    feature=feature,
                                    raw_value=contribution_data['raw_value'],
                                    direction=contribution_data['direction'],
                                    strength=contribution_data['strength'],
                                    weight=contribution_data['weight'],
                                    contribution=contribution_data['contribution'],
                                    explanation=contribution_data['explanation']
                                )

                        decisions_created += 1

                    except Exception as e:
                        error_msg = f'Error analyzing {symbol.symbol} {market_type.name} {timeframe.name}: {str(e)}'
                        logger.exception(f"Full traceback for {symbol.symbol} {market_type.name} {timeframe.name}")
                        errors.append(error_msg)

        return JsonResponse({
            'success': True,
            'decisions_created': decisions_created,
            'errors': errors
        })

    except Exception as e:
        logger.exception("Error running analysis")
        return JsonResponse({'error': str(e)}, status=500)


def indicators_overview(request):
    """
    Show current indicator values and power for each symbol
    Displays all features with their values, direction, and contribution
    """
    # Get filter parameters
    symbol_filter = request.GET.get('symbol', '')
    timeframe_filter = request.GET.get('timeframe', '1h')
    market_type_filter = request.GET.get('market_type', 'SPOT')

    # Get latest decisions for each symbol
    symbols = Symbol.objects.filter(is_active=True)
    if symbol_filter:
        symbols = symbols.filter(symbol=symbol_filter)

    symbol_data = []

    for symbol in symbols:
        # Get the most recent decision for this symbol
        latest_decision = Decision.objects.filter(
            symbol=symbol,
            timeframe__name=timeframe_filter,
            market_type__name=market_type_filter
        ).select_related('timeframe', 'market_type').order_by('-created_at').first()

        if not latest_decision:
            continue

        # Get all feature contributions for this decision
        contributions = FeatureContribution.objects.filter(
            decision=latest_decision
        ).select_related('feature').order_by('-contribution')

        # Organize by category
        categories = {}
        for contrib in contributions:
            cat = contrib.feature.category
            if cat not in categories:
                categories[cat] = []

            categories[cat].append({
                'name': contrib.feature.name,
                'value': contrib.raw_value,
                'direction': 'BULLISH' if contrib.contribution > 0 else ('BEARISH' if contrib.contribution < 0 else 'NEUTRAL'),
                'contribution': float(contrib.contribution),
                'power': abs(float(contrib.contribution)),
                'explanation': contrib.explanation,
                'metadata': {}  # Metadata not stored in FeatureContribution model
            })

        symbol_data.append({
            'symbol': symbol,
            'decision': latest_decision,
            'categories': categories,
            'total_contributions': len(contributions)
        })

    # Get available symbols, timeframes, market types for filters
    all_symbols = Symbol.objects.filter(is_active=True).order_by('symbol')
    all_timeframes = Timeframe.objects.all().order_by('name')
    all_market_types = MarketType.objects.all().order_by('name')

    context = {
        'symbol_data': symbol_data,
        'symbol_filter': symbol_filter,
        'timeframe_filter': timeframe_filter,
        'market_type_filter': market_type_filter,
        'all_symbols': all_symbols,
        'all_timeframes': all_timeframes,
        'all_market_types': all_market_types,
    }

    return render(request, 'dashboard/indicators.html', context)
