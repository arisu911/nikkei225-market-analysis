"""
Statistical Aggregations and Distribution Analysis for Nikkei 225 Behavior.
Provides comprehensive descriptive stats, weekday breakdowns, time-of-day profiles,
historical probability frequencies, and monthly/yearly summaries.
"""

from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
from scipy import stats
from config.settings import WEEKDAYS, PERCENTILES, DEFAULT_PROBABILITY_THRESHOLDS


def compute_distribution_metrics(
    series: pd.Series,
    percentiles: List[int] = PERCENTILES,
    label: str = "Metric"
) -> Dict[str, Any]:
    """
    Compute comprehensive descriptive distribution metrics for any numerical series.
    Returns: Dict with n, mean, median, std, min, max, skew, kurtosis, and custom percentiles.
    """
    clean_s = series.dropna()
    n = len(clean_s)
    if n == 0:
        return {
            "Metric": label,
            "Count (n)": 0,
            "Mean": np.nan,
            "Median": np.nan,
            "Std Dev": np.nan,
            "Min": np.nan,
            "Max": np.nan,
            "Skewness": np.nan,
            "Kurtosis": np.nan,
            **{f"P{p}": np.nan for p in percentiles},
        }

    pct_dict = {f"P{p}": float(np.percentile(clean_s, p)) for p in percentiles}
    
    skew_val = float(stats.skew(clean_s)) if n >= 3 else np.nan
    kurt_val = float(stats.kurtosis(clean_s)) if n >= 4 else np.nan

    return {
        "Metric": label,
        "Count (n)": int(n),
        "Mean": float(clean_s.mean()),
        "Median": float(clean_s.median()),
        "Std Dev": float(clean_s.std()),
        "Min": float(clean_s.min()),
        "Max": float(clean_s.max()),
        "Skewness": skew_val,
        "Kurtosis": kurt_val,
        **pct_dict,
    }


def compute_weekday_statistics(
    daily_df: pd.DataFrame,
    has_valid_volume: bool = True
) -> pd.DataFrame:
    """
    Compute complete Day-of-Week (Monday–Friday) behavior statistics.
    Includes Price, Volatility, Range, Volume, Positive/Negative % and sample size n.
    """
    if daily_df.empty:
        return pd.DataFrame()

    df = daily_df.copy()
    if "DayOfWeek" not in df.columns:
        df["DayOfWeek"] = df.index.day_name()

    records = []
    for day in WEEKDAYS:
        sub = df[df["DayOfWeek"] == day]
        n = len(sub)
        if n == 0:
            continue

        rets = sub["Return_Pct"].dropna()
        abs_rets = sub["Abs_Return_Pct"].dropna() if "Abs_Return_Pct" in sub.columns else rets.abs()
        ranges = sub["Range_Pct"].dropna() if "Range_Pct" in sub.columns else pd.Series(dtype=float)
        
        pos_pct = (rets > 0).mean() * 100.0 if len(rets) > 0 else np.nan
        neg_pct = (rets < 0).mean() * 100.0 if len(rets) > 0 else np.nan

        # Volatility & Percentiles
        vol_mean = rets.std()
        p25 = float(np.percentile(rets, 25)) if len(rets) >= 4 else np.nan
        p75 = float(np.percentile(rets, 75)) if len(rets) >= 4 else np.nan
        p90 = float(np.percentile(rets, 90)) if len(rets) >= 10 else np.nan
        p95 = float(np.percentile(rets, 95)) if len(rets) >= 20 else np.nan

        rec = {
            "Day of Week": day,
            "Sample Size (n)": n,
            "Avg Return (%)": float(rets.mean()),
            "Median Return (%)": float(rets.median()),
            "Avg Abs Move (%)": float(abs_rets.mean()),
            "Avg Range (%)": float(ranges.mean()) if not ranges.empty else np.nan,
            "Median Range (%)": float(ranges.median()) if not ranges.empty else np.nan,
            "Max Return (%)": float(rets.max()),
            "Min Return (%)": float(rets.min()),
            "Positive Days (%)": float(pos_pct),
            "Negative Days (%)": float(neg_pct),
            "Std Dev (%)": float(vol_mean),
            "25th Pct (%)": p25,
            "75th Pct (%)": p75,
            "90th Pct (%)": p90,
            "95th Pct (%)": p95,
        }

        if has_valid_volume and "Volume" in sub.columns:
            vols = sub["Volume"].dropna()
            vols_valid = vols[vols > 0]
            if not vols_valid.empty:
                rec["Avg Volume"] = float(vols_valid.mean())
                rec["Median Volume"] = float(vols_valid.median())
                # Relative volume against overall mean
                overall_vol_mean = df["Volume"][df["Volume"] > 0].mean()
                rec["Relative Volume"] = float(vols_valid.mean() / overall_vol_mean) if overall_vol_mean > 0 else np.nan
            else:
                rec["Avg Volume"] = np.nan
                rec["Median Volume"] = np.nan
                rec["Relative Volume"] = np.nan

        records.append(rec)

    return pd.DataFrame(records)


def compute_intraday_time_profile(
    intraday_df: pd.DataFrame,
    has_valid_volume: bool = True
) -> pd.DataFrame:
    """
    Compute descriptive time-of-day progression profile across all active intraday time slots.
    """
    if intraday_df.empty:
        return pd.DataFrame()

    df = intraday_df.copy().sort_index()
    df["Time_Slot"] = [t.strftime("%H:%M") for t in df.index.time]
    
    # Calculate bar returns
    df["Bar_Return_Pct"] = df["Close"].pct_change() * 100.0
    df["Bar_Range"] = df["High"] - df["Low"]
    df["Bar_Range_Pct"] = (df["Bar_Range"] / df["Open"]) * 100.0

    profile_records = []
    
    for slot, group in df.groupby("Time_Slot"):
        rets = group["Bar_Return_Pct"].dropna()
        n = len(rets)
        if n == 0:
            continue

        pos_pct = (rets > 0).mean() * 100.0
        neg_pct = (rets < 0).mean() * 100.0

        rec = {
            "Time (MYT)": slot,
            "Count (n)": n,
            "Avg Return (%)": float(rets.mean()),
            "Median Return (%)": float(rets.median()),
            "Avg Abs Return (%)": float(rets.abs().mean()),
            "Volatility (Std)": float(rets.std()) if n > 1 else np.nan,
            "Avg Range (%)": float(group["Bar_Range_Pct"].mean()),
            "Median Range (%)": float(group["Bar_Range_Pct"].median()),
            "Positive Bars (%)": float(pos_pct),
            "Negative Bars (%)": float(neg_pct),
        }

        if has_valid_volume and "Volume" in group.columns:
            vols = group["Volume"].dropna()
            vols_valid = vols[vols > 0]
            if not vols_valid.empty:
                rec["Avg Volume"] = float(vols_valid.mean())
                overall_slot_mean = df["Volume"][df["Volume"] > 0].mean()
                rec["Relative Volume"] = float(vols_valid.mean() / overall_slot_mean) if overall_slot_mean > 0 else 1.0
            else:
                rec["Avg Volume"] = np.nan
                rec["Relative Volume"] = np.nan

        profile_records.append(rec)

    res_df = pd.DataFrame(profile_records)
    if not res_df.empty:
        res_df = res_df.sort_values("Time (MYT)").reset_index(drop=True)
    return res_df


def compute_probability_frequencies(
    returns_pct: pd.Series,
    thresholds: List[float] = DEFAULT_PROBABILITY_THRESHOLDS
) -> pd.DataFrame:
    """
    Calculate descriptive historical occurrence frequencies (not predictive probabilities)
    for various return and absolute movement thresholds.
    """
    clean_rets = returns_pct.dropna()
    n = len(clean_rets)
    if n == 0:
        return pd.DataFrame()

    records = [
        {
            "Condition / Event": "Positive Return (Return > 0%)",
            "Historical Frequency (%)": float((clean_rets > 0).mean() * 100.0),
            "Occurrences (Count)": int((clean_rets > 0).sum()),
            "Sample Size (n)": n,
        },
        {
            "Condition / Event": "Negative Return (Return < 0%)",
            "Historical Frequency (%)": float((clean_rets < 0).mean() * 100.0),
            "Occurrences (Count)": int((clean_rets < 0).sum()),
            "Sample Size (n)": n,
        },
        {
            "Condition / Event": "Flat / Unchanged (Return == 0%)",
            "Historical Frequency (%)": float((clean_rets == 0).mean() * 100.0),
            "Occurrences (Count)": int((clean_rets == 0).sum()),
            "Sample Size (n)": n,
        },
    ]

    abs_rets = clean_rets.abs()
    for th in thresholds:
        cnt = int((abs_rets > th).sum())
        freq = float((abs_rets > th).mean() * 100.0)
        records.append({
            "Condition / Event": f"Absolute Move > {th:.2f}% (|Move| > {th:.2f}%)",
            "Historical Frequency (%)": freq,
            "Occurrences (Count)": cnt,
            "Sample Size (n)": n,
        })

    return pd.DataFrame(records)


def compute_monthly_statistics(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute descriptive monthly seasonality statistics (January -> December).
    """
    if daily_df.empty:
        return pd.DataFrame()

    df = daily_df.copy()
    df["Month"] = df.index.strftime("%B")
    df["Month_Num"] = df.index.month

    records = []
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]

    for m_num, m_name in enumerate(month_names, 1):
        sub = df[df["Month_Num"] == m_num]
        n = len(sub)
        if n == 0:
            continue

        rets = sub["Return_Pct"].dropna()
        ranges = sub["Range_Pct"].dropna() if "Range_Pct" in sub.columns else pd.Series(dtype=float)

        records.append({
            "Month": m_name,
            "Sessions (n)": n,
            "Avg Return (%)": float(rets.mean()),
            "Median Return (%)": float(rets.median()),
            "Volatility (Std %)": float(rets.std()) if n > 1 else np.nan,
            "Avg Range (%)": float(ranges.mean()) if not ranges.empty else np.nan,
            "Positive Days (%)": float((rets > 0).mean() * 100.0),
        })

    return pd.DataFrame(records)


def compute_yearly_statistics(daily_df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute annual performance, volatility, and maximum drawdown for context.
    """
    if daily_df.empty:
        return pd.DataFrame()

    df = daily_df.copy().sort_index()
    df["Year"] = df.index.year

    records = []
    for year, group in df.groupby("Year"):
        if group.empty:
            continue
        group_sorted = group.sort_index()
        n = len(group_sorted)
        
        # Annual price change from first open to last close
        start_price = group_sorted["Open"].iloc[0]
        end_price = group_sorted["Close"].iloc[-1]
        ann_return_pct = ((end_price - start_price) / start_price) * 100.0

        daily_rets = group_sorted["Return_Pct"].dropna()
        daily_vol = daily_rets.std() if n > 1 else np.nan

        # Max Drawdown within year
        cumulative_max = group_sorted["Close"].cummax()
        drawdowns = (group_sorted["Close"] - cumulative_max) / cumulative_max * 100.0
        max_dd = drawdowns.min()

        records.append({
            "Year": int(year),
            "Sessions (n)": n,
            "Annual Return (%)": float(ann_return_pct),
            "Avg Daily Return (%)": float(daily_rets.mean()),
            "Daily Volatility (%)": float(daily_vol),
            "Annualized Vol (%)": float(daily_vol * np.sqrt(250)) if daily_vol is not np.nan else np.nan,
            "Max Drawdown (%)": float(max_dd),
        })

    return pd.DataFrame(records).sort_values("Year", ascending=False).reset_index(drop=True)
