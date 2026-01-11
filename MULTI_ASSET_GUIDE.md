# Trading Oracle - Multi-Asset Support & ROI Tracking Guide

## 🎯 Overview

The Trading Oracle system now supports multiple asset types with individualized characteristics and comprehensive ROI tracking. Each asset type (CRYPTO, GOLD, COMMODITY, FX, STOCK, INDEX) is analyzed with asset-specific indicators and decision logic.

---

## 📊 Supported Asset Types

### 1. **CRYPTO** (Cryptocurrency)
- **Indicators**: Funding rate, open interest, order book, liquidations, exchange flow
- **Gold Oracle Adaptation**: News sentiment, VIX correlation, DXY inverse relationship
- **ROI Tracking**: High volatility, 24/7 trading, volume spikes
- **Examples**: BTCUSDT, ETHUSDT, BNBUSDT

### 2. **GOLD** (Gold & Precious Metals)
- **Indicators**: All Gold Oracle indicators fully integrated
  - DXY (US Dollar Index) - inverse correlation
  - Real yields - primary driver
  - Treasury yields - opportunity cost
  - VIX - fear gauge
  - Gold/Silver ratio - relative value
  - Gold/Oil ratio - flight to safety
  - Inflation expectations
  - News sentiment (fear/greed)
- **ROI Tracking**: Safe haven flows, central bank demand
- **Examples**: XAUUSD, Gold Futures

### 3. **COMMODITY** (Other Commodities)
- **Indicators**: Inter-market ratios, supply/demand, seasonal patterns
- **Examples**: Silver, Copper, Oil

### 4. **FX** (Foreign Exchange)
- **Indicators**: Interest rate differentials, central bank policy, economic data
- **Examples**: EURUSD, GBPUSD

### 5. **STOCK** & **INDEX**
- **Indicators**: Earnings, sector rotation, market breadth
- **Examples**: SPY, QQQ, AAPL

---

## 🆕 New Features

### 1. **ROI Tracking System**

The system now tracks Return on Investment across multiple timeframes:

```python
# Model: SymbolPerformance
roi_1h   # 1 hour ROI
roi_1d   # 1 day ROI
roi_1w   # 1 week ROI
roi_1m   # 1 month ROI
roi_1y   # 1 year ROI
```

**Additional Metrics:**
- Current price
- 24h volume & volume change
- 24h volatility
- 24h high/low
- Market cap (for crypto)
- Market cap rank
- Number of trades

### 2. **Calculate ROI Command**

```bash
# Calculate ROI for all active symbols
python manage.py calculate_roi

# Calculate for specific symbols
python manage.py calculate_roi --symbols BTCUSDT XAUUSD ETHUSDT

# Example output:
# BTCUSDT (CRYPTO)...
#   Current price: $43,250.00
#   ROI: 1h=+0.52% | 1d=+2.34% | 1w=+5.67% | 1m=+12.45% | 1y=+125.78%
```

### 3. **Dashboard ROI Display**

The home dashboard now shows:
- **Symbol Performance Table**
  - Real-time prices
  - Color-coded ROI (green = positive, red = negative)
  - Asset type badges
  - 24h volume
  - All timeframe ROIs in one view

### 4. **Template Filters Fixed**

Custom template filters added:
- `replace_underscore`: Replace underscores with spaces
- `format_percentage`: Format decimals as percentages
- `format_roi`: Format ROI with +/- signs
- `abs_value`: Get absolute value

**Fixed Error:** `Invalid filter: 'replace'` → now uses `replace_underscore`

---

## 🔧 Asset-Specific Feature Behavior

### Gold Features (from Gold Oracle)

All 20+ Gold Oracle indicators are fully integrated:

| Feature | What It Does | Gold Impact |
|---------|--------------|-------------|
| **DXY** | US Dollar strength | Inverse (-0.82 correlation) |
| **Real Yields** | Treasury yield - inflation | Primary gold driver |
| **VIX** | Market fear gauge | Safe haven demand |
| **Gold/Silver Ratio** | Relative precious metal value | 80+ = gold overvalued |
| **Gold/Oil Ratio** | Flight to safety indicator | 30+ = strong safe haven |
| **News Sentiment** | Fear index from news | Negative news = bullish gold |
| **Inflation Expectations** | Breakeven inflation | Rising = bullish gold |
| **Treasury 10Y** | Opportunity cost | Rising yields = bearish gold |

### Crypto Features

| Feature | What It Does | Crypto Impact |
|---------|--------------|---------------|
| **Funding Rate** | Perpetual swap funding | Positive = bullish sentiment |
| **Open Interest** | Futures positions | Rising OI + price = bullish |
| **Order Book Imbalance** | Bid/ask volume ratio | >60% bids = buying pressure |
| **Liquidations** | Forced position closures | Mass liq = reversal signal |
| **Exchange Flow** | Deposits/withdrawals | Withdrawals = accumulation |

### Technical Features (Universal)

Work across all asset types:
- RSI (7/14/21 periods)
- MACD
- Stochastic
- Bollinger Bands
- ADX
- ATR
- Moving Averages (SMA/EMA)
- Golden/Death Cross
- Price Momentum

---

## 📈 Dashboard Features

### 1. **Run Analysis from Dashboard**
- Click "Run Analysis" button on home page
- No command line needed!
- Shows spinner during analysis
- Auto-reloads with new decisions

### 2. **Feature Analysis Page**
For each feature, see:
- **Latest Value**: Current indicator reading
- **Power**: Impact magnitude (0.0-2.0+ scale)
- **Effect/Influence**:
  - 🟢 BULLISH ↑ (+buy signal)
  - 🔴 BEARISH ↓ (-sell signal)
  - ⚪ NEUTRAL — (no direction)
- **Contribution**: Signed value (+/-) showing impact on decision
- **Usage Stats**: How often used
- **Distribution**: Breakdown of signals

### 3. **Symbol Performance & ROI**
Table showing:
- Symbol & asset type
- Current price
- ROI across 5 timeframes (1h, 1d, 1w, 1m, 1y)
- 24h trading volume
- Color-coded returns

### 4. **Decision History**
- Full audit trail
- Filter by symbol, timeframe, signal
- View detailed breakdown
- Export capabilities

---

## 🚀 Complete Workflow

### 1. Initialize System
```bash
# Run migrations for new SymbolPerformance model
python manage.py makemigrations
python manage.py migrate

# Initialize database with symbols and features
python manage.py init_oracle
```

### 2. Calculate ROI
```bash
# Calculate performance metrics for all symbols
python manage.py calculate_roi
```

### 3. Run Analysis

**Option A: Command Line**
```bash
python manage.py run_analysis --symbols BTCUSDT XAUUSD --timeframes 1h 4h 1d
```

**Option B: Dashboard (NEW!)**
1. Open http://127.0.0.1:8000/dashboard/
2. Click "Run Analysis" button
3. Wait for completion
4. View results automatically

### 4. View Results

Navigate to:
- **Dashboard Home**: Overview + ROI table
- **Feature Analysis**: All 20+ indicators with power/influence
- **Decision History**: Detailed decisions
- **Live Monitor**: Real-time updates

---

## 🎨 Dashboard Sections

### Home Page
- Key metrics cards (total decisions, active symbols, avg confidence)
- Decision timeline chart (30 days)
- Confidence distribution pie chart
- **NEW: Symbol Performance & ROI table**
- Signal distribution
- Recent decisions (last 20)

### Feature Analysis
- Total features count
- Category breakdown
- Feature power comparison chart (top 15)
- **Detailed table with:**
  - Feature name & description
  - Latest value
  - Power rating with progress bar
  - Effect badge (BULLISH/BEARISH/NEUTRAL)
  - Influence arrows (↑/↓/—)
  - Contribution value
  - Usage count
  - Distribution (positive/negative/neutral)

### Decision History
- Filterable table
- Search by symbol, timeframe, signal
- Pagination
- Export functionality

### Decision Detail Page
- Full breakdown of single decision
- Entry/stop/target prices
- Risk/reward ratio
- Top 5 drivers
- All feature contributions
- Regime context
- Invalidation conditions

---

## 🔍 Indicator Reference

### All 20+ Indicators Integrated

**Technical (9 indicators)**
1. RSI (7/14/21)
2. MACD
3. Stochastic
4. ADX
5. Bollinger Bands
6. ATR
7. SMA
8. MA Crossover
9. Price Momentum

**Macro (5 indicators)**
10. DXY (US Dollar)
11. VIX (Volatility)
12. Treasury 10Y
13. Real Yields
14. Inflation Expectations

**Intermarket (5 indicators)**
15. Gold/Silver Ratio
16. Copper/Gold Ratio
17. Gold/Oil Ratio
18. Miners/Gold Ratio
19. GLD Flow

**Sentiment (2 indicators)**
20. News Sentiment
21. Market Fear Gauge

**Crypto (5 indicators)**
22. Funding Rate
23. Open Interest
24. Order Book Imbalance
25. Liquidations
26. Exchange Flow

**Total: 26 unique indicators**

---

## 📊 ROI Calculation Logic

```python
# For each timeframe
roi_1h = ((current_price - price_1h_ago) / price_1h_ago) * 100

# Examples:
# Price now: $43,250
# Price 1h ago: $43,000
# ROI_1h = ((43,250 - 43,000) / 43,000) * 100 = +0.58%

# Price 1 day ago: $42,000
# ROI_1d = ((43,250 - 42,000) / 42,000) * 100 = +2.98%
```

**Volatility Calculation:**
```python
volatility_24h = (std_dev_24h / mean_price_24h) * 100
```

---

## 🎯 Asset-Specific Decision Logic

### Gold Decision Making
1. **Primary Drivers**: Real yields (-0.82 correlation)
2. **Secondary**: DXY (inverse), VIX (safe haven)
3. **Tertiary**: Gold/Silver ratio, news sentiment
4. **Weights**: Real yields (10), DXY (9), VIX (7), News (4)

### Crypto Decision Making
1. **Primary Drivers**: Funding rate, open interest
2. **Secondary**: Order book, liquidations
3. **Tertiary**: Technical indicators
4. **Weights**: Funding (10), OI (9), Order book (8), Technical (7)

### Universal Technical Analysis
- All assets use RSI, MACD, Bollinger Bands, etc.
- Weights adjusted by asset volatility
- Timeframe-appropriate parameters

---

## 🔧 Configuration

### Feature Weights by Asset Type

Can be customized in feature classes:

```python
class DXYFeature(BaseFeature):
    def calculate(self, df, symbol, timeframe, market_type, context):
        # Stronger weight for GOLD
        if symbol_asset_type == 'GOLD':
            self.weight = 10
        else:
            self.weight = 6
```

### ROI Update Frequency

```bash
# Run hourly via cron
0 * * * * cd /path/to/trading-oracle && python manage.py calculate_roi

# Or run manually as needed
python manage.py calculate_roi
```

---

## 📱 API Endpoints

### Dashboard APIs

```
GET  /dashboard/api/chart/decisions/          # Decision timeline data
GET  /dashboard/api/chart/confidence/         # Confidence distribution
GET  /dashboard/api/chart/feature-power/      # Feature power chart
GET  /dashboard/api/live-updates/             # Live data updates
GET  /dashboard/api/symbol/<symbol>/          # Symbol performance
POST /dashboard/api/run-analysis/             # Trigger analysis
```

---

## 🐛 Troubleshooting

### Template Filter Errors
**Error**: `Invalid filter: 'replace'`
**Fix**: Already fixed! Custom filters in `oracle/dashboard/templatetags/dashboard_filters.py`

### Missing ROI Data
**Issue**: ROI table empty
**Fix**: Run `python manage.py calculate_roi`

### Old Decisions
**Issue**: Low confidence (1%), NEUTRAL signals
**Fix**:
1. yfinance retry logic added
2. Error handling for empty data
3. Run analysis again

### Database Migrations
**Issue**: SymbolPerformance table doesn't exist
**Fix**:
```bash
python manage.py makemigrations
python manage.py migrate
```

---

## 🎉 Summary

**What's New:**
✅ ROI tracking (1h/1d/1w/1m/1y)
✅ Multi-asset type support
✅ Asset-specific indicators
✅ Template filters fixed
✅ Dashboard ROI display
✅ 26 total indicators
✅ Run analysis from UI

**Next Steps:**
1. Start Django: `python manage.py runserver`
2. Calculate ROI: `python manage.py calculate_roi`
3. Open dashboard: http://127.0.0.1:8000/dashboard/
4. Click "Run Analysis"
5. View results with full ROI tracking!

---

**Branch**: `claude/django-trading-oracle-app-3dgc7`
**Commits**:
- `c483d44`: Gold Oracle indicators integrated
- `050480c`: ROI tracking & template fixes

All changes pushed and ready for use! 🚀
