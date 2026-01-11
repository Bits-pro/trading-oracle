"""
YFinance Provider for traditional markets
Gold (XAUUSD), stocks, indices, ETFs, bonds, etc.
"""
import yfinance as yf
import logging
import pandas as pd
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from .base_provider import BaseProvider


class YFinanceProvider(BaseProvider):
    """
    Provider for traditional market data using yfinance

    Supports:
    - Commodities (Gold, Silver, Copper, Oil)
    - Indices (DXY, VIX, SPX)
    - Stocks and ETFs (GLD, GDX, TIP, etc.)
    - Bonds and yields
    """

    # Symbol mapping: our symbols -> yfinance tickers
    SYMBOL_MAP = {
        # Gold
        'XAUUSD': 'GC=F',  # Gold futures
        'GLD': 'GLD',  # Gold ETF
        'GDX': 'GDX',  # Gold miners ETF

        # Silver
        'XAGUSD': 'SI=F',  # Silver futures

        # Copper
        'COPPER': 'HG=F',  # Copper futures

        # Oil
        'CRUDE': 'CL=F',  # Crude oil futures
        'BRENT': 'BZ=F',  # Brent oil futures

        # Indices
        'DXY': 'DX-Y.NYB',  # US Dollar Index
        'VIX': '^VIX',  # Volatility Index
        'SPX': '^GSPC',  # S&P 500
        'NDX': '^NDX',  # Nasdaq 100

        # Yields
        'TNX': '^TNX',  # 10-year Treasury yield
        'TIP': 'TIP',  # TIPS ETF (for real yields proxy)

        # Other
        'BTC': 'BTC-USD',  # Bitcoin (yfinance also has crypto)
        'ETH': 'ETH-USD',  # Ethereum
    }

    def __init__(self, config: Optional[Dict] = None):
        super().__init__(config)

    def _map_symbol(self, symbol: str) -> str:
        """Map our symbol format to yfinance ticker"""
        return self.SYMBOL_MAP.get(symbol, symbol)

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
            symbol: Symbol (e.g., 'XAUUSD', 'GLD', 'DXY')
            timeframe: Timeframe ('1h', '4h', '1d', '1w')
            start_time: Start datetime
            end_time: End datetime
            limit: Number of candles

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        ticker = self._map_symbol(symbol)
        yf_ticker = yf.Ticker(ticker)

        # Map timeframe to yfinance interval
        interval_map = {
            '1m': '1m',
            '5m': '5m',
            '15m': '15m',
            '30m': '30m',
            '1h': '1h',
            '4h': '1h',  # We'll resample
            '1d': '1d',
            '1w': '1wk',
            '1M': '1mo'
        }

        interval = interval_map.get(timeframe, '1d')

        # Calculate period if not specified
        if not start_time:
            # Calculate start based on limit and timeframe
            if timeframe == '1h':
                start_time = datetime.now() - timedelta(hours=limit)
            elif timeframe == '4h':
                start_time = datetime.now() - timedelta(hours=limit * 4)
            elif timeframe == '1d':
                start_time = datetime.now() - timedelta(days=limit)
            elif timeframe == '1w':
                start_time = datetime.now() - timedelta(weeks=limit)
            else:
                start_time = datetime.now() - timedelta(days=limit)

        if not end_time:
            end_time = datetime.now()

        # Fetch data
        df = yf_ticker.history(
            start=start_time,
            end=end_time,
            interval=interval
        )

        if df.empty:
            return pd.DataFrame(columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])

        # Resample if needed (e.g., 4h from 1h data)
        if timeframe == '4h' and interval == '1h':
            df = df.resample('4H').agg({
                'Open': 'first',
                'High': 'max',
                'Low': 'min',
                'Close': 'last',
                'Volume': 'sum'
            }).dropna()

        # Rename columns to match our format
        df = df.rename(columns={
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })

        # Reset index to get timestamp as column
        df = df.reset_index()
        df = df.rename(columns={'Date': 'timestamp', 'Datetime': 'timestamp'})

        # Select only needed columns
        df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]

        # Limit to requested number of candles
        if len(df) > limit:
            df = df.tail(limit)

        return df

    def fetch_ticker(self, symbol: str) -> Dict:
        """
        Fetch current ticker

        Returns:
            Dict with ticker data
        """
        ticker = self._map_symbol(symbol)
        yf_ticker = yf.Ticker(ticker)

        # Get current data
        info = yf_ticker.info
        hist = yf_ticker.history(period='1d')

        if hist.empty:
            return {
                'last_price': None,
                'bid': None,
                'ask': None,
                'volume_24h': None,
                'high_24h': None,
                'low_24h': None,
                'timestamp': datetime.now()
            }

        last_row = hist.iloc[-1]

        return {
            'last_price': last_row['Close'],
            'bid': info.get('bid'),
            'ask': info.get('ask'),
            'volume_24h': last_row['Volume'],
            'high_24h': last_row['High'],
            'low_24h': last_row['Low'],
            'timestamp': hist.index[-1].to_pydatetime()
        }

    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        return list(self.SYMBOL_MAP.keys())

    def get_symbol_info(self, symbol: str) -> Dict:
        """Get symbol information"""
        ticker = self._map_symbol(symbol)
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info

        return {
            'symbol': symbol,
            'yf_ticker': ticker,
            'name': info.get('longName', symbol),
            'type': info.get('quoteType', 'UNKNOWN'),
            'currency': info.get('currency', 'USD'),
            'exchange': info.get('exchange', 'UNKNOWN')
        }

    def fetch_gld_holdings(self) -> pd.DataFrame:
        """
        Fetch GLD ETF holdings data

        Note: This is a placeholder. Real implementation would need
        to scrape from GLD's official website or use a data provider
        """
        # Placeholder - would need actual implementation
        # GLD publishes holdings daily at:
        # https://www.spdrgoldshares.com/usa/

        return pd.DataFrame({
            'date': [datetime.now()],
            'holdings_tonnes': [0.0],  # Placeholder
            'holdings_oz': [0.0]
        })

    def fetch_cot_data(self, commodity: str = 'gold') -> pd.DataFrame:
        """
        Fetch Commitment of Traders (COT) data

        Note: This is a placeholder. Real implementation would need
        to fetch from CFTC website or use a data provider
        """
        # Placeholder - COT data published by CFTC weekly
        # https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm

        return pd.DataFrame({
            'date': [datetime.now()],
            'managed_money_long': [0],
            'managed_money_short': [0],
            'commercial_long': [0],
            'commercial_short': [0]
        })


class MacroDataProvider(YFinanceProvider):
    """
    Specialized provider for macro economic data
    """

    logger = logging.getLogger(__name__)

    def fetch_all_macro_indicators(self) -> Dict[str, pd.DataFrame]:
        """
        Fetch all macro indicators at once

        Returns:
            Dict of {indicator_name: DataFrame}
        """
        indicators = {}

        macro_symbols = ['DXY', 'VIX', 'TNX', 'TIP', 'SPX']

        for symbol in macro_symbols:
            try:
                df = self.fetch_ohlcv(
                    symbol=symbol,
                    timeframe='1d',
                    limit=100
                )
                if df.empty:
                    self.logger.warning("Macro indicator %s returned no data.", symbol)
                    continue
                indicators[symbol] = df
            except Exception as e:
                self.logger.warning("Error fetching macro indicator %s: %s", symbol, e)

        return indicators
