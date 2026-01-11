# Changelog

All notable changes to the Trading Oracle project will be documented in this file.

## [1.0.0] - 2026-01-10

### Added

#### Core System
- Complete Django-based trading oracle application
- Multi-timeframe analysis (Short: 15m/1h/4h, Medium: 4h/1d, Long: 1d/1w)
- Multi-market support (Spot, Perpetual Futures, Dated Futures, CFD)
- 2-layer decision engine with scoring and rule-based conflict resolution

#### Features (50+ indicators)
- **Technical Indicators**: RSI, MACD, Stochastic, Bollinger Bands, BB Width, ATR, ADX, EMA slopes, Supertrend, VWAP, Volume Ratio
- **Macro Indicators**: DXY, VIX, Real Yields, 10Y Yields
- **Intermarket**: Gold/Silver ratio, Copper/Gold ratio, Miners/Gold (GDX/GLD), GLD flow proxy, BTC dominance
- **Crypto Derivatives**: Funding rates, Open Interest, OI/Volume ratio, Basis/Premium, Liquidation spikes
- **Volume Analysis**: Volume spikes, OBV structure
- **Volatility**: ATR percentiles, BB squeeze detection

#### Data Providers
- CCXT integration for cryptocurrency exchanges (Binance, Coinbase, Kraken)
- yfinance integration for traditional markets (gold, stocks, indices, bonds)
- Macro data provider for DXY, VIX, yields

#### API
- Full REST API with Django REST Framework
- Endpoints: symbols, decisions, features, market-data, analysis-runs
- Support for filtering, pagination, and search
- Bulk query capabilities

#### Admin Interface
- Complete Django Admin configuration
- Color-coded signal badges
- Feature weight management
- Custom per-symbol/timeframe weight overrides
- Decision history with drill-down

#### Async Tasks (Celery)
- Hourly market data fetching for all symbols
- 15-minute derivatives data updates (funding, OI)
- Hourly macro indicator updates
- Daily cleanup of old data (90-day market data, 30-day decisions)
- On-demand analysis via API

#### Management Commands
- `init_oracle` - Initialize database with default symbols, timeframes, features
- `run_analysis` - Manually run analysis for specified symbols

#### Examples & Documentation
- Comprehensive README with setup, usage, and API examples
- Example scripts for programmatic usage
- Example scripts for API usage
- Docker Compose for Redis and PostgreSQL
- Quick start shell script

#### Database Models
- Symbol - Tradable instruments
- MarketType - Market classifications
- Timeframe - Time periods
- Feature - Feature registry with weights
- Decision - Trading decisions with full context
- FeatureContribution - Per-feature scoring breakdown
- MarketData - OHLCV candles
- DerivativesData - Funding, OI, liquidations
- MacroData - Economic indicators
- SentimentData - Sentiment scores (placeholder)
- AnalysisRun - Audit trail for executions
- FeatureWeight - Custom weight overrides

#### Assets Supported
- **Gold**: XAUUSD (spot FX feed), PAXGUSDT (crypto token)
- **Crypto**: BTC, ETH, SOL, BNB, XRP, ADA (extensible to any symbol)

#### Decision Outputs
For each symbol/market/timeframe:
- Signal (STRONG_BUY to STRONG_SELL)
- Bias (Bullish/Neutral/Bearish)
- Confidence (0-100%)
- Trade parameters (Entry, Stop Loss, Take Profit, Risk/Reward)
- Invalidation conditions
- Top 5 feature drivers with contributions
- Full regime context
- All feature contributions saved

### Technical Details

#### Decision Engine
- **Layer 1**: Weighted feature scoring with dynamic timeframe-based weights
- **Layer 2**: Rules and filters
  - Regime detection (trending/ranging, volatility levels, BB squeeze)
  - ADX-based trend confidence adjustment
  - Volatility-based caution filters
  - Technical vs Macro conflict resolution
  - Contrarian signals on extreme positioning

#### Precision Enhancements
- Adaptive weighting per timeframe
- Regime-aware signal generation
- Conflicting indicator resolution
- Extreme positioning detection (funding/liquidations)
- Dynamic stop loss calculation using ATR
- Risk/reward optimization based on confidence

### Configuration
- Configurable feature weights via Django Admin
- Per-symbol/timeframe weight overrides
- Celery beat schedules configurable
- Logging to file and console
- CORS support for frontend integration

### Documentation
- Complete README with installation, usage, examples
- API endpoint documentation
- Management command documentation
- Example scripts for both programmatic and API usage
- Docker Compose setup guide

## [Upcoming]

### Phase 2 Features
- [ ] Real sentiment analysis (news, social media)
- [ ] COT (Commitment of Traders) data integration
- [ ] Actual GLD holdings tracking (not volume proxy)
- [ ] Exchange flow tracking (on-chain data)
- [ ] Divergence detection (RSI/MACD)
- [ ] Advanced structure analysis (pivots, breakouts, higher-highs/lower-lows)
- [ ] Ichimoku Cloud implementation

### Phase 3 Features
- [ ] Backtesting framework
- [ ] Performance analytics dashboard
- [ ] Machine learning layer (optional)
- [ ] Multi-asset correlation matrix
- [ ] WebSocket real-time updates
- [ ] Mobile application
- [ ] Telegram/Discord bot integration
- [ ] Portfolio management

### Infrastructure
- [ ] Kubernetes deployment
- [ ] Grafana monitoring
- [ ] Prometheus metrics
- [ ] API rate limiting
- [ ] Webhook notifications
- [ ] Multi-user support with API keys
