"""
Data Quality Safeguards, Validation, and Cleaning Module.
Detects missing bars, duplicates, zero/invalid prices, unexpected session times,
and generates full diagnostic summaries.
"""

from typing import Dict, Any, Tuple
import datetime
import pandas as pd
import numpy as np
from src.timezone_utils import to_myt
from src.market_sessions import filter_tse_sessions, classify_session_segment


def validate_and_clean_dataset(
    df: pd.DataFrame,
    is_intraday: bool = True,
    remove_lunch: bool = True
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Validate, sanitize, and clean a raw financial DataFrame.
    
    Returns:
        cleaned_df: Cleaned and normalized DataFrame in MYT.
        quality_report: Diagnostic report detailing any anomalies found.
    """
    if df.empty:
        return df, {
            "initial_rows": 0,
            "final_rows": 0,
            "duplicate_timestamps": 0,
            "null_ohlc_rows": 0,
            "zero_or_negative_prices": 0,
            "off_session_bars": 0,
            "lunch_bars_removed": 0,
            "anomalies_detected": False,
        }

    df_work = to_myt(df.copy())
    initial_rows = len(df_work)
    
    # 1. Duplicate timestamps check
    dup_count = df_work.index.duplicated(keep="first").sum()
    if dup_count > 0:
        df_work = df_work[~df_work.index.duplicated(keep="first")]

    # 2. Sort chronologically
    df_work = df_work.sort_index()

    # 3. Missing / Null OHLC values
    ohlc_cols = [c for c in ["Open", "High", "Low", "Close"] if c in df_work.columns]
    null_rows = df_work[ohlc_cols].isnull().any(axis=1).sum()
    if null_rows > 0:
        df_work = df_work.dropna(subset=ohlc_cols)

    # 4. Zero or negative prices check
    invalid_price_mask = (df_work[ohlc_cols] <= 0).any(axis=1)
    invalid_price_count = invalid_price_mask.sum()
    if invalid_price_count > 0:
        df_work = df_work[~invalid_price_mask]

    # 5. Logical OHLC sanity check (High >= Low, High >= Open, High >= Close, Low <= Open, Low <= Close)
    illogical_bars = (
        (df_work["High"] < df_work["Low"]) |
        (df_work["High"] < df_work["Open"]) |
        (df_work["High"] < df_work["Close"]) |
        (df_work["Low"] > df_work["Open"]) |
        (df_work["Low"] > df_work["Close"])
    ).sum()

    # 6. Session boundary checks (for intraday datasets)
    off_session_count = 0
    lunch_count = 0
    if is_intraday:
        segments = [classify_session_segment(t) for t in df_work.index.time]
        off_session_count = segments.count("Off-Session")
        lunch_count = segments.count("Lunch")
        
        # Filter to valid TSE trading hours
        df_work = filter_tse_sessions(df_work, include_lunch=not remove_lunch)

    final_rows = len(df_work)
    
    quality_report = {
        "initial_rows": initial_rows,
        "final_rows": final_rows,
        "duplicate_timestamps": int(dup_count),
        "null_ohlc_rows": int(null_rows),
        "zero_or_negative_prices": int(invalid_price_count),
        "illogical_ohlc_bars": int(illogical_bars),
        "off_session_bars": int(off_session_count),
        "lunch_bars_removed": int(lunch_count) if remove_lunch else 0,
        "anomalies_detected": (
            dup_count > 0 or null_rows > 0 or invalid_price_count > 0 or illogical_bars > 0
        ),
    }

    return df_work, quality_report


def detect_intraday_gap_sessions(
    df: pd.DataFrame,
    expected_interval_minutes: int = 5
) -> pd.DataFrame:
    """
    Detect unexpectedly large gaps between consecutive bars during the active TSE sessions.
    (Excluding normal inter-day and lunch break gaps).
    """
    if df.empty or len(df) < 2:
        return pd.DataFrame()

    df_myt = to_myt(df)
    times = df_myt.index
    diffs = (times[1:] - times[:-1]).total_seconds() / 60.0
    
    gaps = []
    for i, diff in enumerate(diffs):
        t1 = times[i]
        t2 = times[i+1]
        
        # Same date check
        if t1.date() == t2.date():
            # Check if gap is within morning or within afternoon
            seg1 = classify_session_segment(t1.time())
            seg2 = classify_session_segment(t2.time())
            
            # If within same segment and gap > 1.5 * expected interval
            if seg1 == seg2 and seg1 in ["Morning", "Afternoon"]:
                if diff > (expected_interval_minutes * 1.5):
                    gaps.append({
                        "session_date": t1.date(),
                        "segment": seg1,
                        "from_time": t1.strftime("%H:%M"),
                        "to_time": t2.strftime("%H:%M"),
                        "gap_minutes": diff,
                    })

    return pd.DataFrame(gaps)
