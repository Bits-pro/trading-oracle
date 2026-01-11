"""
Base provider interface
All data providers must implement this interface
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime


class BaseProvider(ABC):
    """Base class for all market data providers"""

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}

    @abstractmethod
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

        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        pass

    @abstractmethod
    def fetch_ticker(self, symbol: str) -> Dict:
        """
        Fetch current ticker data

        Returns:
            Dict with: last_price, bid, ask, volume_24h, etc.
        """
        pass

    @abstractmethod
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols"""
        pass

    def validate_symbol(self, symbol: str) -> bool:
        """Check if symbol is valid"""
        return symbol in self.get_available_symbols()
