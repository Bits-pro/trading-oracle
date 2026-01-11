"""
CCXT Provider for cryptocurrency data
Supports spot and derivatives (perpetuals, futures)
"""
import ccxt
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .base_provider import BaseProvider


class CCXTProvider(BaseProvider):
    """
    Provider for crypto exchange data using CCXT

    Supports:
    - Spot markets
    - Perpetual futures
    - Derivatives data (funding, OI)
    """

    def __init__(self, exchange_name: str = 'binance', config: Optional[Dict] = None):
        super().__init__(config)
        self.exchange_name = exchange_name
        self.exchange = self._init_exchange()

    def _init_exchange(self):
        """Initialize CCXT exchange"""
        exchange_class = getattr(ccxt, self.exchange_name)
        exchange = exchange_class(self.config)

        # Load markets
        exchange.load_markets()

        return exchange

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500
    ) -> pd.DataFrame:
        """
        Fetch OHLCV data

        Args:
            symbol: Trading pair (e.g., 'BTC/USDT', 'ETH/USDT')
            timeframe: Timeframe string (e.g., '1h', '4h', '1d')
            start_time: Start datetime
            end_time: End datetime
            limit: Number of candles

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        since = None
        if start_time:
            since = int(start_time.timestamp() * 1000)

        # Fetch data
        ohlcv = self.exchange.fetch_ohlcv(
            symbol=symbol,
            timeframe=timeframe,
            since=since,
            limit=limit
        )

        # Convert to DataFrame
        df = pd.DataFrame(
            ohlcv,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )

        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

        # Filter by end_time if specified
        if end_time:
            df = df[df['timestamp'] <= end_time]

        return df

    def fetch_ticker(self, symbol: str) -> Dict:
        """
        Fetch current ticker

        Returns:
            Dict with ticker data
        """
        ticker = self.exchange.fetch_ticker(symbol)
        return {
            'last_price': ticker.get('last'),
            'bid': ticker.get('bid'),
            'ask': ticker.get('ask'),
            'volume_24h': ticker.get('quoteVolume'),
            'high_24h': ticker.get('high'),
            'low_24h': ticker.get('low'),
            'timestamp': datetime.fromtimestamp(ticker['timestamp'] / 1000) if ticker.get('timestamp') else datetime.now()
        }

    def fetch_funding_rate(self, symbol: str) -> Dict:
        """
        Fetch current funding rate (for perpetuals)

        Returns:
            Dict with funding rate data
        """
        try:
            # Binance method
            if self.exchange_name == 'binance':
                # Convert symbol format (BTC/USDT -> BTCUSDT)
                symbol_formatted = symbol.replace('/', '')

                funding_rate = self.exchange.fapiPublicGetPremiumIndex({
                    'symbol': symbol_formatted
                })

                return {
                    'rate': float(funding_rate['lastFundingRate']),
                    'next_funding_time': datetime.fromtimestamp(int(funding_rate['nextFundingTime']) / 1000),
                    'mark_price': float(funding_rate['markPrice']),
                    'index_price': float(funding_rate['indexPrice'])
                }
            else:
                # Generic method
                funding = self.exchange.fetch_funding_rate(symbol)
                return {
                    'rate': funding.get('fundingRate', 0),
                    'next_funding_time': funding.get('fundingTimestamp'),
                    'mark_price': funding.get('markPrice'),
                    'index_price': funding.get('indexPrice')
                }

        except Exception as e:
            print(f"Error fetching funding rate for {symbol}: {e}")
            return {
                'rate': 0,
                'next_funding_time': None,
                'mark_price': None,
                'index_price': None
            }

    def fetch_open_interest(self, symbol: str) -> Dict:
        """
        Fetch open interest data

        Returns:
            Dict with OI data
        """
        try:
            if self.exchange_name == 'binance':
                symbol_formatted = symbol.replace('/', '')

                oi_data = self.exchange.fapiPublicGetOpenInterest({
                    'symbol': symbol_formatted
                })

                return {
                    'open_interest': float(oi_data['openInterest']),
                    'timestamp': datetime.fromtimestamp(int(oi_data['time']) / 1000)
                }
            else:
                # Generic method (if supported)
                oi = self.exchange.fetch_open_interest(symbol)
                return {
                    'open_interest': oi.get('openInterest', 0),
                    'timestamp': datetime.now()
                }

        except Exception as e:
            print(f"Error fetching open interest for {symbol}: {e}")
            return {
                'open_interest': 0,
                'timestamp': datetime.now()
            }

    def fetch_liquidations(self, symbol: str, lookback_hours: int = 1) -> Dict:
        """
        Fetch recent liquidations

        Note: Not all exchanges provide this via CCXT
        This is a placeholder for custom implementation

        Returns:
            Dict with liquidation data
        """
        # This would need custom implementation per exchange
        # Some data providers like Coinglass provide this data
        return {
            'liquidations_long': 0,
            'liquidations_short': 0,
            'timestamp': datetime.now()
        }

    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        return list(self.exchange.markets.keys())

    def get_symbol_info(self, symbol: str) -> Dict:
        """Get detailed symbol information"""
        if symbol not in self.exchange.markets:
            raise ValueError(f"Symbol {symbol} not found")

        market = self.exchange.markets[symbol]
        return {
            'symbol': symbol,
            'base': market['base'],
            'quote': market['quote'],
            'type': market.get('type', 'spot'),  # spot, future, swap
            'active': market.get('active', True),
            'min_amount': market['limits']['amount']['min'] if 'limits' in market else None,
            'max_amount': market['limits']['amount']['max'] if 'limits' in market else None,
            'min_price': market['limits']['price']['min'] if 'limits' in market else None,
            'max_price': market['limits']['price']['max'] if 'limits' in market else None,
        }


class BinanceProvider(CCXTProvider):
    """Specialized Binance provider"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__('binance', config)


class CoinbaseProvider(CCXTProvider):
    """Specialized Coinbase provider"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__('coinbase', config)


class KrakenProvider(CCXTProvider):
    """Specialized Kraken provider"""

    def __init__(self, config: Optional[Dict] = None):
        super().__init__('kraken', config)
