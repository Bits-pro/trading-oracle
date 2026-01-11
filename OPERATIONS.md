# Production Operations Guide

## 🚀 Pre-Deployment Checklist

### Security Hardening

- [ ] Change `SECRET_KEY` in production (use `python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'`)
- [ ] Set `DEBUG = False` in production
- [ ] Configure `ALLOWED_HOSTS` with your domain
- [ ] Set up SSL/TLS certificates (Let's Encrypt recommended)
- [ ] Configure CORS properly (restrict to trusted domains)
- [ ] Set up firewall rules (only expose ports 80, 443)
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Enable Django security middleware settings
- [ ] Set secure cookie flags
- [ ] Configure Content Security Policy headers

### Database Setup

```bash
# Create PostgreSQL database
sudo -u postgres psql
CREATE DATABASE trading_oracle;
CREATE USER oracle_user WITH PASSWORD 'secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE trading_oracle TO oracle_user;
\q

# Update DATABASE_URL in .env
DATABASE_URL=postgresql://oracle_user:secure_password_here@localhost:5432/trading_oracle

# Run migrations
python manage.py migrate
python manage.py init_oracle
python manage.py createsuperuser
```

### Redis Setup

```bash
# Install Redis
sudo apt install redis-server

# Configure Redis for production
sudo nano /etc/redis/redis.conf
# Set: maxmemory 2gb
# Set: maxmemory-policy allkeys-lru

# Enable Redis to start on boot
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Static Files & Media

```bash
# Create directories
sudo mkdir -p /var/www/trading-oracle/static
sudo mkdir -p /var/www/trading-oracle/media
sudo chown -R www-data:www-data /var/www/trading-oracle

# Collect static files
python manage.py collectstatic --no-input
```

### Log Directories

```bash
# Create log directories
sudo mkdir -p /var/log/trading-oracle
sudo chown -R oracle:oracle /var/log/trading-oracle
```

---

## 📊 Performance Optimization

### Database Optimization

```python
# settings.py additions for production

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'trading_oracle',
        'USER': 'oracle_user',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
        'CONN_MAX_AGE': 600,  # Keep connections open
        'OPTIONS': {
            'connect_timeout': 10,
        },
    }
}

# Database connection pooling
DATABASES['default']['OPTIONS']['pool'] = {
    'min_size': 2,
    'max_size': 10,
}
```

### Caching Strategy

```python
# settings.py - Add caching

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': 'redis://127.0.0.1:6379/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'trading_oracle',
        'TIMEOUT': 300,  # 5 minutes default
    }
}

# Cache API responses
REST_FRAMEWORK = {
    'DEFAULT_CACHE': 'default',
    'DEFAULT_CACHE_TIMEOUT': 300,
}
```

### Query Optimization

```python
# In views.py - Add select_related and prefetch_related

# Bad (N+1 queries)
decisions = Decision.objects.all()

# Good (optimized)
decisions = Decision.objects.select_related(
    'symbol', 'market_type', 'timeframe'
).prefetch_related(
    'feature_contributions__feature'
).order_by('-created_at')[:100]
```

### Celery Optimization

```bash
# Use multiple workers
celery -A trading_oracle worker -l info --concurrency=4

# Use separate queues for priority
celery -A trading_oracle worker -Q high_priority,default -l info

# Enable autoscaling
celery -A trading_oracle worker --autoscale=10,3
```

---

## 🔍 Monitoring & Alerting

### System Monitoring

```bash
# Install monitoring tools
pip install django-prometheus
pip install flower  # Celery monitoring

# Add to INSTALLED_APPS
INSTALLED_APPS = [
    ...
    'django_prometheus',
]

# Add to MIDDLEWARE (at the beginning)
MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]
```

### Flower (Celery Dashboard)

```bash
# Start Flower
celery -A trading_oracle flower --port=5555

# Access at http://localhost:5555
# Add to supervisor config for production
```

### Health Check Endpoint

```python
# oracle/api/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.db import connection

@api_view(['GET'])
def health_check(request):
    """Health check endpoint for monitoring"""
    try:
        # Check database
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")

        # Check Redis
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)

        return Response({
            'status': 'healthy',
            'database': 'ok',
            'cache': 'ok',
        })
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=500)
```

### Error Tracking (Sentry)

```bash
pip install sentry-sdk
```

```python
# settings.py

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration

sentry_sdk.init(
    dsn="your-sentry-dsn",
    integrations=[DjangoIntegration()],
    traces_sample_rate=1.0,
    send_default_pii=True
)
```

### Uptime Monitoring

Use external services:
- UptimeRobot (free tier available)
- Pingdom
- StatusCake

Monitor endpoints:
- `https://yourdomain.com/api/health/`
- `https://yourdomain.com/admin/`

---

## 📈 Performance Metrics to Track

### Application Metrics

```python
# Track in your code
from django.core.cache import cache
import time

def track_decision_time(symbol, timeframe):
    start = time.time()
    # ... decision logic ...
    duration = time.time() - start

    # Store metric
    cache.set(f'decision_time:{symbol}:{timeframe}', duration, 3600)
```

### Database Metrics

```sql
-- Check slow queries (PostgreSQL)
SELECT
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;

-- Check table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Celery Metrics

```bash
# Monitor via Flower or custom script
celery -A trading_oracle inspect stats

# Key metrics to track:
# - Task success rate
# - Average task duration
# - Queue length
# - Worker memory usage
```

---

## 🔐 Security Best Practices

### API Rate Limiting

```bash
pip install django-ratelimit
```

```python
# oracle/api/views.py

from django_ratelimit.decorators import ratelimit

@ratelimit(key='ip', rate='100/h', method='POST')
def analyze(request):
    # ... analysis logic ...
    pass
```

### API Authentication (Optional)

```python
# For authenticated API access

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
}
```

### Database Backups

```bash
# Create backup script
cat > /usr/local/bin/backup-trading-oracle.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/var/backups/trading-oracle"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
pg_dump -U oracle_user trading_oracle | gzip > $BACKUP_DIR/db_$DATE.sql.gz

# Backup media files
tar -czf $BACKUP_DIR/media_$DATE.tar.gz /var/www/trading-oracle/media/

# Keep only last 7 days
find $BACKUP_DIR -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF

chmod +x /usr/local/bin/backup-trading-oracle.sh

# Add to crontab
crontab -e
# Add: 0 2 * * * /usr/local/bin/backup-trading-oracle.sh
```

---

## 🚨 Incident Response

### Common Issues & Solutions

#### High Memory Usage

```bash
# Check memory usage
free -h
top -u oracle

# Restart workers if needed
sudo supervisorctl restart trading_oracle:trading_oracle_celery_worker
```

#### Database Connection Errors

```bash
# Check PostgreSQL connections
sudo -u postgres psql -c "SELECT count(*) FROM pg_stat_activity;"

# Kill idle connections
sudo -u postgres psql trading_oracle << EOF
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'trading_oracle'
AND pid <> pg_backend_pid()
AND state = 'idle'
AND state_change < current_timestamp - INTERVAL '5 minutes';
EOF
```

#### Celery Tasks Stuck

```bash
# Inspect active tasks
celery -A trading_oracle inspect active

# Revoke stuck task
celery -A trading_oracle revoke <task-id>

# Purge all tasks and restart
celery -A trading_oracle purge
sudo supervisorctl restart trading_oracle:trading_oracle_celery_worker
```

#### High API Latency

```bash
# Check for slow queries
python manage.py shell
from django.db import connection
print(connection.queries)

# Enable query logging temporarily
# settings.py
LOGGING = {
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}
```

---

## 📊 Capacity Planning

### Expected Resource Usage

**For 10 symbols, 3 timeframes, hourly analysis:**

| Resource | Usage | Recommendation |
|----------|-------|----------------|
| CPU | 20-40% | 2-4 cores |
| RAM | 2-4 GB | 8 GB server |
| Disk | 10-50 GB | 100 GB SSD |
| Network | <1 GB/day | Standard |

**Scaling Guidelines:**

- **10-50 symbols**: Single server (4 cores, 8GB RAM)
- **50-200 symbols**: Add Celery workers (8 cores, 16GB RAM)
- **200+ symbols**: Consider multi-server setup with Redis Cluster

### Database Growth Estimates

```python
# Approximate storage per day:
# - Decisions: 10 symbols × 3 timeframes × 24 hours = 720 records/day
# - Average size: 2KB per decision = ~1.4 MB/day
# - With feature contributions: ~5 MB/day
# - Market data: ~20 MB/day
# - Total: ~30 MB/day or ~1 GB/month

# With default retention (90 days market data, 30 days decisions):
# Expected database size: ~3-5 GB
```

---

## 🎯 Performance Benchmarks

### Expected Performance

| Operation | Target Time | Notes |
|-----------|-------------|-------|
| Single decision generation | <2 seconds | With 50 features |
| Batch analysis (10 symbols) | <30 seconds | Parallel processing |
| API response (list) | <200ms | With caching |
| API response (single) | <100ms | Cached |
| Backtest (30 days) | 1-5 minutes | Depends on trade count |

### Optimization Targets

If performance is below targets:

1. **Enable caching** (API responses)
2. **Optimize queries** (use select_related)
3. **Add database indexes** (on frequently queried fields)
4. **Scale Celery workers** (add more workers)
5. **Use connection pooling** (pgbouncer for PostgreSQL)

---

## 📝 Maintenance Schedule

### Daily
- [ ] Check system health (`/api/health/`)
- [ ] Review error logs
- [ ] Monitor Celery task success rate

### Weekly
- [ ] Run backtest (`python manage.py backtest --days 7`)
- [ ] Check database size
- [ ] Review top API endpoints (slow queries)

### Monthly
- [ ] Full backtest (`python manage.py backtest --days 30 --export`)
- [ ] Optimize feature weights if needed
- [ ] Update dependencies (`pip list --outdated`)
- [ ] Review and clean old data

### Quarterly
- [ ] Security audit
- [ ] Performance review
- [ ] Feature weight optimization cycle
- [ ] Database maintenance (VACUUM, ANALYZE)

---

## 🔧 Troubleshooting Guide

### Decision Quality Issues

**Problem**: Win rate dropping below 50%

**Solution**:
```bash
# 1. Run backtest to identify issues
python manage.py backtest --days 30 --export

# 2. Check if specific signals are failing
# Look at CSV: signal column vs pnl_percent

# 3. Check confidence calibration
# High confidence should outperform low confidence

# 4. Review recent market regime
# Has ADX dropped? Is volatility high?

# 5. Adjust weights or filters
# Via Django Admin: Features > Adjust weights
```

**Problem**: Confidence not well calibrated

**Solution**:
```python
# Run this analysis
python manage.py shell

from oracle.models import Decision
from django.db.models import Avg

# Check avg confidence by signal
for signal in ['STRONG_BUY', 'BUY', 'WEAK_BUY']:
    avg_conf = Decision.objects.filter(signal=signal).aggregate(
        avg=Avg('confidence')
    )['avg']
    print(f"{signal}: {avg_conf:.1f}%")

# If BUY has same confidence as STRONG_BUY:
# → Increase thresholds in decision_engine.py Layer 2
```

### System Performance Issues

**Problem**: High latency on API calls

**Solutions**:
```bash
# 1. Enable caching
# settings.py: Add Django cache configuration

# 2. Add database indexes
python manage.py shell
from oracle.models import Decision
from django.db import connection
connection.queries  # See which queries are slow

# 3. Optimize queries
# Use select_related and prefetch_related

# 4. Scale horizontally
# Add more Gunicorn workers
```

**Problem**: Celery tasks timing out

**Solutions**:
```bash
# 1. Increase timeout
# celery.py: CELERY_TASK_TIME_LIMIT = 60 * 60  # 1 hour

# 2. Split large tasks
# Instead of analyzing 50 symbols at once, batch in groups of 10

# 3. Add more workers
celery -A trading_oracle worker --concurrency=8
```

---

## 📞 Getting Help

### Check Logs First

```bash
# Django
tail -f /var/log/trading-oracle/gunicorn-error.log

# Celery Worker
tail -f /var/log/trading-oracle/celery-worker.log

# Celery Beat
tail -f /var/log/trading-oracle/celery-beat.log

# Nginx
tail -f /var/log/nginx/trading-oracle-error.log
```

### Debug Mode (Development Only)

```python
# settings.py
DEBUG = True  # NEVER in production!

# Run with verbose output
python manage.py runserver --verbosity 3
```

### Database Console

```bash
# PostgreSQL
sudo -u postgres psql trading_oracle

# Check recent decisions
SELECT symbol_id, signal, confidence, created_at
FROM oracle_decision
ORDER BY created_at DESC
LIMIT 10;
```

---

## 🎓 Best Practices Summary

### Development
✅ Use virtual environments
✅ Keep requirements.txt updated
✅ Write tests for new features
✅ Use meaningful commit messages
✅ Run backtest before deploying changes

### Production
✅ Use PostgreSQL (not SQLite)
✅ Enable caching (Redis)
✅ Set up monitoring (Sentry + Flower)
✅ Configure backups (daily)
✅ Use environment variables (.env)
✅ Enable SSL/TLS
✅ Keep DEBUG=False

### Operations
✅ Monitor system health daily
✅ Run backtests weekly
✅ Optimize weights monthly
✅ Review logs regularly
✅ Keep dependencies updated
✅ Document configuration changes

### Trading
✅ Only trade high confidence (70%+)
✅ Never risk >2% per trade
✅ Use stop losses religiously
✅ Monitor invalidation conditions
✅ Diversify across symbols/timeframes
✅ Re-validate accuracy quarterly

---

**Last Updated**: 2026-01-10
**Version**: 1.0.0
