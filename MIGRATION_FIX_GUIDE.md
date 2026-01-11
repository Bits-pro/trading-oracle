# Migration Fix Guide - SymbolPerformance Table

## 🔧 Problem Solved

**Error**: `no such table: oracle_symbolperformance`

**Cause**: The SymbolPerformance model was added to `oracle/models.py` but the database migration wasn't applied.

**Solution**: ✅ **FIXED** - The table has been created and migration recorded.

---

## ✅ What Was Done

### 1. Created Migration File
- **File**: `oracle/migrations/0002_symbolperformance.py`
- Creates the `oracle_symbolperformance` table
- Adds all ROI and performance tracking fields
- Creates indexes for optimal query performance

### 2. Created Fix Script
- **File**: `fix_migration.py`
- Manually creates the table using raw SQL
- Records migration in `django_migrations` table
- ✅ **Already run successfully**

### 3. Created SQL Backup
- **File**: `create_symbolperformance_table.sql`
- Pure SQL version for manual execution if needed
- Can be run directly with sqlite3 or Python

---

## 📊 Table Schema

The `oracle_symbolperformance` table includes:

### ROI Fields
- `roi_1h` - 1 hour return on investment (%)
- `roi_1d` - 1 day return on investment (%)
- `roi_1w` - 1 week return on investment (%)
- `roi_1m` - 1 month return on investment (%)
- `roi_1y` - 1 year return on investment (%)

### Price & Volume Fields
- `current_price` - Latest price
- `volume_24h` - 24-hour trading volume
- `volume_change_24h` - 24h volume change (%)
- `high_24h` - 24-hour high
- `low_24h` - 24-hour low

### Volatility & Market Data
- `volatility_24h` - 24-hour volatility (%)
- `market_cap` - Market capitalization (for crypto)
- `market_cap_rank` - Market cap ranking
- `trades_24h` - Number of trades in 24h

### Relationships
- `symbol_id` - Foreign key to oracle_symbol
- `market_type_id` - Foreign key to oracle_markettype
- `timestamp` - When data was recorded

### Indexes Created
- `symbol_id, timestamp DESC` - Fast lookup by symbol
- `symbol_id, market_type_id, timestamp DESC` - Fast lookup by symbol+market
- `timestamp` - Time-based queries
- Foreign key indexes on `symbol_id` and `market_type_id`

---

## 🚀 Next Steps

### 1. Calculate ROI Data

Now that the table exists, populate it with data:

```bash
python manage.py calculate_roi
```

This will:
- Fetch historical price data for all active symbols
- Calculate ROI across 1h, 1d, 1w, 1m, 1y timeframes
- Store volume and volatility metrics
- Save to `oracle_symbolperformance` table

**Example output:**
```
BTCUSDT (CRYPTO)...
  Current price: $43,250.00
  ROI: 1h=+0.52% | 1d=+2.34% | 1w=+5.67% | 1m=+12.45% | 1y=+125.78%

XAUUSD (GOLD)...
  Current price: $2,045.50
  ROI: 1h=+0.12% | 1d=+0.87% | 1w=+2.34% | 1m=+5.67% | 1y=+15.32%
```

### 2. View ROI in Dashboard

Start the server and view performance data:

```bash
python manage.py runserver
```

Navigate to: http://127.0.0.1:8000/dashboard/

The home page now displays:
- **Symbol Performance & ROI table** with color-coded returns
- Current prices for all symbols
- ROI across all 5 timeframes (1h, 1d, 1w, 1m, 1y)
- 24h volume data
- Asset type indicators

### 3. Run Analysis

Generate trading decisions with full context:

**Option A - From Dashboard:**
1. Click "Run Analysis" button
2. Wait for completion (shows spinner)
3. View results automatically

**Option B - Command Line:**
```bash
python manage.py run_analysis --symbols BTCUSDT XAUUSD --timeframes 1h 4h 1d
```

---

## 🔍 Verification

Check that everything is working:

### 1. Verify Table Exists
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='oracle_symbolperformance';")
print("✓ Table exists" if cursor.fetchone() else "✗ Table not found")
conn.close()
EOF
```

### 2. Verify Migration Recorded
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute("SELECT name FROM django_migrations WHERE app='oracle';")
print("Migrations:", [row[0] for row in cursor.fetchall()])
conn.close()
EOF
```

Expected output:
```
Migrations: ['0001_initial', '0002_symbolperformance']
```

### 3. Check Table Schema
```bash
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('db.sqlite3')
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(oracle_symbolperformance);")
columns = cursor.fetchall()
print(f"Columns ({len(columns)}):", [col[1] for col in columns])
conn.close()
EOF
```

Expected: 18 columns including roi_1h, roi_1d, roi_1w, roi_1m, roi_1y

---

## 🛠️ Troubleshooting

### Issue: "Table already exists" error
**Solution**: The table is already created. Skip to "Calculate ROI Data" step.

### Issue: Migration conflicts
**Solution**: Check django_migrations table:
```bash
python3 -c "import sqlite3; conn=sqlite3.connect('db.sqlite3'); print(conn.execute('SELECT * FROM django_migrations WHERE app=\"oracle\"').fetchall())"
```

If needed, manually remove the migration:
```bash
python3 -c "import sqlite3; conn=sqlite3.connect('db.sqlite3'); conn.execute('DELETE FROM django_migrations WHERE app=\"oracle\" AND name=\"0002_symbolperformance\"'); conn.commit()"
```

Then re-run `python3 fix_migration.py`

### Issue: Django not installed
**Solution**:
```bash
pip install -r requirements.txt
# or
pip install django django-celery-beat django-celery-results
```

### Issue: Can't run calculate_roi
**Possible causes:**
1. Django not installed - `pip install django`
2. Missing dependencies - `pip install yfinance ccxt pandas numpy`
3. No active symbols - `python manage.py init_oracle` first

---

## 📁 Files Created

### Migration Files
- `oracle/migrations/0002_symbolperformance.py` - Django migration
- `create_symbolperformance_table.sql` - SQL backup
- `fix_migration.py` - Python script to create table manually

### Documentation
- `MULTI_ASSET_GUIDE.md` - Complete guide to multi-asset support
- `MIGRATION_FIX_GUIDE.md` - This file

---

## 🎯 Summary

✅ **Migration Fixed** - oracle_symbolperformance table created
✅ **18 columns** including all ROI timeframes (1h, 1d, 1w, 1m, 1y)
✅ **Indexes created** for optimal performance
✅ **Migration recorded** in django_migrations table
✅ **Ready to use** - Run `python manage.py calculate_roi`

---

## 📚 Related Commands

### ROI Management
```bash
# Calculate ROI for all symbols
python manage.py calculate_roi

# Calculate for specific symbols
python manage.py calculate_roi --symbols BTCUSDT XAUUSD ETHUSDT

# Schedule with cron (hourly updates)
0 * * * * cd /path/to/trading-oracle && python manage.py calculate_roi
```

### Analysis
```bash
# Run analysis
python manage.py run_analysis --symbols BTCUSDT XAUUSD

# Initialize oracle (first time)
python manage.py init_oracle

# View dashboard
python manage.py runserver
```

### Database Management
```bash
# Check migrations
python manage.py showmigrations oracle

# Create new migrations
python manage.py makemigrations oracle

# Apply migrations
python manage.py migrate oracle

# Reset migrations (DANGER - deletes data)
python manage.py migrate oracle zero
```

---

## 🚀 Quick Start After Fix

1. **Calculate ROI**:
   ```bash
   python manage.py calculate_roi
   ```

2. **Start Dashboard**:
   ```bash
   python manage.py runserver
   ```

3. **View Results**:
   - Open http://127.0.0.1:8000/dashboard/
   - See Symbol Performance & ROI table
   - Color-coded returns (green=profit, red=loss)

4. **Run Analysis**:
   - Click "Run Analysis" button in dashboard
   - Or use: `python manage.py run_analysis`

---

## ✨ What's New

The SymbolPerformance model enables:
- **Multi-timeframe ROI tracking** (1h to 1y)
- **Volume analysis** (24h volume + change)
- **Volatility metrics** (standard deviation)
- **Market data** (high/low, market cap)
- **Performance comparison** across assets
- **Historical tracking** (timestamps for each record)

All data is displayed in the dashboard with:
- Color-coded positive/negative returns
- Asset type badges (CRYPTO, GOLD, FX, etc.)
- Current prices
- Complete ROI breakdown

---

**Status**: ✅ **RESOLVED** - Table created, migration recorded, ready to use!

**Last Updated**: 2026-01-11
**Branch**: claude/django-trading-oracle-app-3dgc7
