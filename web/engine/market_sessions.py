"""
TSE Market Session Handling, Classification, and Filtering in MYT (UTC+8).
Ensures accurate isolation of Morning Session (08:00–10:30), Afternoon Session (11:30–14:30),
and strict exclusion of the Lunch Break (10:30–11:30) from continuous session statistics.
"""

from typing import Optional, List, Tuple
import datetime
import pandas as pd
from config.settings import TSE_SESSIONS_MYT
from engine.timezone_utils import to_myt


def classify_session_segment(dt: datetime.time) -> str:
    """
    Classify a time of day into its respective TSE session segment in MYT.
    Returns: 'Morning', 'Lunch', 'Afternoon', or 'Off-Session'.
    """
    t = dt if isinstance(dt, datetime.time) else dt.time()
    
    m_open = TSE_SESSIONS_MYT["morning_open"]
    m_close = TSE_SESSIONS_MYT["morning_close"]
    l_end = TSE_SESSIONS_MYT["lunch_end"]
    a_close = TSE_SESSIONS_MYT["afternoon_close"]

    if m_open <= t <= m_close:
        return "Morning"
    elif m_close < t < l_end:
        return "Lunch"
    elif l_end <= t <= a_close:
        return "Afternoon"
    else:
        return "Off-Session"


def filter_tse_sessions(
    df: pd.DataFrame,
    include_lunch: bool = False,
    include_off_session: bool = False
) -> pd.DataFrame:
    """
    Filter DataFrame to valid TSE trading hours in MYT.
    
    Parameters:
        df: DataFrame with DatetimeIndex (or converted to MYT).
        include_lunch: If True, retains bars during the 10:30-11:30 MYT lunch break. Default False.
        include_off_session: If True, retains pre-market/after-market bars. Default False.
    """
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return df

    df_myt = to_myt(df)
    times = df_myt.index.time
    
    m_open = TSE_SESSIONS_MYT["morning_open"]
    m_close = TSE_SESSIONS_MYT["morning_close"]
    a_open = TSE_SESSIONS_MYT["afternoon_open"]
    a_close = TSE_SESSIONS_MYT["afternoon_close"]

    morning_mask = (times >= m_open) & (times <= m_close)
    afternoon_mask = (times >= a_open) & (times <= a_close)
    lunch_mask = (times > m_close) & (times < a_open)

    if include_off_session:
        return df_myt
    elif include_lunch:
        valid_mask = (times >= m_open) & (times <= a_close)
    else:
        valid_mask = morning_mask | afternoon_mask

    filtered = df_myt[valid_mask].copy()
    return filtered


def get_morning_session_bars(df: pd.DataFrame) -> pd.DataFrame:
    """Extract bars exclusively falling within the Morning Session (08:00 - 10:30 MYT)."""
    if df.empty:
        return df
    df_myt = to_myt(df)
    times = df_myt.index.time
    mask = (times >= TSE_SESSIONS_MYT["morning_open"]) & (times <= TSE_SESSIONS_MYT["morning_close"])
    return df_myt[mask].copy()


def get_afternoon_session_bars(df: pd.DataFrame) -> pd.DataFrame:
    """Extract bars exclusively falling within the Afternoon Session (11:30 - 14:30 MYT)."""
    if df.empty:
        return df
    df_myt = to_myt(df)
    times = df_myt.index.time
    mask = (times >= TSE_SESSIONS_MYT["afternoon_open"]) & (times <= TSE_SESSIONS_MYT["afternoon_close"])
    return df_myt[mask].copy()


def get_opening_window_bars(df: pd.DataFrame, minutes: int = 30) -> pd.DataFrame:
    """
    Extract bars for the opening window (08:00 MYT to 08:00 + minutes).
    Supported windows typically: 5, 15, 30, 60 minutes.
    """
    if df.empty:
        return df
    df_myt = to_myt(df)
    times = df_myt.index.time
    
    start_time = datetime.time(8, 0)
    # Calculate end time based on minutes
    end_hour = 8 + (minutes // 60)
    end_minute = minutes % 60
    end_time = datetime.time(end_hour, end_minute)
    
    mask = (times >= start_time) & (times <= end_time)
    return df_myt[mask].copy()


def get_custom_window_bars(
    df: pd.DataFrame,
    start_time_str: str,
    end_time_str: str
) -> pd.DataFrame:
    """
    Filter DataFrame for a specific intraday time window given strings like '08:00' and '08:30'.
    """
    if df.empty:
        return df
    df_myt = to_myt(df)
    
    h_s, m_s = map(int, start_time_str.split(":"))
    h_e, m_e = map(int, end_time_str.split(":"))
    
    t_start = datetime.time(h_s, m_s)
    t_end = datetime.time(h_e, m_e)
    
    times = df_myt.index.time
    mask = (times >= t_start) & (times <= t_end)
    return df_myt[mask].copy()


def resample_ohlcv_intraday(df: pd.DataFrame, target_rule: str = "5min") -> pd.DataFrame:
    """
    Resample high-resolution intraday data to a target interval (e.g., '5min', '10min', '15min', '30min', '60min').
    Performs grouping by session date and session segment to prevent lunch break / inter-day bleeding.
    """
    if df.empty or not isinstance(df.index, pd.DatetimeIndex):
        return df

    # Filter to valid TSE sessions without lunch
    cleaned = filter_tse_sessions(df, include_lunch=False)
    if cleaned.empty:
        return cleaned

    # Group by date and session segment (Morning / Afternoon)
    cleaned = cleaned.copy()
    cleaned["_date"] = cleaned.index.date
    cleaned["_segment"] = [classify_session_segment(t) for t in cleaned.index.time]

    resampled_pieces = []
    for (sess_date, segment), group in cleaned.groupby(["_date", "_segment"]):
        if group.empty:
            continue
        # Standard OHLCV resample
        agg_dict = {
            "Open": "first",
            "High": "max",
            "Low": "min",
            "Close": "last",
        }
        if "Volume" in group.columns:
            agg_dict["Volume"] = "sum"

        resampled_group = group.resample(target_rule, closed="left", label="left").agg(agg_dict)
        resampled_group = resampled_group.dropna(subset=["Open", "Close"])
        resampled_pieces.append(resampled_group)

    if not resampled_pieces:
        return pd.DataFrame(columns=df.columns)

    result = pd.concat(resampled_pieces).sort_index()
    # Ensure timezone info is preserved
    if df.index.tz is not None and result.index.tz is None:
        result.index = result.index.tz_localize(df.index.tz)
    return result
