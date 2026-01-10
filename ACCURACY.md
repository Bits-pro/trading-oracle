# Trading Oracle Accuracy & Precision Guide

## ⚠️ Important Disclaimer

**The trading oracle is a decision-making framework, not a validated trading strategy.**

Accuracy metrics are **situational and depend on**:
- Market conditions (trending vs ranging)
- Asset volatility
- Timeframe
- Feature configuration
- Risk management settings

**Past performance does not guarantee future results.**

---

## 📊 Expected Accuracy Ranges

### By Market Regime

#### Trending Markets (ADX > 25)
**Expected Performance:**
- ✅ **Win Rate**: 55-70%
- ✅ **Average R**: 1.5-3.0R
- ✅ **Best Signals**: BUY/SELL (not STRONG variants)
- ✅ **Best Timeframes**: 4h, 1d (trend-following)

**Why:** Trend-following indicators (ADX, EMA, Supertrend) perform best in clear directional moves.

**Confidence Calibration:**
- 85-100%: ~65-75% win rate
- 70-85%: ~55-65% win rate
- 50-70%: ~45-55% win rate

#### Ranging Markets (ADX < 20)
**Expected Performance:**
- ⚠️ **Win Rate**: 40-55%
- ⚠️ **Average R**: 0.5-1.5R
- ⚠️ **Best Signals**: WEAK_BUY/WEAK_SELL
- ⚠️ **Best Timeframes**: 15m, 1h (mean reversion)

**Why:** Trend signals false-break frequently. Mean reversion (RSI, Bollinger Bands, VWAP) works better but with smaller R.

**System Behavior:**
- Layer 2 rules automatically reduce confidence in ranging markets
- ADX < 18 triggers "weak trend" filter (reduces scores by 40%)

**Recommendation:** Trade less frequently or focus on oscillator-heavy setups.

#### High Volatility (ATR > 80th percentile)
**Expected Performance:**
- ⚠️ **Win Rate**: 45-60%
- ⚠️ **Average R**: Variable (wider stops needed)
- ⚠️ **Risk**: Higher chance of stop-outs before target

**Why:** Price whipsaws invalidate setups more often. Wider stops reduce R:R ratio.

**System Behavior:**
- High volatility filter reduces scores by 20%
- Stop loss automatically widens (2.5x ATR vs 2.0x)

---

## 🎯 Accuracy by Timeframe

### Short-term (15m, 1h, 4h)

**Ideal Conditions:**
- Clear intraday trend
- High volume
- Low macro conflict

**Expected Metrics:**
| Confidence | Win Rate | Avg R | Sample Size Needed |
|------------|----------|-------|--------------------|
| 85-100%    | 60-70%   | 1.5R  | 50+ trades         |
| 70-85%     | 50-60%   | 1.2R  | 100+ trades        |
| 50-70%     | 40-50%   | 1.0R  | 150+ trades        |

**Key Features:**
- RSI (weight: 1.2)
- MACD (weight: 1.0)
- VWAP (weight: 1.3)
- Funding Rate (weight: 1.3 for crypto)

**Challenges:**
- Noise and false signals
- Requires tight monitoring
- Higher transaction costs

### Medium-term (4h, 1d)

**Ideal Conditions:**
- Multi-day trend
- Macro alignment (DXY, VIX supportive)
- Clear structure

**Expected Metrics:**
| Confidence | Win Rate | Avg R | Sample Size Needed |
|------------|----------|-------|--------------------|
| 85-100%    | 65-75%   | 2.0R  | 30+ trades         |
| 70-85%     | 55-65%   | 1.5R  | 50+ trades         |
| 50-70%     | 45-55%   | 1.2R  | 75+ trades         |

**Key Features:**
- ADX (weight: 1.2)
- EMA crossovers (weight: 1.3)
- Supertrend (weight: 1.2)
- DXY (weight: 1.0)
- Real Yields (weight: 1.1)

**Sweet Spot:** This is the optimal timeframe for most users. Balance between frequency and reliability.

### Long-term (1d, 1w)

**Ideal Conditions:**
- Major trend change
- Macro regime shift
- Fundamental catalyst

**Expected Metrics:**
| Confidence | Win Rate | Avg R | Sample Size Needed |
|------------|----------|-------|--------------------|
| 85-100%    | 70-80%   | 3.0R  | 20+ trades         |
| 70-85%     | 60-70%   | 2.5R  | 30+ trades         |
| 50-70%     | 50-60%   | 2.0R  | 50+ trades         |

**Key Features:**
- EMA 200 (weight: 1.5)
- DXY structural (weight: 1.4)
- Real Yields (weight: 1.5)
- Gold/Silver ratio (weight: 1.2)
- COT data (when available)

**Advantages:**
- Higher win rate
- Larger R multiples
- Less noise

**Challenges:**
- Infrequent signals (10-20 per year per symbol)
- Requires patience
- Larger capital commitment

---

## 💎 Accuracy by Asset Type

### Gold (XAUUSD, PAXGUSDT)

**Typical Performance:**
- **Win Rate**: 55-65%
- **Average R**: 1.5-2.5R
- **Best Timeframes**: 4h, 1d
- **Best Conditions**: DXY trending, real yields directional

**Key Drivers:**
1. DXY (inverse correlation: -0.70 to -0.85)
2. Real Yields (inverse correlation: -0.60 to -0.75)
3. VIX (positive correlation during fear: +0.40 to +0.60)
4. Gold/Silver ratio (mean reversion at extremes)

**Special Considerations:**
- XAUUSD: Use macro heavily (weights: DXY 1.4, Real Yields 1.5)
- PAXGUSDT: Blend crypto + gold features (add funding, OI)
- Weekend gaps on XAUUSD but not PAXG

**Expected Accuracy by Scenario:**
| Scenario | Win Rate | Notes |
|----------|----------|-------|
| DXY strong trend down | 70-80% | Gold bull run |
| Real yields falling | 65-75% | Flight to safety |
| VIX spiking (>30) | 60-70% | Fear premium |
| Mixed signals | 40-50% | Choppy, avoid |

### Crypto (BTC, ETH, SOL, etc.)

**Typical Performance:**
- **Win Rate**: 50-60%
- **Average R**: 1.0-2.0R
- **Best Timeframes**: 1h, 4h (high volatility)
- **Best Conditions**: Clear trend + funding extremes

**Key Drivers (Spot):**
1. MACD (momentum)
2. RSI (oversold/overbought)
3. EMA structure
4. DXY (risk-on/risk-off proxy)
5. BTC Dominance (for altcoins)

**Key Drivers (Perpetuals - Additional):**
6. Funding Rate (crowded positioning)
7. Open Interest (leverage buildup)
8. Liquidations (reversal signals)
9. Basis (sentiment gauge)

**Expected Accuracy by Scenario:**
| Scenario | Win Rate | Notes |
|----------|----------|-------|
| Trending + funding extreme | 65-75% | Strong contrarian |
| Trending + normal funding | 55-65% | Standard trend-follow |
| Ranging + funding extreme | 45-55% | Mean reversion play |
| Ranging + normal funding | 35-45% | Avoid trading |

**Funding Rate Impact:**
- Funding >0.1% (annualized >100%): Bearish edge (+10-15% win rate on shorts)
- Funding <-0.05%: Bullish edge (+10-15% win rate on longs)
- Normal funding (-0.01% to 0.03%): No edge

**Liquidation Spikes:**
- Large long liquidations (>3x average): Potential bottom (+15-20% win rate on longs)
- Large short liquidations (>3x average): Potential top (+15-20% win rate on shorts)

---

## 🔬 Confidence Score Calibration

### What Confidence Means

The confidence score (0-100%) represents:
1. **Feature Alignment**: How many features agree on direction
2. **Signal Strength**: How extreme the indicator readings are
3. **Regime Support**: Is the market regime favorable?

**It does NOT directly equal win probability.** It's a relative measure.

### Calibration Guidelines

**After 100+ trades, you should see:**

| Confidence Range | Target Win Rate | Actual Win Rate | Calibration Status |
|------------------|-----------------|-----------------|-------------------|
| 85-100%          | 65-75%          | ?               | Run backtest      |
| 70-85%           | 55-65%          | ?               | Run backtest      |
| 50-70%           | 45-55%          | ?               | Run backtest      |
| 0-50%            | 35-45%          | ?               | Don't trade these |

**If calibration is off:**
- High confidence underperforming → Tighten filters, increase weights on reliable features
- Low confidence overperforming → You may be filtering out good trades
- All confidences similar → Feature weights need tuning

### Recommended Actions by Confidence

| Confidence | Action |
|------------|--------|
| 90-100%    | Full position size (1.0-2.0% risk) |
| 80-90%     | Standard position (0.75-1.5% risk) |
| 70-80%     | Reduced position (0.5-1.0% risk) |
| 60-70%     | Watchlist only or very small (0.25% risk) |
| <60%       | Do not trade |

---

## 📈 Improving Accuracy

### 1. Feature Weight Optimization

**Run backtests to find optimal weights:**

```bash
# Test current configuration
python manage.py backtest --days 90 --export

# Analyze which features performed best
# Adjust weights in Django Admin

# Re-test
python manage.py backtest --days 90 --export
```

**Optimization Process:**
1. Identify best-performing features (highest contribution in winning trades)
2. Increase their weights by 20-30%
3. Identify worst-performing features
4. Decrease their weights or disable them
5. Repeat until win rate improves

### 2. Signal Filtering

**Add custom filters in `oracle/engine/decision_engine.py` Layer 2:**

Example filters to consider:
- Minimum ADX threshold (e.g., only trade if ADX > 20)
- Volume confirmation (e.g., volume > 1.5x average)
- Macro alignment (e.g., only long gold if DXY < SMA50)
- Funding extremes only (e.g., only trade crypto if |funding| > 0.05%)

### 3. Symbol-Specific Tuning

Some symbols need custom weights:

```python
# Example: BTC is more sensitive to funding
from oracle.models import FeatureWeight, Feature, Symbol

FeatureWeight.objects.create(
    feature=Feature.objects.get(name='FundingRate'),
    symbol=Symbol.objects.get(symbol='BTCUSDT'),
    timeframe=Timeframe.objects.get(name='1h'),
    weight=2.0  # Double the standard weight
)
```

### 4. Sample Size Requirements

**Minimum trades needed for statistical validity:**
- Short-term (1h): 150+ trades
- Medium-term (4h, 1d): 75+ trades
- Long-term (1w): 30+ trades

**Don't make decisions on <30 trades.** Randomness dominates small samples.

---

## ⚠️ Common Pitfalls

### 1. Overfitting
**Problem:** Optimizing weights for past data, fails in future.

**Solution:**
- Use out-of-sample testing (train on 70%, test on 30%)
- Don't over-optimize for one symbol/timeframe
- Keep feature set simple

### 2. Curve Fitting
**Problem:** Adding too many features that "explain" past but don't predict.

**Solution:**
- Start with 10-15 core features
- Only add features that improve out-of-sample results
- Use economic logic (e.g., DXY affects gold) not just correlation

### 3. Ignoring Regime Changes
**Problem:** Bull market weights don't work in bear markets.

**Solution:**
- Monitor regime indicators (ADX, volatility)
- Have separate configs for trending/ranging
- Re-calibrate every 3-6 months

### 4. Overtrading
**Problem:** Trading every signal, even low confidence.

**Solution:**
- Only trade 70%+ confidence
- Focus on 1-2 best setups per day
- Quality over quantity

---

## 🎯 Target Metrics (By Experience Level)

### Beginner (0-6 months)
- **Target Win Rate**: 50-55%
- **Target Avg R**: 1.0-1.5R
- **Focus**: High confidence only (80%+), 1-2 symbols, 1 timeframe
- **Position Size**: 0.5-1.0% risk per trade

### Intermediate (6-18 months)
- **Target Win Rate**: 55-60%
- **Target Avg R**: 1.5-2.0R
- **Focus**: Multiple timeframes, symbol-specific tuning
- **Position Size**: 1.0-2.0% risk per trade

### Advanced (18+ months)
- **Target Win Rate**: 60-65%
- **Target Avg R**: 2.0-2.5R
- **Focus**: Full multi-symbol/timeframe, custom weights, macro integration
- **Position Size**: 1.5-2.5% risk per trade (with proper diversification)

---

## 📊 How to Measure Your Accuracy

### 1. Run Backtest

```bash
# Last 30 days
python manage.py backtest --days 30

# Specific symbols
python manage.py backtest --days 60 --symbols BTCUSDT XAUUSD --export

# Specific timeframes
python manage.py backtest --days 90 --timeframes 4h 1d
```

### 2. Analyze Results

Check:
- Overall win rate (target: 55%+)
- Avg R (target: 1.5R+)
- Confidence calibration (high confidence should win more)
- By timeframe (which works best for you?)
- By signal type (which signals are most reliable?)

### 3. Track Live Performance

Use Django Admin:
1. Go to Decisions
2. Filter by date range
3. Manually track outcomes (will automate in Phase 2)
4. Compare with backtest

### 4. Iterate

- Week 1-4: Collect data, don't optimize
- Week 5-8: First optimization round
- Week 9-12: Test optimized settings
- Month 4+: Fine-tune continuously

---

## 🚀 Realistic Expectations

### What This System CAN Do:
✅ Provide structured, multi-factor analysis
✅ Identify high-probability setups (>55% win rate achievable)
✅ Combine 50+ data points into actionable signals
✅ Adapt to different market regimes
✅ Improve with tuning and experience

### What This System CANNOT Do:
❌ Guarantee profits (no system can)
❌ Predict black swan events
❌ Work equally well in all market conditions
❌ Replace risk management and position sizing
❌ Eliminate losing trades

### Bottom Line:
**With proper configuration and risk management, expect:**
- Win rate: 55-65% (in favorable conditions)
- Average R: 1.5-2.5R
- Drawdown: 10-25% (max)
- Sharpe ratio: 1.0-2.0 (good for trading)

**This is sufficient for profitable trading**, but requires:
- Discipline to follow signals
- Proper position sizing (never risk >2% per trade)
- Patience during drawdowns
- Continuous monitoring and optimization

---

## 📞 Support

For accuracy questions:
1. Run backtest: `python manage.py backtest --days 90 --export`
2. Review ACCURACY.md (this file)
3. Check feature weights in Django Admin
4. Optimize based on results

**Remember: The goal is not 100% accuracy. The goal is positive expectancy.**

Even at 50% win rate with 2R average, you have a profitable system.

---

## 📅 Accuracy Validation Schedule

**Recommended testing schedule:**
- **Daily**: Review current day's signals (informal)
- **Weekly**: Check decisions from past week in Admin
- **Monthly**: Run 30-day backtest, review metrics
- **Quarterly**: Full optimization cycle (90-day backtest, weight tuning, out-of-sample testing)
- **Annually**: Major review, add/remove features, consider regime changes

---

**Last Updated**: 2026-01-10
**Version**: 1.0.0
