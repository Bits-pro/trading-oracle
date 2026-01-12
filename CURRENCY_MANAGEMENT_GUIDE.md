# Currency Management & Enhanced Live Monitoring Guide

## Overview

Your Trading Oracle now has powerful currency management and enhanced live monitoring features! This guide explains how to use all the new capabilities.

---

## 🪙 Currency Management

### Accessing the Page
Navigate to: **Dashboard → Currencies** or visit `/dashboard/symbols/`

### What You Can Do

#### 1. **View All Currencies**
- See complete list of all configured currencies
- Each card shows:
  - Symbol and full name
  - Asset type (CRYPTO, GOLD, COMMODITY, etc.)
  - Current status (Active/Inactive)
  - Trading pair (e.g., BTC/USDT, XAU/USD)
  - Total decisions made
  - Time since last analysis

#### 2. **Toggle Active/Inactive**
Each currency card has action buttons:
- **Active currencies**: Click "Deactivate" to exclude from analysis
- **Inactive currencies**: Click "Activate" to include in analysis

**Important:** Only **active** currencies are analyzed when you run "Run Analysis"!

#### 3. **Filter Currencies**
Use the filter dropdown to view:
- **All Symbols**: Complete list
- **Active Only**: Only currencies currently being analyzed
- **Inactive Only**: Currencies excluded from analysis
- **By Type**: Filter by Crypto, Gold, Commodity, etc.

#### 4. **Statistics Dashboard**
Top banner shows:
- Total Symbols count
- Active currencies count (green)
- Inactive currencies count (gray)

### Use Cases

**Example 1: Focus on Specific Markets**
```
1. Go to Currencies page
2. Deactivate all but BTC and Gold
3. Run analysis → Only BTC and Gold analyzed
4. Faster analysis, reduced API calls
```

**Example 2: Add New Currency**
```
1. Admin adds new symbol to database
2. Go to Currencies page
3. Click "Activate" on new symbol
4. Next analysis run includes it
```

**Example 3: Temporary Exclusion**
```
1. Market closed for a currency (e.g., weekend for gold spot)
2. Deactivate temporarily
3. Reactivate when market reopens
4. No failed API calls during closure
```

---

## 📊 Enhanced Live Monitoring

### Accessing the Page
Navigate to: **Dashboard → Live** or visit `/dashboard/live-enhanced/`

### New Features

#### 1. **Essential Indicators at a Glance**

Each currency card displays:

**Top Section (Always Visible):**
- **Current Price**: Real-time price in USD
- **24h Change**: Percentage change with color coding
  - Green = Positive
  - Red = Negative
- **24h Volume**: Trading volume in last 24 hours

**ROI Quick View:**
Five period buttons showing return on investment:
- **1H**: Last hour performance
- **1D**: Last 24 hours performance
- **1W**: Last week performance
- **1M**: Last month performance
- **1Y**: Last year performance

Color coding:
- 🟢 Green: Positive ROI
- 🔴 Red: Negative ROI
- ⚫ Gray: No data available

#### 2. **Interactive Price Chart**

**Period Selector Buttons:**
- Click any period (1H, 1D, 1W, 1M, 1Y) to update chart
- Active period highlighted in indigo
- Chart updates instantly without page reload

**Chart Features:**
- Line chart with filled area
- Hover to see exact price at any point
- Responsive design
- Smooth animations

#### 3. **Latest Trading Signal**

Shows the most recent analysis result:
- **Signal Type**: STRONG_BUY, BUY, NEUTRAL, SELL, etc.
- **Confidence**: Percentage confidence (e.g., 85%)
- **Timeframe**: Analysis timeframe (1h, 4h, 1d)
- **Time Ago**: "2 hours ago", "15 minutes ago", etc.

#### 4. **"Show More" Expandable Section**

Click "Show More Details" to reveal:

**Technical Indicators Panel:**
- Top 6 most impactful indicators
- Current values
- Direction (Bullish/Bearish/Neutral)
- Color-coded for quick assessment

**Trade Levels Panel:**
- Entry Price: Recommended entry point
- Stop Loss: Risk management level
- Take Profit: Target exit price
- Risk/Reward Ratio: Expected R:R

**Market Statistics:**
- Total Decisions: Historical analysis count
- Average Confidence: Mean confidence across all decisions
- Link to full history

---

## 📱 User Interface Highlights

### Navigation Updates

**New Menu Structure:**
1. **Overview** - Dashboard home
2. **Live** - Enhanced live monitoring ⭐ NEW
3. **Currencies** - Currency management ⭐ NEW
4. **Indicators** - Detailed indicator analysis
5. **Features** - Feature performance tracking
6. **History** - Decision history

### Responsive Design

- **Desktop**: 2-column grid for currency cards
- **Tablet**: Single column, full width
- **Mobile**: Optimized card layout

### Color Scheme

- **Active Status**: Green badge with pulse dot
- **Inactive Status**: Gray badge
- **Positive Changes**: Green text
- **Negative Changes**: Red text
- **Signal Types**: Color-coded badges (green=buy, red=sell, gray=neutral)

---

## 🔧 Technical Details

### API Endpoints

**Currency Management:**
```
POST /dashboard/api/symbols/toggle/
Body: {"symbol_id": 1, "is_active": true}
Response: {"success": true, "symbol": "BTCUSDT", "is_active": true}
```

**Chart Data:**
```
GET /dashboard/api/chart-data/BTCUSDT/?period=1d
Response: {"labels": [...], "prices": [...]}
```

### Data Sources

**ROI Calculation:**
- Uses `MarketData` table
- Compares current price to historical price at period start
- Formula: `((current - past) / past) * 100`

**Chart Data:**
- Fetched from `MarketData` table
- Filtered by time period
- Ordered chronologically
- Returns timestamps and closing prices

**Indicators:**
- Fetched from `FeatureContribution` table
- Linked to latest decision
- Top 6 by contribution value

---

## 🎯 Best Practices

### Currency Management

1. **Start Small**: Begin with 2-3 currencies to test
2. **Monitor Performance**: Activate currencies you actively trade
3. **Seasonal Adjustments**: Deactivate during market closures
4. **API Efficiency**: Fewer active = faster analysis + lower costs

### Live Monitoring

1. **Check Multiple Periods**: Look at 1H, 1D, and 1W ROI together
2. **Confirm with Chart**: Visual confirmation of trends
3. **Use "Show More"**: Deep dive only when needed
4. **Auto-Refresh**: Page auto-refreshes every 60 seconds

### Workflow Examples

**Morning Routine:**
```
1. Open Live Monitoring
2. Check ROI for all currencies (1D, 1W)
3. Expand "Show More" for currencies with significant changes
4. Review technical indicators
5. Check latest signals
6. Make trading decisions
```

**Before Analysis Run:**
```
1. Go to Currencies page
2. Verify correct currencies are active
3. Deactivate any you don't want analyzed
4. Return to Overview
5. Click "Run Analysis"
6. Check Live Monitoring for updated data
```

---

## ⚡ Quick Reference

### Keyboard Shortcuts
- None currently (feature request for future)

### Color Codes

| Color | Meaning |
|-------|---------|
| 🟢 Green | Bullish, Positive, Active, Buy |
| 🔴 Red | Bearish, Negative, Sell |
| ⚫ Gray | Neutral, Inactive, No data |
| 🔵 Indigo | Selected, Active UI element |

### Status Indicators

| Symbol | Status |
|--------|--------|
| 🟢 Active | Included in analysis |
| ⚫ Inactive | Excluded from analysis |
| 🔴 Error | Data fetch failed |
| ⏸️ Paused | Temporarily disabled |

---

## 🐛 Troubleshooting

### Problem: Currency won't activate
**Solution:** Check that symbol has valid provider configuration

### Problem: ROI showing "—"
**Solution:** Not enough historical data yet, wait for more market data collection

### Problem: Chart not loading
**Solution:**
1. Check browser console for errors
2. Verify MarketData exists for symbol
3. Try different time period

### Problem: "Show More" not expanding
**Solution:**
1. Clear browser cache
2. Verify Alpine.js is loaded (check browser console)
3. Try different browser

---

## 📊 Performance Tips

1. **Limit Active Currencies**: 5-10 for optimal performance
2. **Use Filters**: Don't load all symbols at once
3. **Close Unused Cards**: Collapse "Show More" when not needed
4. **Monitor API Calls**: More active = more provider requests

---

## 🚀 Next Steps

1. **Explore Currencies Page**:
   - Visit `/dashboard/symbols/`
   - Review current active/inactive status
   - Adjust based on your trading focus

2. **Check Enhanced Live**:
   - Visit `/dashboard/live-enhanced/`
   - Explore different time periods
   - Test "Show More" functionality

3. **Run Analysis**:
   - Go to Overview page
   - Click "Run Analysis"
   - Return to Live page to see updated data

4. **Optimize Setup**:
   - Deactivate currencies you don't trade
   - Keep 3-5 active for best performance
   - Re-evaluate weekly based on trading strategy

---

## 📧 Support

If you encounter issues or have feature requests:
1. Check error logs in Django admin
2. Verify database migrations are up to date
3. Review browser console for JavaScript errors
4. Check network tab for failed API calls

---

## ✨ Feature Highlights

**What's New:**
✅ Currency activation/deactivation
✅ ROI tracking (5 time periods)
✅ Interactive price charts
✅ Expandable detail sections
✅ Live trading signal display
✅ Top technical indicators
✅ Trade level recommendations
✅ Enhanced navigation
✅ Responsive design
✅ Auto-refresh capability

**Coming Soon:**
- Real-time WebSocket updates
- Customizable indicator selection
- Alert notifications
- Export capabilities
- Mobile app

---

Enjoy your enhanced Trading Oracle! 🎉
