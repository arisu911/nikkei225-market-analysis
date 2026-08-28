"""
Core Quantitative Calculations for Nikkei 225 Market Behavior Analysis.
Purely descriptive and statistical calculations: returns, ranges, volatilities,
gaps, gap fills, opening ranges, MFE/MAE excursions, and relative volume.
"""

from typing import Dict, Any, List, Optional, Tuple
import datetime
import pandas as pd
import numpy as np
from src.timezone_utils import to_myt
from src.market_sessions import filter_tse_sessions, classify_session_segment, TSE_SESSIONS_MYT


def calculate_returns(df: pd.DataFrame, price_col: str = "Close") -> pd.DataFrame:
    """
    Calculate simple return, percentage return, absolute return, and direction flags.
    """
    if df.empty or price_col not in df.columns:
        return df

    res = df.copy()
    res["Return"] = res[price_col].pct_change()
    res["Return_Pct"] = res["Return"] * 100.0
    res["Abs_Return_Pct"] = res["Return_Pct"].abs()
    res["Is_Positive"] = res["Return_Pct"] > 0
    res["Is_Negative"] = res["Return_Pct"] < 0
    return res


def calculate_bar_hl_range(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate High-Low range, Range %, MFE, MFE %, MAE, and MAE % for each bar or session.
    """
    if df.empty:
        return df
    res = df.copy()
    res["Range"] = res["High"] - res["Low"]
    res["Range_Pct"] = (res["Range"] / res["Open"]) * 100.0
    res["MFE"] = res["High"] - res["Open"]
    res["MFE_Pct"] = (res["MFE"] / res["Open"]) * 100.0
    res["MAE"] = res["Low"] - res["Open"]
    res["MAE_Pct"] = (res["MAE"] / res["Open"]) * 100.0
    return res


def calculate_daily_summary_from_intraday(
    df: pd.DataFrame,
    volume_df: Optional[pd.DataFrame] = None
) -> pd.DataFrame:
    """
    Construct complete daily sessions from intraday bars.
    Calculates Open (08:00), High, Low, Close (14:30), Full-day Range, Return, MFE, MAE.
    """
    if df.empty:
        return pd.DataFrame()

    cleaned = filter_tse_sessions(df, include_lunch=False)
    if cleaned.empty:
        return pd.DataFrame()

    cleaned = cleaned.copy()
    cleaned["Session_Date"] = cleaned.index.date
    
    daily_records = []
    
    # Pre-merge volume if provided
    vol_by_time = None
    if volume_df is not None and not volume_df.empty and "Volume" in volume_df.columns:
        vol_clean = filter_tse_sessions(volume_df, include_lunch=False).copy()
        vol_clean["Session_Date"] = vol_clean.index.date
        vol_by_time = vol_clean.groupby("Session_Date")["Volume"].sum()

    for sess_date, group in cleaned.groupby("Session_Date"):
        if group.empty:
            continue
            
        group_sorted = group.sort_index()
        sess_open = group_sorted["Open"].iloc[0]
        sess_high = group_sorted["High"].max()
        sess_low = group_sorted["Low"].min()
        sess_close = group_sorted["Close"].iloc[-1]
        
        sess_return_pct = ((sess_close - sess_open) / sess_open) * 100.0
        sess_range = sess_high - sess_low
        sess_range_pct = (sess_range / sess_open) * 100.0
        
        # MFE: Maximum upward excursion from open
        mfe = sess_high - sess_open
        mfe_pct = (mfe / sess_open) * 100.0
        
        # MAE: Maximum downward excursion from open (expressed as negative %)
        mae = sess_low - sess_open
        mae_pct = (mae / sess_open) * 100.0
        
        # Volume
        sess_vol = np.nan
        if vol_by_time is not None and sess_date in vol_by_time.index:
            sess_vol = vol_by_time.loc[sess_date]
        elif "Volume" in group_sorted.columns:
            sess_vol = group_sorted["Volume"].sum()

        daily_records.append({
            "Date": pd.Timestamp(sess_date),
            "Open": sess_open,
            "High": sess_high,
            "Low": sess_low,
            "Close": sess_close,
            "Return_Pct": sess_return_pct,
            "Abs_Return_Pct": abs(sess_return_pct),
            "Range": sess_range,
            "Range_Pct": sess_range_pct,
            "MFE": mfe,
            "MFE_Pct": mfe_pct,
            "MAE": mae,
            "MAE_Pct": mae_pct,
            "Volume": sess_vol,
            "Bar_Count": len(group_sorted),
            "DayOfWeek": pd.Timestamp(sess_date).day_name(),
        })

    daily_df = pd.DataFrame(daily_records)
    if not daily_df.empty:
        daily_df = daily_df.set_index("Date").sort_index()
        # Bar to bar close-to-close return
        daily_df["Close_to_Close_Return_Pct"] = daily_df["Close"].pct_change() * 100.0
    return daily_df


def calculate_opening_gaps(daily_df: pd.DataFrame, intraday_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """
    Calculate opening gap metrics:
    - Previous Close to Current Open (08:00 MYT)
    - Gap %, Absolute Gap %
    - Positive Gap / Negative Gap
    - Gap Fill detection and time-to-fill (if intraday data available)
    """
    if daily_df.empty or len(daily_df) < 2:
        return pd.DataFrame()

    df = daily_df.copy().sort_index()
    df["Prev_Close"] = df["Close"].shift(1)
    df = df.dropna(subset=["Prev_Close"]).copy()

    df["Gap"] = df["Open"] - df["Prev_Close"]
    df["Gap_Pct"] = (df["Gap"] / df["Prev_Close"]) * 100.0
    df["Abs_Gap_Pct"] = df["Gap_Pct"].abs()
    df["Is_Gap_Up"] = df["Gap_Pct"] > 0
    df["Is_Gap_Down"] = df["Gap_Pct"] < 0
    
    # Gap fill logic:
    # Gap Up: filled if Day Low <= Prev Close
    # Gap Down: filled if Day High >= Prev Close
    gap_filled = []
    fill_time_minutes = []
    
    # Pre-clean intraday data in MYT if provided
    intra_myt = None
    if intraday_df is not None and not intraday_df.empty:
        intra_myt = to_myt(intraday_df).copy().sort_index()

    for dt, row in df.iterrows():
        prev_c = row["Prev_Close"]
        is_up = row["Is_Gap_Up"]
        is_down = row["Is_Gap_Down"]
        
        filled = False
        t_fill = np.nan
        
        if is_up:
            filled = row["Low"] <= prev_c
        elif is_down:
            filled = row["High"] >= prev_c
        else: # Gap is 0
            filled = True
            t_fill = 0

        # If intraday data is available for this session, find the exact minute of fill
        if filled and intra_myt is not None:
            sess_bars = intra_myt[intra_myt.index.date == dt.date()]
            if not sess_bars.empty:
                for bar_time, bar_row in sess_bars.iterrows():
                    bar_time_myt = to_myt(bar_time)
                    if (is_up and bar_row["Low"] <= prev_c) or (is_down and bar_row["High"] >= prev_c):
                        open_dt = bar_time_myt.replace(hour=8, minute=0, second=0, microsecond=0)
                        elapsed_min = (bar_time_myt - open_dt).total_seconds() / 60.0
                        t_fill = int(max(0, round(elapsed_min)))
                        break

        gap_filled.append(filled)
        fill_time_minutes.append(t_fill)

    df["Gap_Filled"] = gap_filled
    df["Time_To_Fill_Min"] = fill_time_minutes
    return df


def calculate_opening_ranges(
    intraday_df: pd.DataFrame,
    windows_minutes: List[int] = [5, 15, 30, 60]
) -> Dict[int, pd.DataFrame]:
    """
    Calculate opening ranges for 5, 15, 30, and 60 minutes after 08:00 MYT.
    Includes Opening High, Low, Range, Range %, Return %, and Ratio vs Full-day Range.
    """
    if intraday_df.empty:
        return {}

    cleaned = filter_tse_sessions(intraday_df, include_lunch=False)
    if cleaned.empty:
        return {}

    daily_sessions = calculate_daily_summary_from_intraday(cleaned)
    cleaned = cleaned.copy()
    cleaned["Session_Date"] = cleaned.index.date

    results = {}
    for win_min in windows_minutes:
        records = []
        end_h = 8 + (win_min // 60)
        end_m = win_min % 60
        t_end = datetime.time(end_h, end_m)
        t_start = datetime.time(8, 0)

        for sess_date, group in cleaned.groupby("Session_Date"):
            group_sorted = group.sort_index()
            # Filter bars within [08:00, t_end]
            times = group_sorted.index.time
            win_bars = group_sorted[(times >= t_start) & (times <= t_end)]
            
            if win_bars.empty:
                continue

            or_open = win_bars["Open"].iloc[0]
            or_high = win_bars["High"].max()
            or_low = win_bars["Low"].min()
            or_close = win_bars["Close"].iloc[-1]
            or_range = or_high - or_low
            or_range_pct = (or_range / or_open) * 100.0
            or_return_pct = ((or_close - or_open) / or_open) * 100.0

            # Full day comparison
            full_range = np.nan
            ratio_to_full = np.nan
            if not daily_sessions.empty and pd.Timestamp(sess_date) in daily_sessions.index:
                full_range = daily_sessions.loc[pd.Timestamp(sess_date), "Range"]
                if full_range > 0:
                    ratio_to_full = (or_range / full_range) * 100.0

            records.append({
                "Date": pd.Timestamp(sess_date),
                "OR_Open": or_open,
                "OR_High": or_high,
                "OR_Low": or_low,
                "OR_Close": or_close,
                "OR_Range": or_range,
                "OR_Range_Pct": or_range_pct,
                "OR_Return_Pct": or_return_pct,
                "Abs_OR_Return_Pct": abs(or_return_pct),
                "Full_Day_Range": full_range,
                "OR_Ratio_Pct": ratio_to_full,
                "DayOfWeek": pd.Timestamp(sess_date).day_name(),
            })

        df_win = pd.DataFrame(records)
        if not df_win.empty:
            df_win = df_win.set_index("Date").sort_index()
        results[win_min] = df_win

    return results


def calculate_morning_vs_afternoon(
    intraday_df: pd.DataFrame,
    volume_df: Optional[pd.DataFrame] = None
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Compare Morning Session (08:00 - 10:30 MYT) vs Afternoon Session (11:30 - 14:30 MYT).
    Returns: (morning_daily_df, afternoon_daily_df).
    """
    if intraday_df.empty:
        return pd.DataFrame(), pd.DataFrame()

    cleaned = to_myt(intraday_df).copy()
    cleaned["Session_Date"] = cleaned.index.date
    times = cleaned.index.time

    m_open = TSE_SESSIONS_MYT["morning_open"]
    m_close = TSE_SESSIONS_MYT["morning_close"]
    a_open = TSE_SESSIONS_MYT["afternoon_open"]
    a_close = TSE_SESSIONS_MYT["afternoon_close"]

    morning_bars = cleaned[(times >= m_open) & (times <= m_close)]
    afternoon_bars = cleaned[(times >= a_open) & (times <= a_close)]

    def _summarize_segment(segment_df: pd.DataFrame, seg_name: str) -> pd.DataFrame:
        records = []
        for sess_date, group in segment_df.groupby("Session_Date"):
            if group.empty:
                continue
            group_sorted = group.sort_index()
            o = group_sorted["Open"].iloc[0]
            h = group_sorted["High"].max()
            l = group_sorted["Low"].min()
            c = group_sorted["Close"].iloc[-1]
            ret_pct = ((c - o) / o) * 100.0
            rng = h - l
            rng_pct = (rng / o) * 100.0
            
            # Volatility: standard deviation of bar returns within session
            bar_rets = group_sorted["Close"].pct_change().dropna() * 100.0
            vol = bar_rets.std() if len(bar_rets) > 1 else np.nan

            vol_val = group_sorted["Volume"].sum() if "Volume" in group_sorted.columns else np.nan

            records.append({
                "Date": pd.Timestamp(sess_date),
                "Segment": seg_name,
                "Open": o,
                "High": h,
                "Low": l,
                "Close": c,
                "Return_Pct": ret_pct,
                "Abs_Return_Pct": abs(ret_pct),
                "Range": rng,
                "Range_Pct": rng_pct,
                "Intraday_Volatility": vol,
                "Volume": vol_val,
                "DayOfWeek": pd.Timestamp(sess_date).day_name(),
            })
        df_seg = pd.DataFrame(records)
        if not df_seg.empty:
            df_seg = df_seg.set_index("Date").sort_index()
        return df_seg

    m_df = _summarize_segment(morning_bars, "Morning")
    a_df = _summarize_segment(afternoon_bars, "Afternoon")
    return m_df, a_df


def calculate_relative_volume_intraday(
    df: pd.DataFrame,
    time_slot_col: str = "Time_Slot"
) -> pd.DataFrame:
    """
    Calculate Relative Volume (RVOL) = Volume / Average Volume for that specific time slot.
    """
    if df.empty or "Volume" not in df.columns:
        return df

    res = df.copy()
    if time_slot_col not in res.columns:
        res[time_slot_col] = [t.strftime("%H:%M") for t in res.index.time]

    mean_vol_by_slot = res.groupby(time_slot_col)["Volume"].transform("mean")
    # Avoid zero division
    res["RVOL"] = np.where(mean_vol_by_slot > 0, res["Volume"] / mean_vol_by_slot, 1.0)
    return res


def calculate_rolling_volatility(
    daily_df: pd.DataFrame,
    windows: List[int] = [20, 60, 120]
) -> pd.DataFrame:
    """
    Calculate rolling historical volatility (standard deviation of returns) for given session windows.
    Annualized using sqrt(250) trading sessions per year.
    """
    if daily_df.empty or "Close" not in daily_df.columns:
        return pd.DataFrame()

    res = daily_df.copy().sort_index()
    if "Close_to_Close_Return_Pct" not in res.columns:
        res["Close_to_Close_Return_Pct"] = res["Close"].pct_change() * 100.0

    for w in windows:
        col_name = f"Vol_{w}d"
        col_ann = f"Vol_Annual_{w}d"
        res[col_name] = res["Close_to_Close_Return_Pct"].rolling(window=w).std()
        res[col_ann] = res[col_name] * np.sqrt(250)

    return res
