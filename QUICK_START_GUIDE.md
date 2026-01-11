# Trading Oracle - Quick Start Guide

**Ready to use in 5 minutes!**

---

## 🚀 Option 1: Instant Start (Recommended)

### Step 1: Install Dependencies
```bash
cd /home/user/trading-oracle
pip install -r requirements.txt
```

### Step 2: Setup Database
```bash
# Run migrations
python manage.py migrate

# Initialize oracle data (symbols, features, timeframes)
python manage.py init_oracle
```

### Step 3: Create Admin User (Optional but Recommended)
```bash
python manage.py createsuperuser
# Enter username, email, password when prompted
```

### Step 4: Start the Server
```bash
python manage.py runserver
```

### Step 5: Open Dashboard
Open your browser to: **http://localhost:8000/**

You'll see the dashboard with:
- ✅ Overview page
- ✅ Feature analysis
- ✅ Decision history
- ✅ Live monitoring

---

## 📊 Generate Your First Decisions

### Quick Test (1 symbol, 1 timeframe)
```bash
# In a new terminal window
python manage.py run_analysis --symbol BTCUSDT --timeframe 1h
```

### Full Analysis (All symbols, all timeframes)
```bash
python manage.py run_analysis
```

### Check the Results
1. Refresh dashboard: http://localhost:8000/
2. You'll see your decisions appear!
3. Click any decision for detailed analysis

---

## 🎯 What You Can Do Right Now

### 1. View Dashboard
```
http://localhost:8000/
```
See:
- Total decisions generated
- Average confidence
- Signal distribution
- Recent decisions

### 2. Analyze Features
```
http://localhost:8000/dashboard/features/
```
See:
- Feature power rankings (0.0-2.0+ scale)
- Effect classification (BULLISH/BEARISH/NEUTRAL)
- Usage statistics
- Interactive charts

### 3. Browse History
```
http://localhost:8000/dashboard/history/
```
Filter by:
- Symbol (BTCUSDT, ETHUSDT, etc.)
- Timeframe (1h, 4h, 1d, 1w)
- Signal type
- Date range

### 4. Monitor Live
```
http://localhost:8000/dashboard/live/
```
Features:
- Auto-refresh (every 30s)
- Real-time decisions
- Symbol prices
- System status

### 5. Admin Panel
```
http://localhost:8000/admin/
```
Login with superuser credentials to:
- View all database records
- Manage symbols and features
- Edit decisions
- Configure system

### 6. API Endpoints
```
http://localhost:8000/api/
```
Available endpoints:
- GET /api/symbols/
- GET /api/decisions/latest/
- GET /api/decisions/by_symbol/?symbol=BTCUSDT
- POST /api/decisions/analyze/
- GET /api/features/

---

## 🧪 Test the System

### Run Backtest (Validate Accuracy)
```bash
# 30-day backtest
python manage.py backtest --days 30

# Specific symbol
python manage.py backtest --symbol BTCUSDT --days 30
```

**Output shows**:
- Win rate
- Average R multiples
- Profit factor
- Kelly Criterion
- Expectancy
- Performance by confidence level

---

## 💡 Usage Examples

### Example 1: Day Trading Setup

```bash
# Generate 1h decisions for BTC and ETH
python manage.py run_analysis --symbol BTCUSDT --timeframe 1h
python manage.py run_analysis --symbol ETHUSDT --timeframe 1h

# Check dashboard for signals
# Look for:
#   - Confidence > 85%
#   - Strong consensus (> 75%)
#   - No conflicts
#   - Check order book imbalance
```

### Example 2: Swing Trading Setup

```bash
# Generate 4h and 1d decisions for multiple assets
python manage.py run_analysis --timeframe 4h
python manage.py run_analysis --timeframe 1d

# Filter in dashboard:
#   - Confidence > 70%
#   - Check top 5 drivers
#   - Review invalidation conditions
```

### Example 3: Position Trading Setup

```bash
# Generate 1d and 1w decisions
python manage.py run_analysis --timeframe 1d
python manage.py run_analysis --timeframe 1w

# Focus on:
#   - Macro alignment (check DXY, VIX, yields)
#   - Long-term trends (ADX > 25)
#   - High timeframe consensus
```

---

## 📈 Reading a Decision

### Example Decision Output:

```
Symbol: BTCUSDT
Timeframe: 1h
Signal: STRONG_BUY
Bias: BULLISH
Confidence: 87%

Trade Parameters:
  Entry: $42,500.00
  Stop Loss: $41,200.00
  Take Profit: $45,800.00
  Risk/Reward: 2.54

Consensus Analysis:
  Level: STRONG_CONSENSUS (82%)
  Conflicts: None
  Explanation: High cross-category agreement

Top 5 Drivers:
  1. RSI (+0.6421) - Oversold, bullish divergence
  2. FundingRate (+0.5234) - Negative funding, shorts crowded
  3. ADX (+0.4123) - Strong uptrend confirmed
  4. MACD (+0.3891) - Bullish crossover
  5. OrderBookImbalance (+0.3567) - 65% bids, buying pressure

Regime Context:
  Trend: TRENDING
  Volatility: HIGH
  Consensus: STRONG

Invalidation:
  - Break below $41,200
  - ADX falls below 20
  - Funding rate turns extremely positive
```

### How to Interpret:

✅ **High Confidence (87%)**: Strong signal
✅ **Strong Consensus (82%)**: Most features agree
✅ **No Conflicts**: Technical and Macro aligned
✅ **Good R:R (2.54)**: Risk $1 to make $2.54
✅ **Clear Invalidation**: Know when to exit

**Action**: Strong buy signal with good risk/reward

---

## 🔧 Customization

### Change Symbols
Edit `oracle/management/commands/init_oracle.py` and add symbols:
```python
symbols_to_create = [
    ('BTCUSDT', 'CRYPTO'),
    ('YOURSYMBOL', 'CRYPTO'),  # Add here
]
```

Then re-run:
```bash
python manage.py init_oracle
```

### Adjust Feature Weights
Edit `oracle/engine/decision_engine.py`:
```python
def _get_default_timeframe_weights(self):
    if self.timeframe in ['15m', '1h', '4h']:
        return {
            'RSI': 1.5,  # Increase RSI weight
            'MACD': 1.2,  # Increase MACD weight
            ...
        }
```

### Change Confidence Thresholds
Edit `oracle/engine/consensus_engine.py`:
```python
STRONG_CONSENSUS = 0.75  # Default 75%, change to 0.80 for 80%
MODERATE_CONSENSUS = 0.60
```

---

## 🔄 Automated Updates (Optional)

### Setup Celery for Background Tasks

#### Terminal 1: Start Celery Worker
```bash
celery -A trading_oracle worker -l info
```

#### Terminal 2: Start Celery Beat (Scheduler)
```bash
celery -A trading_oracle beat -l info
```

#### Terminal 3: Django Server
```bash
python manage.py runserver
```

**Now decisions generate automatically every hour!**

---

## 🐛 Troubleshooting

### Problem: "No module named 'oracle'"
**Solution**: Make sure you're in the project directory
```bash
cd /home/user/trading-oracle
python manage.py runserver
```

### Problem: Dashboard shows "No decisions yet"
**Solution**: Generate decisions first
```bash
python manage.py run_analysis
```

### Problem: Charts not loading
**Solution**: Check internet connection (Chart.js loads from CDN)

### Problem: "Database is locked" (SQLite)
**Solution**: Use PostgreSQL in production, or close all connections

### Problem: Features showing 0 power
**Solution**: More decisions needed for statistical significance
```bash
# Generate more decisions
python manage.py run_analysis
# Run multiple times for different timestamps
```

---

## 📊 Expected Results

### After Initial Setup:
- ✅ Dashboard accessible
- ✅ Admin panel working
- ✅ API responding
- ⏳ No decisions yet (need to generate)

### After First Analysis:
- ✅ 1-10 decisions generated (depends on symbols/timeframes)
- ✅ Features showing power metrics
- ✅ Charts updating
- ✅ History populated

### After Multiple Analyses:
- ✅ 50+ decisions
- ✅ Meaningful feature statistics
- ✅ Confidence calibration data
- ✅ Backtest results available

---

## 🎯 Daily Workflow

### Morning Routine (5 minutes)
```bash
# 1. Generate latest decisions
python manage.py run_analysis

# 2. Check dashboard for signals
# Open: http://localhost:8000/

# 3. Review high-confidence decisions
# Filter: Confidence > 80%, Strong Consensus

# 4. Check for conflicts
# Look at decision details, review consensus analysis

# 5. Validate with backtesting
python manage.py backtest --days 7
```

### Before Trading (Per Signal)
1. ✅ Check confidence (>70% minimum)
2. ✅ Review consensus (no major conflicts)
3. ✅ Verify top 5 drivers make sense
4. ✅ Check regime context (trending vs ranging)
5. ✅ Validate risk/reward (>1.5:1 minimum)
6. ✅ Set invalidation alerts

---

## 🚀 Production Deployment

### Using Docker (Recommended)
```bash
# Build and start
docker-compose up -d

# Access
http://your-server-ip:8000/
```

### Manual Deployment
See `OPERATIONS.md` for:
- Gunicorn configuration
- Nginx setup
- Supervisor process management
- SSL/TLS configuration
- Database optimization

---

## 📚 Next Steps

### Learn More:
1. **ACCURACY.md** - Understand expected win rates
2. **DASHBOARD_README.md** - Master dashboard features
3. **INSPIRATION_ANALYSIS.md** - See best practices
4. **OPERATIONS.md** - Production deployment

### Enhance System:
1. **Phase 2**: Add machine learning (ML models)
2. **Phase 3**: Add sentiment analysis (Twitter, Reddit)
3. **Phase 4**: Add AI assistant (Claude API)
4. **Phase 5**: Add live trading (execution engine)

---

## 💬 Support

### Get Help:
1. Check this guide
2. Read relevant documentation
3. Check Django logs: `python manage.py runserver --verbosity 2`
4. Check browser console (F12) for frontend errors

### Common Commands:
```bash
# Show help
python manage.py --help
python manage.py run_analysis --help
python manage.py backtest --help

# Check system status
python manage.py check

# Run tests
python manage.py test oracle

# Shell access
python manage.py shell
```

---

## ✅ Checklist: First Time Setup

- [ ] Install dependencies (`pip install -r requirements.txt`)
- [ ] Run migrations (`python manage.py migrate`)
- [ ] Initialize data (`python manage.py init_oracle`)
- [ ] Create superuser (`python manage.py createsuperuser`)
- [ ] Start server (`python manage.py runserver`)
- [ ] Open dashboard (http://localhost:8000/)
- [ ] Generate decisions (`python manage.py run_analysis`)
- [ ] Refresh dashboard (see results!)
- [ ] Explore features page
- [ ] Review decision details
- [ ] Run backtest (`python manage.py backtest --days 30`)
- [ ] Check accuracy metrics

---

## 🎉 You're Ready!

Your Trading Oracle is now operational. Start by:

1. ✅ **Generate decisions**: `python manage.py run_analysis`
2. ✅ **Open dashboard**: http://localhost:8000/
3. ✅ **Explore features**: Click "Features" in navigation
4. ✅ **Review decisions**: Click "History" and filter
5. ✅ **Monitor live**: Click "Live" for real-time updates

**Happy Trading!** 📈🚀

---

**Need Phase 2 (Machine Learning)?** Let me know and I'll implement:
- FreqAI-style adaptive ML
- 10,000+ engineered features
- Automatic model retraining
- ML-adjusted confidence scores

**Status**: ✅ Ready to use NOW!
