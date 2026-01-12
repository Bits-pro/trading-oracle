"""
Health Check API for Trading Oracle
Monitors system components and dependencies
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status as http_status
from django.db import connection
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
import time


@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Comprehensive health check endpoint

    Checks:
    - Database connectivity
    - Redis cache availability
    - Recent analysis runs
    - Data freshness
    - Feature availability

    Returns:
    - 200 OK if all systems healthy
    - 503 Service Unavailable if critical systems down
    - 207 Multi-Status if some systems degraded
    """
    checks = {
        'database': _check_database(),
        'cache': _check_cache(),
        'celery_broker': _check_redis_broker(),
        'recent_data': _check_recent_data(),
        'features': _check_features(),
    }

    # Determine overall health status
    critical_checks = ['database', 'cache']
    critical_failed = any(not checks[check]['healthy'] for check in critical_checks)

    any_failed = any(not check['healthy'] for check in checks.values())

    if critical_failed:
        status_code = http_status.HTTP_503_SERVICE_UNAVAILABLE
        overall_status = 'CRITICAL'
    elif any_failed:
        status_code = http_status.HTTP_207_MULTI_STATUS
        overall_status = 'DEGRADED'
    else:
        status_code = http_status.HTTP_200_OK
        overall_status = 'HEALTHY'

    response_data = {
        'status': overall_status,
        'timestamp': timezone.now().isoformat(),
        'checks': checks,
        'summary': {
            'total_checks': len(checks),
            'passed': sum(1 for c in checks.values() if c['healthy']),
            'failed': sum(1 for c in checks.values() if not c['healthy']),
        }
    }

    return Response(response_data, status=status_code)


@api_view(['GET'])
@permission_classes([AllowAny])
def readiness_check(request):
    """
    Kubernetes-style readiness probe

    Checks if the application is ready to serve traffic
    Returns 200 if ready, 503 if not
    """
    checks = {
        'database': _check_database(),
        'cache': _check_cache(),
    }

    all_ready = all(check['healthy'] for check in checks.values())

    if all_ready:
        return Response({'status': 'ready'}, status=http_status.HTTP_200_OK)
    else:
        return Response(
            {'status': 'not_ready', 'checks': checks},
            status=http_status.HTTP_503_SERVICE_UNAVAILABLE
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def liveness_check(request):
    """
    Kubernetes-style liveness probe

    Simple check to verify the application is alive
    Returns 200 if alive
    """
    return Response({'status': 'alive'}, status=http_status.HTTP_200_OK)


def _check_database():
    """Check database connectivity and performance"""
    try:
        start = time.time()

        # Test database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        latency_ms = (time.time() - start) * 1000

        # Check if database is slow
        healthy = latency_ms < 100  # Warn if query takes > 100ms

        return {
            'healthy': healthy,
            'latency_ms': round(latency_ms, 2),
            'status': 'healthy' if healthy else 'slow',
            'message': f'Database responding in {latency_ms:.2f}ms'
        }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'error',
            'message': f'Database check failed: {str(e)}'
        }


def _check_cache():
    """Check Redis cache availability"""
    try:
        start = time.time()

        # Test cache write/read
        cache_key = 'health_check_test'
        cache_value = str(timezone.now().timestamp())
        cache.set(cache_key, cache_value, timeout=10)
        retrieved = cache.get(cache_key)

        latency_ms = (time.time() - start) * 1000

        if retrieved != cache_value:
            raise Exception("Cache read/write mismatch")

        # Clean up
        cache.delete(cache_key)

        healthy = latency_ms < 50  # Redis should be very fast

        return {
            'healthy': healthy,
            'latency_ms': round(latency_ms, 2),
            'status': 'healthy' if healthy else 'slow',
            'message': f'Cache responding in {latency_ms:.2f}ms'
        }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'error',
            'message': f'Cache check failed: {str(e)}'
        }


def _check_redis_broker():
    """Check Redis broker (Celery) availability"""
    try:
        import redis
        from django.conf import settings

        start = time.time()

        # Parse Redis URL
        redis_url = settings.CELERY_BROKER_URL
        r = redis.from_url(redis_url)
        r.ping()

        latency_ms = (time.time() - start) * 1000

        healthy = latency_ms < 50

        return {
            'healthy': healthy,
            'latency_ms': round(latency_ms, 2),
            'status': 'healthy' if healthy else 'slow',
            'message': f'Redis broker responding in {latency_ms:.2f}ms'
        }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'error',
            'message': f'Redis broker check failed: {str(e)}'
        }


def _check_recent_data():
    """Check if market data is recent"""
    try:
        from oracle.models import MarketData, Decision

        # Check for recent market data (within last 2 hours)
        two_hours_ago = timezone.now() - timedelta(hours=2)
        recent_data_count = MarketData.objects.filter(
            timestamp__gte=two_hours_ago
        ).count()

        # Check for recent decisions (within last 6 hours)
        six_hours_ago = timezone.now() - timedelta(hours=6)
        recent_decisions_count = Decision.objects.filter(
            created_at__gte=six_hours_ago
        ).count()

        # Consider healthy if we have recent data
        healthy = recent_data_count > 0 and recent_decisions_count > 0

        return {
            'healthy': healthy,
            'status': 'healthy' if healthy else 'stale',
            'recent_market_data_count': recent_data_count,
            'recent_decisions_count': recent_decisions_count,
            'message': f'{recent_market_data_count} market data points, {recent_decisions_count} decisions in last period'
        }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'error',
            'message': f'Data freshness check failed: {str(e)}'
        }


def _check_features():
    """Check feature registry health"""
    try:
        from oracle.models import Feature

        # Get active features count
        active_features = Feature.objects.filter(is_active=True).count()
        total_features = Feature.objects.count()

        # Should have at least 30 active features for good coverage
        healthy = active_features >= 30

        return {
            'healthy': healthy,
            'status': 'healthy' if healthy else 'degraded',
            'active_features': active_features,
            'total_features': total_features,
            'message': f'{active_features}/{total_features} features active'
        }
    except Exception as e:
        return {
            'healthy': False,
            'status': 'error',
            'message': f'Feature check failed: {str(e)}'
        }
