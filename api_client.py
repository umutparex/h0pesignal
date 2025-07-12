# src/api_client.py

import requests
import pandas as pd
from typing import Optional, Dict, List, Any

class APIClient:
    """
    Binance API'si ile etkileşim kuran, spot ve vadeli işlem verilerini çeken sınıf.
    """
    def __init__(self, config: Dict):
        self.base_url = "https://api.binance.com/api/v3"
        self.futures_base_url = "https://fapi.binance.com/fapi/v1"
        self.futures_data_url = "https://fapi.binance.com/futures/data"
        self.config = config

    def get_klines(self, symbol: str, interval: str, limit: int = 200) -> Optional[pd.DataFrame]:
        """Belirtilen parite için mum verilerini çeker."""
        endpoint = f"{self.base_url}/klines"
        params = {"symbol": symbol, "interval": interval, "limit": limit}
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_volume', 'number_of_trades', 'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'])
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
            for col in df.columns:
                if col != 'timestamp':
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            return df
        except requests.exceptions.RequestException as e:
            # print(f"API Hatası (get_klines - {symbol}): {e}")
            return None

    def get_long_short_ratio(self, symbol: str, period: str = "5m") -> Optional[float]:
        """Global Long/Short Oranını çeker."""
        endpoint = f"{self.futures_data_url}/globalLongShortAccountRatio"
        params = {"symbol": symbol, "period": period, "limit": 1}
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data[0]['longShortRatio']) if data else None
        except (requests.exceptions.RequestException, KeyError, IndexError):
            return None

    def get_funding_rate(self, symbol: str) -> Optional[float]:
        """Anlık fonlama oranını çeker."""
        endpoint = f"{self.futures_base_url}/premiumIndex"
        params = {"symbol": symbol}
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data['lastFundingRate']) * 100 if data else None
        except (requests.exceptions.RequestException, KeyError):
            return None

    def get_open_interest(self, symbol: str) -> Optional[float]:
        """Açık faiz miktarını çeker."""
        endpoint = f"{self.futures_base_url}/openInterest"
        params = {"symbol": symbol}
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return float(data['openInterest']) if data else None
        except (requests.exceptions.RequestException, KeyError):
            return None

    def get_order_book_depth(self, symbol: str, limit: int = 10) -> Optional[Dict[str, List[Any]]]:
        """Order book verisini (Heatmap için) çeker."""
        endpoint = f"{self.futures_base_url}/depth"
        params = {"symbol": symbol, "limit": limit}
        try:
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            return {"bids": data.get("bids", []), "asks": data.get("asks", [])}
        except requests.exceptions.RequestException:
            return None
