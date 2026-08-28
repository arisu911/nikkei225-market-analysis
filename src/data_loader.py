"""
Data Provider Abstraction and Loader for Nikkei 225 Market Data.
Handles yfinance API integration, local Parquet/CSV caching, custom offline datasets,
and precise coverage/metadata reporting.
"""

from typing import Dict, Any, Optional, Tuple
from pathlib import Path
import datetime
import pandas as pd
import yfinance as yf

from config.settings import (
    PRIMARY_INDEX_SYMBOL,
    DEFAULT_VOLUME_SYMBOL,
    RAW_DATA_DIR,
    CACHE_DATA_DIR,
    PROCESSED_DATA_DIR,
    SOURCE_TIMEZONE,
    DISPLAY_TIMEZONE,
)
from src.timezone_utils import to_myt


class MarketDataProvider:
    """Base abstraction for financial market data providers."""
    
    def fetch_daily(self, symbol: str, period: str = "max") -> pd.DataFrame:
        raise NotImplementedError
        
    def fetch_intraday(self, symbol: str, interval: str = "5m", period: str = "60d") -> pd.DataFrame:
        raise NotImplementedError


class YFinanceDataProvider(MarketDataProvider):
    """Yahoo Finance API Data Provider with local disk caching."""
    
    def __init__(self, cache_dir: Path = CACHE_DATA_DIR):
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_filepath(self, symbol: str, interval: str, period: str) -> Path:
        clean_sym = symbol.replace("^", "").replace("=", "").replace(".", "_")
        return self.cache_dir / f"yf_{clean_sym}_{interval}_{period}.parquet"

    def fetch_daily(
        self,
        symbol: str = PRIMARY_INDEX_SYMBOL,
        period: str = "max",
        force_reload: bool = False
    ) -> pd.DataFrame:
        """
        Fetch daily OHLCV data. Caches locally to parquet for rapid subsequent loads.
        """
        cache_file = self._get_cache_filepath(symbol, "1d", period)
        
        # Check cache if not forcing reload and cache is not older than 12 hours
        if not force_reload and cache_file.exists():
            try:
                mtime = datetime.datetime.fromtimestamp(cache_file.stat().st_mtime)
                if datetime.datetime.now() - mtime < datetime.timedelta(hours=12):
                    df = pd.read_parquet(cache_file)
                    return to_myt(df)
            except Exception:
                pass # fallback to re-download

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1d")
        
        if df.empty:
            return pd.DataFrame()

        # Clean index timezone and standardize columns
        df = to_myt(df)
        # Keep standard OHLCV columns
        std_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[std_cols]
        
        # Save to cache
        try:
            df.to_parquet(cache_file)
        except Exception:
            pass

        return df

    def fetch_intraday(
        self,
        symbol: str = PRIMARY_INDEX_SYMBOL,
        interval: str = "5m",
        period: Optional[str] = None,
        force_reload: bool = False
    ) -> pd.DataFrame:
        """
        Fetch intraday OHLCV data from Yahoo Finance within provider limits:
        1m -> max 7d, 5m/15m/30m -> max 60d, 60m -> max 730d.
        """
        # Determine safest maximum period supported by yfinance
        if period is None:
            if interval == "1m":
                period = "7d"
            elif interval in ["5m", "10m", "15m", "30m"]:
                period = "60d"
            elif interval in ["60m", "1h"]:
                period = "730d"
            else:
                period = "60d"

        # Note: 10m is not directly supported by yfinance, fetch 5m and resample in caller if needed
        yf_interval = "5m" if interval == "10m" else interval
        cache_file = self._get_cache_filepath(symbol, yf_interval, period)

        if not force_reload and cache_file.exists():
            try:
                mtime = datetime.datetime.fromtimestamp(cache_file.stat().st_mtime)
                if datetime.datetime.now() - mtime < datetime.timedelta(hours=4):
                    df = pd.read_parquet(cache_file)
                    return to_myt(df)
            except Exception:
                pass

        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval=yf_interval)

        if df.empty:
            return pd.DataFrame()

        df = to_myt(df)
        std_cols = [c for c in ["Open", "High", "Low", "Close", "Volume"] if c in df.columns]
        df = df[std_cols]

        try:
            df.to_parquet(cache_file)
        except Exception:
            pass

        return df


def load_custom_offline_data(filename: str) -> Optional[pd.DataFrame]:
    """
    Load custom user-supplied offline datasets placed in `data/raw/`.
    Supports CSV and Parquet formats.
    """
    raw_path = RAW_DATA_DIR / filename
    if not raw_path.exists():
        return None

    try:
        if raw_path.suffix.lower() == ".parquet":
            df = pd.read_parquet(raw_path)
        else:
            df = pd.read_csv(raw_path, index_col=0, parse_dates=True)
            
        df = to_myt(df)
        return df
    except Exception as e:
        print(f"Error loading offline data {raw_path}: {e}")
        return None


def get_dataset_coverage_report(
    df: pd.DataFrame,
    symbol: str,
    instrument_name: str,
    interval_label: str
) -> Dict[str, Any]:
    """
    Generate a precise, transparent data coverage summary for the given dataset.
    Never fabricates coverage.
    """
    if df.empty:
        return {
            "symbol": symbol,
            "instrument_name": instrument_name,
            "interval": interval_label,
            "available": False,
            "start_date": "N/A",
            "end_date": "N/A",
            "total_bars": 0,
            "total_sessions": 0,
            "has_volume": False,
            "timezone": DISPLAY_TIMEZONE,
        }

    df_myt = to_myt(df)
    unique_dates = df_myt.index.date
    total_sessions = len(set(unique_dates))
    total_bars = len(df_myt)
    
    has_vol = "Volume" in df_myt.columns and (df_myt["Volume"] > 0).sum() > 0
    vol_non_zero_pct = (
        ((df_myt["Volume"] > 0).sum() / total_bars * 100) if "Volume" in df_myt.columns else 0.0
    )

    return {
        "symbol": symbol,
        "instrument_name": instrument_name,
        "interval": interval_label,
        "available": True,
        "start_date": str(df_myt.index[0]),
        "end_date": str(df_myt.index[-1]),
        "start_date_display": df_myt.index[0].strftime("%Y-%m-%d %H:%M MYT"),
        "end_date_display": df_myt.index[-1].strftime("%Y-%m-%d %H:%M MYT"),
        "total_bars": total_bars,
        "total_sessions": total_sessions,
        "has_volume": has_vol,
        "volume_coverage_pct": round(vol_non_zero_pct, 1),
        "timezone": f"{DISPLAY_TIMEZONE} (UTC+8)",
    }
