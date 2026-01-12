"""
Multi-Source Data Provider with Automatic Failover
Tries multiple data sources in order of confidence/reliability
"""
import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

from .yfinance_provider import YFinanceProvider
from .ccxt_provider import BinanceProvider


class SourceConfidence(Enum):
    """Data source confidence levels"""
    HIGH = 3      # Most reliable, primary source
    MEDIUM = 2    # Good alternative, reliable
    LOW = 1       # Last resort, may be less accurate


@dataclass
class DataSourceConfig:
    """Configuration for a data source"""
    name: str
    provider: any
    symbol_map: Dict[str, str]  # Our symbol -> provider symbol
    confidence: SourceConfidence
    enabled: bool = True
    max_retries: int = 2
    timeout_seconds: int = 10


class MultiSourceProvider:
    """
    Multi-source data provider with automatic failover

    Features:
    - Tries sources in order of confidence (HIGH -> MEDIUM -> LOW)
    - Automatic failover on errors or empty data
    - Configurable retry logic per source
    - Tracks which source was successful
    - Smart symbol mapping per provider
    """

    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._init_sources()

    def _init_sources(self):
        """Initialize data sources with priorities"""

        # Initialize providers
        self.binance = BinanceProvider()
        self.yfinance = YFinanceProvider()

        # Define source configurations for each asset type
        self.sources = {
            # Bitcoin sources (in priority order)
            'BTCUSDT': [
                DataSourceConfig(
                    name='Binance',
                    provider=self.binance,
                    symbol_map={'BTCUSDT': 'BTC/USDT'},
                    confidence=SourceConfidence.HIGH,
                    max_retries=2
                ),
                DataSourceConfig(
                    name='YFinance',
                    provider=self.yfinance,
                    symbol_map={'BTCUSDT': 'BTC-USD'},
                    confidence=SourceConfidence.MEDIUM,
                    max_retries=2
                ),
            ],

            # Gold sources (in priority order)
            'XAUUSD': [
                DataSourceConfig(
                    name='Binance PAXG',
                    provider=self.binance,
                    symbol_map={'XAUUSD': 'PAXG/USDT'},
                    confidence=SourceConfidence.HIGH,
                    max_retries=2
                ),
                DataSourceConfig(
                    name='YFinance Gold Spot',
                    provider=self.yfinance,
                    symbol_map={'XAUUSD': 'XAUUSD=X'},
                    confidence=SourceConfidence.MEDIUM,
                    max_retries=2
                ),
                DataSourceConfig(
                    name='YFinance Gold Futures',
                    provider=self.yfinance,
                    symbol_map={'XAUUSD': 'GC=F'},
                    confidence=SourceConfidence.LOW,
                    max_retries=1
                ),
            ],

            # Ethereum sources
            'ETHUSDT': [
                DataSourceConfig(
                    name='Binance',
                    provider=self.binance,
                    symbol_map={'ETHUSDT': 'ETH/USDT'},
                    confidence=SourceConfidence.HIGH,
                    max_retries=2
                ),
                DataSourceConfig(
                    name='YFinance',
                    provider=self.yfinance,
                    symbol_map={'ETHUSDT': 'ETH-USD'},
                    confidence=SourceConfidence.MEDIUM,
                    max_retries=2
                ),
            ],

            # Silver sources
            'XAGUSD': [
                DataSourceConfig(
                    name='YFinance Silver Spot',
                    provider=self.yfinance,
                    symbol_map={'XAGUSD': 'XAGUSD=X'},
                    confidence=SourceConfidence.HIGH,
                    max_retries=2
                ),
                DataSourceConfig(
                    name='YFinance Silver Futures',
                    provider=self.yfinance,
                    symbol_map={'XAGUSD': 'SI=F'},
                    confidence=SourceConfidence.MEDIUM,
                    max_retries=1
                ),
            ],
        }

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 500,
        verbose: bool = True
    ) -> Tuple[pd.DataFrame, str]:
        """
        Fetch OHLCV data with automatic multi-source failover

        Args:
            symbol: Symbol to fetch (e.g., 'BTCUSDT', 'XAUUSD')
            timeframe: Timeframe string
            start_time: Optional start datetime
            end_time: Optional end datetime
            limit: Number of candles
            verbose: Log source attempts

        Returns:
            Tuple of (DataFrame, source_name)

        Raises:
            Exception: If all sources fail
        """

        # Get source configs for this symbol
        source_configs = self.sources.get(symbol, [])

        if not source_configs:
            raise ValueError(f"No data sources configured for symbol: {symbol}")

        # Sort by confidence (HIGH -> MEDIUM -> LOW)
        source_configs = sorted(
            source_configs,
            key=lambda x: x.confidence.value,
            reverse=True
        )

        # Track attempts
        attempts = []
        last_error = None

        # Try each source in order
        for config in source_configs:
            if not config.enabled:
                continue

            # Map symbol to provider format
            provider_symbol = config.symbol_map.get(symbol)
            if not provider_symbol:
                continue

            # Try this source with retries
            for attempt in range(config.max_retries):
                try:
                    if verbose:
                        confidence_emoji = {
                            SourceConfidence.HIGH: '🟢',
                            SourceConfidence.MEDIUM: '🟡',
                            SourceConfidence.LOW: '🟠',
                        }.get(config.confidence, '⚪')

                        self.logger.info(
                            f"{confidence_emoji} Trying {config.name} for {symbol} "
                            f"(confidence: {config.confidence.name}, attempt: {attempt + 1}/{config.max_retries})"
                        )

                    # Fetch data
                    df = config.provider.fetch_ohlcv(
                        symbol=provider_symbol,
                        timeframe=timeframe,
                        start_time=start_time,
                        end_time=end_time,
                        limit=limit
                    )

                    # Check if data is valid
                    if not df.empty and len(df) > 0:
                        if verbose:
                            self.logger.info(
                                f"✅ Success! Fetched {len(df)} candles from {config.name} "
                                f"(confidence: {config.confidence.name})"
                            )

                        attempts.append({
                            'source': config.name,
                            'success': True,
                            'rows': len(df)
                        })

                        return df, config.name

                    else:
                        if verbose:
                            self.logger.warning(
                                f"⚠️ {config.name} returned empty data (attempt {attempt + 1})"
                            )
                        last_error = f"Empty data from {config.name}"

                except Exception as e:
                    last_error = str(e)
                    if verbose:
                        self.logger.warning(
                            f"❌ {config.name} error (attempt {attempt + 1}): {e}"
                        )

                    attempts.append({
                        'source': config.name,
                        'success': False,
                        'error': str(e)
                    })

                    # Don't retry on certain errors
                    if 'not found' in str(e).lower():
                        break

        # All sources failed
        error_summary = f"All data sources failed for {symbol}. Attempts: {len(attempts)}"
        if last_error:
            error_summary += f". Last error: {last_error}"

        self.logger.error(error_summary)
        raise Exception(error_summary)

    def fetch_ticker(
        self,
        symbol: str,
        verbose: bool = True
    ) -> Tuple[Dict, str]:
        """
        Fetch current ticker with automatic failover

        Returns:
            Tuple of (ticker_dict, source_name)
        """

        source_configs = self.sources.get(symbol, [])
        if not source_configs:
            raise ValueError(f"No data sources configured for symbol: {symbol}")

        source_configs = sorted(
            source_configs,
            key=lambda x: x.confidence.value,
            reverse=True
        )

        for config in source_configs:
            if not config.enabled:
                continue

            provider_symbol = config.symbol_map.get(symbol)
            if not provider_symbol:
                continue

            for attempt in range(config.max_retries):
                try:
                    ticker = config.provider.fetch_ticker(provider_symbol)

                    if ticker and ticker.get('last_price'):
                        if verbose:
                            self.logger.info(
                                f"✅ Ticker from {config.name}: ${ticker['last_price']}"
                            )
                        return ticker, config.name

                except Exception as e:
                    if verbose and attempt == config.max_retries - 1:
                        self.logger.warning(f"❌ {config.name} ticker error: {e}")

        raise Exception(f"All ticker sources failed for {symbol}")

    def add_source(
        self,
        symbol: str,
        name: str,
        provider: any,
        provider_symbol: str,
        confidence: SourceConfidence,
        enabled: bool = True
    ):
        """
        Dynamically add a new data source

        Example:
            provider.add_source(
                symbol='BTCUSDT',
                name='Coinbase',
                provider=coinbase_provider,
                provider_symbol='BTC-USD',
                confidence=SourceConfidence.MEDIUM
            )
        """
        if symbol not in self.sources:
            self.sources[symbol] = []

        config = DataSourceConfig(
            name=name,
            provider=provider,
            symbol_map={symbol: provider_symbol},
            confidence=confidence,
            enabled=enabled
        )

        self.sources[symbol].append(config)
        self.logger.info(f"Added {name} as source for {symbol} (confidence: {confidence.name})")

    def disable_source(self, symbol: str, source_name: str):
        """Temporarily disable a source"""
        if symbol in self.sources:
            for config in self.sources[symbol]:
                if config.name == source_name:
                    config.enabled = False
                    self.logger.info(f"Disabled {source_name} for {symbol}")
                    break

    def enable_source(self, symbol: str, source_name: str):
        """Re-enable a source"""
        if symbol in self.sources:
            for config in self.sources[symbol]:
                if config.name == source_name:
                    config.enabled = True
                    self.logger.info(f"Enabled {source_name} for {symbol}")
                    break

    def get_source_status(self, symbol: str) -> List[Dict]:
        """Get status of all sources for a symbol"""
        configs = self.sources.get(symbol, [])

        return [
            {
                'name': config.name,
                'confidence': config.confidence.name,
                'enabled': config.enabled,
                'provider_symbol': config.symbol_map.get(symbol, 'N/A')
            }
            for config in sorted(configs, key=lambda x: x.confidence.value, reverse=True)
        ]
