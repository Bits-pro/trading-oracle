# Trading Oracle - Multi-Timeframe Trading Decision System

A sophisticated Django-based trading analysis system that provides multi-timeframe, multi-market trading decisions for Gold and Cryptocurrency markets using a 2-layer decision engine with 50+ technical, macro, and market-specific features.

## Features

### Core Capabilities

- **Multi-Timeframe Analysis**: Short-term (15m, 1h, 4h), Medium-term (4h, 1d), Long-term (1d, 1w)
- **Multi-Market Support**:
  - Spot markets
  - Perpetual futures
  - Derivatives with funding rates, open interest, liquidations
- **Asset Coverage**:
  - Gold: XAUUSD (FX feed), PAXGUSDT (crypto token)
  - Crypto: BTC, ETH, SOL, BNB, XRP, ADA (+ user-extensible)

### Decision System

#### Layer 1: Feature Scoring (50+ Features)

**Technical Indicators**:
- RSI, MACD, Stochastic, Bollinger Bands, Bollinger Band Width
- ATR, ADX with DI+/DI-, EMA slopes, Supertrend, Ichimoku
- VWAP (intraday), Volume Ratio, OBV, CMF/MFI
- Market structure (pivots, break of structure)

**Macro Indicators**:
- DXY (US Dollar Index)
- VIX (fear gauge)
- Real yields (10Y - inflation)
- Nominal yields (TNX)
- Inflation expectations

**Intermarket Relationships**:
- Gold/Silver ratio + momentum
- Copper/Gold ratio (growth proxy)
- Gold miners vs Gold (GDX/GLD)
- GLD holdings (institutional flow)
- BTC dominance (crypto health)

**Crypto-Specific (Derivatives)**:
- Funding rate (long/short bias)
- Open Interest + OI/Volume ratio
- Basis/Premium (perp vs spot)
- Liquidation spikes (reversal signals)

**Sentiment** (placeholder for Phase 2):
- News sentiment
- Fear & Greed Index
- Social media signals

#### Layer 2: Rules & Conflict Resolution

- **Regime Detection**: Trending vs Ranging (ADX), Volatility levels (ATR), BB squeeze
- **Filters**: ADX-based trend reduction, volatility adjustments, squeeze warnings
- **Conflict Resolution**: Technical vs Macro divergence, Funding vs Spot signals
- **Precision Boosters**: Contrarian signals on extreme funding/liquidations

### Decision Output

For each symbol/market type/timeframe combination:
- **Signal**: STRONG_BUY / BUY / WEAK_BUY / NEUTRAL / WEAK_SELL / SELL / STRONG_SELL
- **Bias**: Bullish / Neutral / Bearish
- **Confidence**: 0-100 score
- **Trade Parameters**: Entry, Stop Loss, Take Profit, Risk/Reward ratio
- **Invalidation Conditions**: Conditions that cancel the signal
- **Top Drivers**: Top 5 features with direction, strength, and contribution scores

### API Endpoints

Full REST API built with Django REST Framework:

- `GET /api/symbols/` - List all symbols
- `GET /api/decisions/` - Get decisions with filters
- `GET /api/decisions/latest/` - Latest decisions for all symbols
- `GET /api/decisions/by_symbol/?symbol=BTC` - All decisions for a symbol
- `POST /api/decisions/analyze/` - Trigger new analysis
- `GET /api/features/` - List all features with weights
- `GET /api/market-data/` - OHLCV data
- `GET /api/analysis-runs/{run_id}/` - Check analysis status

### Admin Interface

Django Admin for configuration:
- Manage symbols, market types, timeframes
- Configure features and weights
- Custom feature weights per symbol/timeframe
- View decisions with color-coded signals
- Monitor analysis runs

## Architecture

```
trading-oracle/
├── oracle/                      # Main Django app
│   ├── models.py               # Database models
│   ├── admin.py                # Django admin configuration
│   ├── tasks.py                # Celery tasks
│   ├── features/               # Feature library
│   │   ├── base.py            # Base classes and registry
│   │   ├── technical.py       # Technical indicators
│   │   ├── macro.py           # Macro/intermarket features
│   │   └── crypto.py          # Crypto-specific features
│   ├── engine/                 # Decision engine
│   │   └── decision_engine.py # 2-layer decision system
│   ├── providers/              # Data providers
│   │   ├── base_provider.py
│   │   ├── ccxt_provider.py   # Crypto exchanges (CCXT)
│   │   └── yfinance_provider.py # Traditional markets
│   └── api/                    # REST API
│       ├── serializers.py
│       ├── views.py
│       └── urls.py
├── trading_oracle/             # Django project settings
│   ├── settings.py            # Configuration
│   ├── celery.py              # Celery config
│   └── urls.py                # URL routing
├── requirements.txt            # Python dependencies
└── manage.py                   # Django management
```

## Installation

### Prerequisites

- Python 3.10+
- Redis (for Celery)
- SQLite (default) or PostgreSQL (recommended for production)

### Setup Steps

1. **Clone and navigate to project**:
```bash
cd /path/to/trading-oracle
```

2. **Create virtual environment**:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

**Note**: If `ta-lib` installation fails, you need to install system TA-Lib first:
- **Ubuntu/Debian**: `sudo apt-get install ta-lib`
- **MacOS**: `brew install ta-lib`
- **Windows**: Download from https://github.com/mrjbq7/ta-lib#windows

If TA-Lib is problematic, the system falls back to `pandas-ta` for indicators.

4. **Create logs directory**:
```bash
mkdir logs
```

5. **Run migrations**:
```bash
python manage.py makemigrations
python manage.py migrate
```

6. **Create superuser**:
```bash
python manage.py createsuperuser
```

7. **Load initial data** (optional):
```bash
python manage.py shell
```

Then run this Python code to create initial symbols and timeframes:
```python
from oracle.models import Symbol, MarketType, Timeframe, Feature

# Create market types
MarketType.objects.create(name='SPOT', description='Spot Market', supports_funding=False, supports_open_interest=False)
MarketType.objects.create(name='PERPETUAL', description='Perpetual Futures', supports_funding=True, supports_open_interest=True)
MarketType.objects.create(name='FUTURES', description='Dated Futures', supports_funding=False, supports_open_interest=True)

# Create timeframes
Timeframe.objects.create(name='15m', minutes=15, classification='SHORT', display_order=1)
Timeframe.objects.create(name='1h', minutes=60, classification='SHORT', display_order=2)
Timeframe.objects.create(name='4h', minutes=240, classification='MEDIUM', display_order=3)
Timeframe.objects.create(name='1d', minutes=1440, classification='LONG', display_order=4)
Timeframe.objects.create(name='1w', minutes=10080, classification='LONG', display_order=5)

# Create symbols
# Gold
Symbol.objects.create(symbol='XAUUSD', name='Gold Spot', asset_type='GOLD', base_currency='XAU', quote_currency='USD')
Symbol.objects.create(symbol='PAXGUSDT', name='PAX Gold', asset_type='GOLD', base_currency='PAXG', quote_currency='USDT')

# Crypto
Symbol.objects.create(symbol='BTCUSDT', name='Bitcoin', asset_type='CRYPTO', base_currency='BTC', quote_currency='USDT')
Symbol.objects.create(symbol='ETHUSDT', name='Ethereum', asset_type='CRYPTO', base_currency='ETH', quote_currency='USDT')
Symbol.objects.create(symbol='SOLUSDT', name='Solana', asset_type='CRYPTO', base_currency='SOL', quote_currency='USDT')
Symbol.objects.create(symbol='BNBUSDT', name='Binance Coin', asset_type='CRYPTO', base_currency='BNB', quote_currency='USDT')
Symbol.objects.create(symbol='XRPUSDT', name='Ripple', asset_type='CRYPTO', base_currency='XRP', quote_currency='USDT')
Symbol.objects.create(symbol='ADAUSDT', name='Cardano', asset_type='CRYPTO', base_currency='ADA', quote_currency='USDT')

# Features (auto-registered, but you can customize weights in admin)
print("Initial data loaded!")
```

## Usage

### Starting the Services

You need to run 3 services:

**Terminal 1 - Django Server**:
```bash
python manage.py runserver
```

**Terminal 2 - Celery Worker**:
```bash
celery -A trading_oracle worker -l info
```

**Terminal 3 - Celery Beat (Scheduler)**:
```bash
celery -A trading_oracle beat -l info
```

### Using the API

#### 1. Trigger Analysis

```bash
curl -X POST http://localhost:8000/api/decisions/analyze/ \
  -H "Content-Type: application/json" \
  -d '{
    "symbols": ["BTCUSDT", "XAUUSD"],
    "market_types": ["SPOT", "PERPETUAL"],
    "timeframes": ["1h", "4h", "1d"]
  }'
```

Response:
```json
{
  "run_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PENDING",
  "message": "Analysis queued..."
}
```

#### 2. Check Analysis Status

```bash
curl http://localhost:8000/api/analysis-runs/550e8400-e29b-41d4-a716-446655440000/
```

#### 3. Get Latest Decisions

```bash
curl http://localhost:8000/api/decisions/latest/
```

#### 4. Get Decisions for Specific Symbol

```bash
curl http://localhost:8000/api/decisions/by_symbol/?symbol=BTCUSDT
```

Response:
```json
{
  "symbol": "BTCUSDT",
  "name": "Bitcoin",
  "asset_type": "CRYPTO",
  "decisions": {
    "SPOT": {
      "1h": [{
        "signal": "BUY",
        "bias": "BULLISH",
        "confidence": 78,
        "entry_price": "45000.00",
        "stop_loss": "44200.00",
        "take_profit": "47400.00",
        "risk_reward": "3.00",
        "invalidation_conditions": [
          "Close below EMA50 (44800.00)",
          "ADX drops below 18 (trend failure)"
        ],
        "top_drivers": [
          {
            "name": "MACD",
            "category": "TECHNICAL",
            "direction": 1,
            "strength": 0.85,
            "contribution": 0.85,
            "explanation": "MACD crossed above signal - bullish"
          }
        ]
      }]
    },
    "PERPETUAL": {
      "1h": [...]
    }
  }
}
```

#### 5. Bulk Query Multiple Symbols

```bash
curl "http://localhost:8000/api/decisions/bulk/?symbols=BTCUSDT,ETHUSDT,XAUUSD"
```

### Using Django Admin

1. Navigate to http://localhost:8000/admin/
2. Login with superuser credentials
3. Configure:
   - **Symbols**: Add/edit tradable symbols
   - **Features**: Adjust feature weights per timeframe
   - **Feature Weights**: Create custom weights for specific symbol/timeframe combos
   - **Decisions**: View all generated decisions with color-coded signals

### Celery Periodic Tasks

The system automatically runs these tasks:

- **Every 1 hour**: Fetch market data (OHLCV) for all symbols
- **Every 15 minutes**: Fetch derivatives data (funding, OI) for crypto
- **Every 1 hour**: Fetch macro indicators (DXY, VIX, yields)
- **Daily**: Cleanup old data (keeps 90 days market data, 30 days decisions)

You can manually trigger tasks:
```bash
python manage.py shell
```

```python
from oracle.tasks import run_analysis, fetch_market_data

# Trigger analysis
run_analysis.delay('manual-run-id')

# Fetch market data
fetch_market_data.delay()
```

## Configuration

### Adding New Features

1. Create feature class in `oracle/features/`:
```python
from oracle.features.base import BaseFeature, FeatureResult

class MyNewFeature(BaseFeature):
    category = 'TECHNICAL'

    def calculate(self, df, symbol, timeframe, market_type, context=None):
        # Your calculation logic
        value = ...  # Calculate indicator
        direction = ...  # -1, 0, or 1
        strength = ...  # 0.0 to 1.0

        return FeatureResult(
            name='MyNewFeature',
            category=self.category,
            raw_value=value,
            direction=direction,
            strength=strength,
            explanation="..."
        )

# Register it
from oracle.features.base import registry
registry.register('MyNewFeature', MyNewFeature)
```

2. Add to database via Django Admin or shell:
```python
from oracle.models import Feature

Feature.objects.create(
    name='MyNewFeature',
    category='TECHNICAL',
    description='Description of what it does',
    weight_short=1.0,
    weight_medium=0.8,
    weight_long=0.5
)
```

### Adjusting Feature Weights

**Via Django Admin**:
- Go to Features → Select feature → Adjust `weight_short`, `weight_medium`, `weight_long`

**Via API** (programmatically):
```python
from oracle.models import Feature

feature = Feature.objects.get(name='RSI')
feature.weight_short = 1.5  # Increase importance for short-term
feature.save()
```

**Per-Symbol Custom Weights**:
```python
from oracle.models import FeatureWeight, Feature, Symbol, Timeframe

FeatureWeight.objects.create(
    feature=Feature.objects.get(name='FundingRate'),
    symbol=Symbol.objects.get(symbol='BTCUSDT'),
    timeframe=Timeframe.objects.get(name='1h'),
    weight=2.0  # Double the weight for BTC 1h
)
```

### Environment Variables

Create `.env` file (optional):
```bash
DEBUG=True
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/dbname
REDIS_URL=redis://localhost:6379/0
BINANCE_API_KEY=your-api-key
BINANCE_SECRET_KEY=your-secret-key
```

Update `settings.py` to use `django-environ`:
```python
import environ
env = environ.Env()
environ.Env.read_env()

SECRET_KEY = env('SECRET_KEY')
DEBUG = env.bool('DEBUG', default=False)
```

## Advanced Usage

### Custom Decision Logic

Override decision engine logic in `oracle/engine/decision_engine.py`:

```python
class CustomLayer2Rules(Layer2Rules):
    def apply_rules(self, raw_score):
        # Your custom rule logic
        ...
        return signal, bias, confidence, regime_context
```

### Backtesting (Future Enhancement)

Structure supports backtesting by:
1. Fetching historical decisions: `Decision.objects.filter(created_at__range=...)`
2. Comparing signals vs actual price moves
3. Calculating win rate, avg R:R realized, etc.

### Webhooks/Notifications (Future Enhancement)

Add webhook support in `oracle/tasks.py`:
```python
import requests

@shared_task
def send_decision_webhook(decision_id):
    decision = Decision.objects.get(id=decision_id)
    requests.post('https://your-webhook-url.com', json={
        'symbol': decision.symbol.symbol,
        'signal': decision.signal,
        'confidence': decision.confidence
    })
```

## Database Schema

Key models:
- **Symbol**: Tradable instruments
- **MarketType**: SPOT, PERPETUAL, FUTURES
- **Timeframe**: 15m, 1h, 4h, 1d, 1w
- **Feature**: Feature registry with weights
- **Decision**: Trading decisions with full context
- **FeatureContribution**: Individual feature scores per decision
- **MarketData**: OHLCV candles
- **DerivativesData**: Funding, OI, liquidations
- **MacroData**: DXY, VIX, yields
- **AnalysisRun**: Audit trail for each analysis execution

## Testing

Run tests (to be implemented):
```bash
python manage.py test oracle
```

## Production Deployment

### Use PostgreSQL
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'trading_oracle',
        'USER': 'user',
        'PASSWORD': 'password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

### Set DEBUG=False
```python
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com']
```

### Use production-grade task queue
- Deploy Celery workers with supervisor/systemd
- Use Redis Cluster or RabbitMQ for broker
- Monitor with Flower: `celery -A trading_oracle flower`

### Serve with Gunicorn + Nginx
```bash
gunicorn trading_oracle.wsgi:application --bind 0.0.0.0:8000
```

## Troubleshooting

### TA-Lib Installation Issues
If you can't install TA-Lib:
1. Remove `ta-lib==0.4.28` from requirements.txt
2. The system will use `pandas-ta` as fallback
3. Some advanced indicators may not be available

### Redis Connection Error
Make sure Redis is running:
```bash
redis-cli ping
```
Should return `PONG`.

### CCXT Errors
If crypto data fetching fails:
- Check exchange API status
- Verify symbol format (BTC/USDT vs BTCUSDT)
- Add API keys if required for certain endpoints

## Roadmap

### Phase 1 (Current)
- [x] Core decision engine
- [x] 50+ technical/macro/crypto features
- [x] Multi-timeframe/market support
- [x] REST API
- [x] Django Admin
- [x] Celery periodic tasks

### Phase 2 (Future)
- [ ] Sentiment analysis (news, social media)
- [ ] COT data integration
- [ ] GLD holdings scraper
- [ ] Exchange flow tracking
- [ ] Divergence detection (RSI/MACD)
- [ ] Advanced structure analysis (pivots, breakouts)

### Phase 3 (Long-term)
- [ ] Backtesting framework
- [ ] Performance analytics dashboard
- [ ] Machine learning layer (optional)
- [ ] Multi-asset correlation matrix
- [ ] WebSocket real-time updates
- [ ] Mobile app

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

## License

This project is proprietary. All rights reserved.

## Support

For issues and questions:
- Create an issue in the repository
- Email: support@trading-oracle.com (if applicable)

## Acknowledgments

- CCXT for crypto exchange data
- yfinance for traditional market data
- Django & DRF for the framework
- Celery for task scheduling

---

**Disclaimer**: This software is for educational and research purposes. Trading financial instruments carries risk. Past performance does not guarantee future results. Always do your own research and consult with a financial advisor before trading.
