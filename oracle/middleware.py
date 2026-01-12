"""
Middleware for Trading Oracle
Includes query profiling and performance monitoring
"""
import time
import logging
from django.db import connection
from django.conf import settings

logger = logging.getLogger(__name__)


class QueryCountMiddleware:
    """
    Middleware to track query count and execution time per request
    Logs warnings for slow queries and excessive query counts
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.slow_query_threshold = getattr(settings, 'SLOW_QUERY_THRESHOLD_MS', 100)
        self.max_queries_threshold = getattr(settings, 'MAX_QUERIES_PER_REQUEST', 50)

    def __call__(self, request):
        # Get initial query count
        initial_queries = len(connection.queries)

        # Start timer
        start_time = time.time()

        # Process request
        response = self.get_response(request)

        # Calculate metrics
        end_time = time.time()
        total_time = (end_time - start_time) * 1000  # Convert to ms

        # Get final query count
        final_queries = len(connection.queries)
        num_queries = final_queries - initial_queries

        # Log slow queries
        if settings.DEBUG:
            slow_queries = []
            for query in connection.queries[initial_queries:]:
                query_time = float(query['time']) * 1000  # Convert to ms
                if query_time > self.slow_query_threshold:
                    slow_queries.append({
                        'sql': query['sql'][:200],  # Truncate long queries
                        'time_ms': round(query_time, 2)
                    })

            # Log if there are slow queries
            if slow_queries:
                logger.warning(
                    f"Slow queries detected on {request.path}: "
                    f"{len(slow_queries)} queries > {self.slow_query_threshold}ms"
                )
                for sq in slow_queries[:5]:  # Log first 5 slow queries
                    logger.warning(f"  {sq['time_ms']}ms: {sq['sql']}")

            # Log excessive query counts
            if num_queries > self.max_queries_threshold:
                logger.warning(
                    f"Excessive queries on {request.path}: "
                    f"{num_queries} queries (threshold: {self.max_queries_threshold})"
                )

        # Add metrics to response headers (useful for monitoring)
        response['X-Query-Count'] = num_queries
        response['X-Response-Time-Ms'] = round(total_time, 2)

        # Log request summary for performance tracking
        if num_queries > 0:
            logger.info(
                f"{request.method} {request.path} - "
                f"{num_queries} queries, {round(total_time, 2)}ms"
            )

        return response


class FeaturePerformanceMiddleware:
    """
    Middleware to track feature calculation performance
    Stores metrics in database for analysis
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response


class SystemMetricsMiddleware:
    """
    Middleware to collect system-wide metrics
    Periodically saves to SystemMetrics model
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.request_count = 0
        self.query_times = []

    def __call__(self, request):
        initial_queries = len(connection.queries) if settings.DEBUG else 0
        start_time = time.time()

        response = self.get_response(request)

        if settings.DEBUG:
            # Calculate query metrics
            final_queries = len(connection.queries)
            num_queries = final_queries - initial_queries

            # Track query times
            for query in connection.queries[initial_queries:]:
                query_time = float(query['time']) * 1000
                self.query_times.append(query_time)

            self.request_count += 1

            # Every 100 requests, save metrics to database
            if self.request_count % 100 == 0:
                self._save_metrics()

        return response

    def _save_metrics(self):
        """Save collected metrics to SystemMetrics model"""
        if not self.query_times:
            return

        try:
            from oracle.models import SystemMetrics

            # Calculate statistics
            avg_query_time = sum(self.query_times) / len(self.query_times)
            slow_query_count = sum(1 for qt in self.query_times if qt > 100)

            # Save metrics
            SystemMetrics.objects.create(
                provider_name='django_orm',
                total_queries=len(self.query_times),
                avg_query_time_ms=avg_query_time,
                slow_query_count=slow_query_count
            )

            # Reset counters
            self.query_times = []
            self.request_count = 0

        except Exception as e:
            logger.error(f"Failed to save system metrics: {e}")
