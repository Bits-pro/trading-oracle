# Trading Oracle - Quick Reference Guide

## 🚀 Quick Start (5 minutes)

```bash
# 1. Clone and setup
git clone <repo-url>
cd trading-oracle
./quickstart.sh

# 2. Start services (3 terminals)
python manage.py runserver              # Terminal 1
celery -A trading_oracle worker -l info # Terminal 2
celery -A trading_oracle beat -l info   # Terminal 3

# 3. Initialize data
python manage.py init_oracle

# 4. Run first analysis
python manage.py run_analysis --symbols BTCUSDT --verbose

# 5. Access
# Admin: http://localhost:8000/admin/
# API: http://localhost:8000/api/
```

---

## 📋 Essential Commands

### Management Commands

```bash
# Initialize database with default data
python manage.py init_oracle

# Run analysis manually
python manage.py run_analysis --symbols BTCUSDT ETHUSDT --timeframes 1h 4h

# Run backtest (validate accuracy)
python manage.py backtest --days 30 --export

# Create superuser
python manage.py createsuperuser

# Run migrations
python manage.py makemigrations
python manage.py migrate

# Collect static files (production)
python manage.py collectstatic --no-input

# Django shell
python manage.py shell
```

### Analysis Commands

```bash
# Analyze single symbol, single timeframe
python manage.py run_analysis --symbols BTCUSDT --timeframes 1h

# Analyze multiple symbols and timeframes
python manage.py run_analysis \
  --symbols BTCUSDT ETHUSDT XAUUSD \
  --timeframes 1h 4h 1d \
  --verbose

# Analyze specific market types
python manage.py run_analysis \
  --symbols BTCUSDT \
  --market-types SPOT PERPETUAL \
  --timeframes 4h
```

### Backtesting Commands

```bash
# Last 30 days
python manage.py backtest --days 30

# Last 90 days with export
python manage.py backtest --days 90 --export

# Specific symbols
python manage.py backtest --days 60 --symbols BTCUSDT XAUUSD

# Specific timeframes
python manage.py backtest --days 90 --timeframes 4h 1d
```

---

## 🔧 Celery Commands

### Worker Management

```bash
# Start worker
celery -A trading_oracle worker -l info

# Start with specific concurrency
celery -A trading_oracle worker -l info --concurrency=4

# Start beat scheduler
celery -A trading_oracle beat -l info

# Start both (development only)
celery -A trading_oracle worker -l info -B

# Flower (monitoring dashboard)
celery -A trading_oracle flower
# Access at: http://localhost:5555/
```

### Task Management

```bash
# List active tasks
celery -A trading_oracle inspect active

# Revoke task
celery -A trading_oracle revoke <task-id>

# Purge all tasks
celery -A trading_oracle purge

# Check registered tasks
celery -A trading_oracle inspect registered
```

---

## 🌐 API Quick Reference

### Base URL
```
http://localhost:8000/api/
```

### Endpoints

#### Symbols
```bash
# List all symbols
GET /api/symbols/

# Get specific symbol
GET /api/symbols/{id}/

# Filter by asset type
GET /api/symbols/?asset_type=CRYPTO

# Search
GET /api/symbols/?search=BTC
```

#### Decisions
```bash
# List recent decisions
GET /api/decisions/

# Latest decisions for all symbols
GET /api/decisions/latest/

# Decisions for specific symbol
GET /api/decisions/by_symbol/?symbol=BTCUSDT

# Filter by parameters
GET /api/decisions/?signal=BUY&confidence__gte=80&timeframe=1h

# Bulk query
GET /api/decisions/bulk/?symbols=BTCUSDT,ETHUSDT,XAUUSD

# Trigger new analysis
POST /api/decisions/analyze/
{
  "symbols": ["BTCUSDT", "XAUUSD"],
  "market_types": ["SPOT"],
  "timeframes": ["1h", "4h", "1d"]
}
```

#### Features
```bash
# List all features
GET /api/features/

# Filter by category
GET /api/features/?category=TECHNICAL

# Search features
GET /api/features/?search=RSI
```

#### Analysis Runs
```bash
# List analysis runs
GET /api/analysis-runs/

# Get specific run
GET /api/analysis-runs/{run_id}/

# Get decisions from run
GET /api/analysis-runs/{run_id}/decisions/
```

### cURL Examples

```bash
# Get latest decisions
curl http://localhost:8000/api/decisions/latest/

# Trigger analysis
curl -X POST http://localhost:8000/api/decisions/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTCUSDT"],
    "timeframes": ["1h", "4h"]
  }'

# Get decisions for BTC
curl "http://localhost:8000/api/decisions/by_symbol/?symbol=BTCUSDT"

# Filter high-confidence BUY signals
curl "http://localhost:8000/api/decisions/?signal=BUY&confidence__gte=80"
```

---

## 🐍 Python API Usage

### Programmatic Analysis

```python
from oracle.engine import DecisionEngine
from oracle.providers import BinanceProvider

# Initialize provider
provider = BinanceProvider()

# Fetch data
df = provider.fetch_ohlcv('BTC/USDT', '1h', limit=500)

# Run analysis
engine = DecisionEngine('BTCUSDT', 'SPOT', '1h')
decision = engine.generate_decision(df, context={})

# Access results
print(f"{decision.signal} | Confidence: {decision.confidence}%")
print(f"Entry: {decision.entry_price} | Stop: {decision.stop_loss}")

# Top drivers
for driver in decision.top_drivers[:3]:
    print(f"{driver['name']}: {driver['contribution']:.3f}")
```

### Database Queries

```python
from oracle.models import Decision, Symbol

# Get latest decisions
latest = Decision.objects.order_by('-created_at')[:10]

# Filter by confidence
high_conf = Decision.objects.filter(confidence__gte=80)

# Get symbol decisions
btc = Symbol.objects.get(symbol='BTCUSDT')
btc_decisions = Decision.objects.filter(symbol=btc)

# Get BUY signals from last week
from datetime import timedelta
from django.utils import timezone

week_ago = timezone.now() - timedelta(days=7)
buys = Decision.objects.filter(
    signal__in=['STRONG_BUY', 'BUY'],
    created_at__gte=week_ago
)
```

---

## 🔍 Common Workflows

### Daily Trading Workflow

```bash
# 1. Check overnight decisions
python manage.py run_analysis --symbols BTCUSDT ETHUSDT --timeframes 1h 4h

# 2. Review in admin
# Visit http://localhost:8000/admin/oracle/decision/

# 3. Filter high confidence (80%+)
# Use admin filters: confidence >= 80

# 4. Validate with charts
# Check invalidation conditions

# 5. Place trades with proper risk management
```

### Weekly Optimization Workflow

```bash
# 1. Run backtest
python manage.py backtest --days 7 --export

# 2. Analyze results
# Check win rate by confidence level
# Identify best-performing features

# 3. Adjust weights in Django Admin
# Go to Features > Select feature > Adjust weights

# 4. Re-test
python manage.py backtest --days 7

# 5. Deploy if improved
# Restart Celery workers to pick up new weights
```

### Adding New Symbol

```python
# Via Django shell
python manage.py shell

from oracle.models import Symbol

Symbol.objects.create(
    symbol='SOLUSDT',
    name='Solana',
    asset_type='CRYPTO',
    base_currency='SOL',
    quote_currency='USDT',
    description='Solana cryptocurrency'
)
```

Or via Django Admin:
1. Go to http://localhost:8000/admin/oracle/symbol/
2. Click "Add Symbol"
3. Fill in details
4. Save

### Custom Feature Weights

```python
# For symbol-specific tuning
python manage.py shell

from oracle.models import FeatureWeight, Feature, Symbol, Timeframe

FeatureWeight.objects.create(
    feature=Feature.objects.get(name='FundingRate'),
    symbol=Symbol.objects.get(symbol='BTCUSDT'),
    timeframe=Timeframe.objects.get(name='1h'),
    weight=2.0,  # Double the standard weight
    notes='BTC is very sensitive to funding'
)
```

---

## 🐛 Debugging & Troubleshooting

### Check Service Status

```bash
# Django
curl http://localhost:8000/api/

# Celery Worker
celery -A trading_oracle inspect active

# Redis
redis-cli ping
```

### View Logs

```bash
# Django logs
tail -f logs/trading_oracle.log

# Celery worker logs
tail -f logs/celery-worker.log

# Celery beat logs
tail -f logs/celery-beat.log
```

### Common Issues

#### Issue: "No module named 'django'"
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

#### Issue: Redis connection error
```bash
# Check Redis is running
redis-cli ping

# Start Redis
# Docker: docker-compose up -d redis
# Or: redis-server
```

#### Issue: Celery tasks not running
```bash
# Check worker is running
celery -A trading_oracle inspect active

# Restart worker
# Kill existing: ps aux | grep celery
# Start new: celery -A trading_oracle worker -l info
```

#### Issue: Analysis returns no data
```bash
# Check data providers
python manage.py shell

from oracle.providers import BinanceProvider
provider = BinanceProvider()
df = provider.fetch_ohlcv('BTC/USDT', '1h', limit=10)
print(len(df))  # Should be 10
```

---

## 📊 Performance Monitoring

### Check System Health

```bash
# Database size
python manage.py dbshell
# Then: SELECT COUNT(*) FROM oracle_decision;

# Decision count by day
SELECT DATE(created_at), COUNT(*)
FROM oracle_decision
GROUP BY DATE(created_at)
ORDER BY DATE(created_at) DESC
LIMIT 7;

# Avg confidence by signal
SELECT signal, AVG(confidence)
FROM oracle_decision
GROUP BY signal;
```

### Monitor Accuracy

```bash
# Weekly backtest
python manage.py backtest --days 7

# Monthly comprehensive backtest
python manage.py backtest --days 30 --export

# By symbol
python manage.py backtest --days 30 --symbols BTCUSDT --export
```

---

## 🚢 Production Deployment

### Quick Deploy (Ubuntu/Debian)

```bash
# 1. Install dependencies
sudo apt update
sudo apt install python3-pip python3-venv postgresql redis-server nginx supervisor

# 2. Setup project
cd /var/www/
git clone <repo> trading-oracle
cd trading-oracle
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
nano .env  # Edit with your values

# 4. Setup database
python manage.py migrate
python manage.py init_oracle
python manage.py createsuperuser
python manage.py collectstatic --no-input

# 5. Configure Nginx
sudo cp deploy/nginx.conf /etc/nginx/sites-available/trading-oracle
sudo ln -s /etc/nginx/sites-available/trading-oracle /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 6. Configure Supervisor
sudo cp deploy/supervisor.conf /etc/supervisor/conf.d/trading-oracle.conf
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start trading_oracle:*

# 7. Check status
sudo supervisorctl status trading_oracle:*
```

### Update Deployment

```bash
cd /var/www/trading-oracle
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --no-input
sudo supervisorctl restart trading_oracle:*
```

---

## 📖 Documentation Links

- **README.md**: Complete setup guide
- **ACCURACY.md**: Accuracy and precision guide
- **CHANGELOG.md**: Version history
- **SUMMARY.md**: Project overview
- **API Docs**: http://localhost:8000/api/ (when running)
- **Admin**: http://localhost:8000/admin/

---

## 🆘 Getting Help

### Check Logs First
```bash
# Django
tail -f logs/trading_oracle.log

# Celery
tail -f logs/celery-worker.log
```

### Run Tests
```bash
python manage.py test oracle
```

### Debug Mode
```bash
# Set DEBUG=True in settings.py (development only!)
# Then restart server
```

---

## 💡 Pro Tips

1. **Always use high confidence signals (80%+) for live trading**
2. **Run backtests monthly to validate accuracy**
3. **Start with 4h timeframe (best win rate)**
4. **Never risk >2% per trade**
5. **Monitor regime indicators (ADX, volatility)**
6. **Adjust weights based on backtest results**
7. **Use invalidation conditions as hard stops**
8. **Diversify across symbols and timeframes**

---

## 🎯 Quick Checks

### Is Everything Working?

```bash
# Check services
curl http://localhost:8000/api/symbols/        # Django
redis-cli ping                                  # Redis
celery -A trading_oracle inspect active       # Celery

# Run test analysis
python manage.py run_analysis --symbols BTCUSDT --timeframes 1h

# Check logs for errors
tail -f logs/trading_oracle.log
```

### Performance Baseline

After 30 days, you should see:
- ✅ 50-65% win rate
- ✅ 1.5R+ average R
- ✅ High confidence (85%+) outperforming low confidence
- ✅ 4h/1d timeframes showing best results

If not, run optimization workflow.

---

**Last Updated**: 2026-01-10
**Version**: 1.0.0
