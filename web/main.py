import sys
from pathlib import Path
import json
import datetime
from typing import Optional, Dict, Any, List

# Ensure web root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from fastapi import FastAPI, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from config.settings import (
    PRIMARY_INDEX_SYMBOL,
    PRIMARY_INDEX_NAME,
    VOLUME_INSTRUMENTS,
    DEFAULT_VOLUME_SYMBOL,
    ANALYSIS_PERIODS,
    DEFAULT_PERIOD,
    SUPPORTED_RESOLUTIONS,
    DEFAULT_RESOLUTION,
    DISPLAY_TIMEZONE,
    WEEKDAYS,
    STANDARD_TIME_WINDOWS_MYT,
)
from engine.data_loader import YFinanceDataProvider, get_dataset_coverage_report
from engine.data_cleaner import validate_and_clean_dataset
from engine.timezone_utils import to_myt
from engine.market_sessions import filter_tse_sessions, resample_ohlcv_intraday, get_custom_window_bars
from engine.calculations import (
    calculate_returns,
    calculate_bar_hl_range,
    calculate_opening_gaps,
    calculate_opening_ranges,
    calculate_rolling_volatility,
    calculate_morning_vs_afternoon,
)
from engine.statistics import (
    compute_distribution_metrics,
    compute_monthly_statistics,
    compute_yearly_statistics,
    compute_weekday_statistics,
    compute_intraday_time_profile,
    compute_probability_frequencies,
)
from engine.charts import (
    build_cumulative_return_chart,
    plot_intraday_profile,
    plot_weekday_comparisons,
    plot_distribution_histogram,
    plot_box_plots,
    plot_weekday_time_heatmap,
    plot_morning_vs_afternoon_comparison,
    plot_mfe_mae_scatter,
    plot_rolling_volatility_chart,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_DANGER,
    _apply_dark_theme,
)

app = FastAPI(
    title="Nikkei 225 Market Behavior Research API",
    version="2.0.0",
    description="FastAPI Quantitative Analytics Engine for Nikkei 225 TSE Market Behavior"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

STATIC_DIR = BASE_DIR / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

@app.get("/", include_in_schema=False)
async def serve_index():
    return FileResponse(STATIC_DIR / "index.html")


def clean_for_json(val: Any) -> Any:
    """Sanitize nested data structures for JSON serialization."""
    if val is None:
        return None
    if isinstance(val, (np.floating, float)):
        if np.isnan(val) or np.isinf(val):
            return None
        return float(val)
    if isinstance(val, (np.integer, int)):
        return int(val)
    if isinstance(val, (np.bool_, bool)):
        return bool(val)
    if isinstance(val, (pd.Timestamp, datetime.datetime, datetime.date)):
        return str(val)
    if isinstance(val, dict):
        return {str(k): clean_for_json(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [clean_for_json(x) for x in val]
    if isinstance(val, pd.DataFrame):
        df_copy = val.copy()
        if not isinstance(df_copy.index, pd.RangeIndex):
            df_copy = df_copy.reset_index()
            if len(df_copy.columns) > 0 and df_copy.columns[0] in ["index", "level_0"]:
                df_copy.rename(columns={df_copy.columns[0]: "label"}, inplace=True)
        records = df_copy.replace({np.nan: None}).to_dict(orient="records")
        return clean_for_json(records)
    if isinstance(val, pd.Series):
        s_copy = val.copy()
        s_df = s_copy.reset_index()
        if len(s_df.columns) > 0 and s_df.columns[0] in ["index", "level_0"]:
            s_df.rename(columns={s_df.columns[0]: "label"}, inplace=True)
        records = s_df.replace({np.nan: None}).to_dict(orient="records")
        return clean_for_json(records)
    return str(val)


# In-Memory Cache for Loaded Market Data
_CACHE: Dict[str, Any] = {}

def get_market_data(
    period_key: str = "5Y",
    resolution: str = "15m",
    volume_symbol: str = "1321.T",
    force_reload: bool = False
) -> Dict[str, Any]:
    """
    Cached quantitative data pipeline loader.
    """
    cache_key = f"{period_key}_{resolution}_{volume_symbol}"
    if not force_reload and cache_key in _CACHE:
        return _CACHE[cache_key]

    provider = YFinanceDataProvider()

    # 1. Fetch Daily Data
    raw_daily = provider.fetch_daily(PRIMARY_INDEX_SYMBOL, period="max", force_reload=force_reload)
    clean_daily, daily_qual = validate_and_clean_dataset(raw_daily, is_intraday=False)

    # 2. Fetch Intraday Data
    raw_intra = provider.fetch_intraday(PRIMARY_INDEX_SYMBOL, interval=resolution, force_reload=force_reload)
    clean_intra, intra_qual = validate_and_clean_dataset(raw_intra, is_intraday=True, remove_lunch=True)

    if resolution == "10m" and not clean_intra.empty:
        clean_intra = resample_ohlcv_intraday(clean_intra, target_rule="10min")

    # 3. Fetch Volume Proxy Instrument
    raw_vol = pd.DataFrame()
    clean_vol = pd.DataFrame()
    has_valid_vol = False

    if volume_symbol and volume_symbol in VOLUME_INSTRUMENTS:
        raw_vol = provider.fetch_intraday(volume_symbol, interval=resolution, force_reload=force_reload)
        if not raw_vol.empty:
            clean_vol, _ = validate_and_clean_dataset(raw_vol, is_intraday=True, remove_lunch=True)
            has_valid_vol = "Volume" in clean_vol.columns and (clean_vol["Volume"] > 0).sum() > 0

    # 4. Period Filtering on Daily Data
    now = datetime.datetime.now(datetime.timezone.utc)
    if period_key in ANALYSIS_PERIODS and ANALYSIS_PERIODS[period_key]["days"] is not None:
        days = ANALYSIS_PERIODS[period_key]["days"]
        cutoff = clean_daily.index[-1] - pd.Timedelta(days=days) if not clean_daily.empty else now
        clean_daily = clean_daily[clean_daily.index >= cutoff]

    # Calculate returns, ranges, MFE/MAE for daily data
    if not clean_daily.empty:
        clean_daily = calculate_returns(clean_daily, "Close")
        clean_daily = calculate_bar_hl_range(clean_daily)
        clean_daily["DayOfWeek"] = clean_daily.index.day_name()
        clean_daily = clean_daily[clean_daily["DayOfWeek"].isin(WEEKDAYS)]

    daily_cov = get_dataset_coverage_report(clean_daily, PRIMARY_INDEX_SYMBOL, PRIMARY_INDEX_NAME, "1d")
    intra_cov = get_dataset_coverage_report(clean_intra, PRIMARY_INDEX_SYMBOL, PRIMARY_INDEX_NAME, resolution)

    bundle = {
        "daily_df": clean_daily,
        "intraday_df": clean_intra,
        "volume_df": clean_vol,
        "has_valid_volume": has_valid_vol,
        "daily_cov": daily_cov,
        "intra_cov": intra_cov,
        "daily_qual": daily_qual,
        "intra_qual": intra_qual,
    }
    _CACHE[cache_key] = bundle
    return bundle


def resolve_instrument(instrument: Optional[str]) -> str:
    if not instrument:
        return DEFAULT_VOLUME_SYMBOL
    if "1321" in instrument:
        return "1321.T"
    if "1329" in instrument:
        return "1329.T"
    if "NKD" in instrument:
        return "NKD=F"
    return DEFAULT_VOLUME_SYMBOL


# ==========================================
# REST API Endpoints
# ==========================================

@app.get("/api/metadata")
async def get_metadata(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    daily_df = data["daily_df"]
    if weekday != "All" and not daily_df.empty:
        daily_df = daily_df[daily_df["DayOfWeek"] == weekday]

    daily_cov = data["daily_cov"]
    intra_cov = data["intra_cov"]

    resp = {
        "symbol": PRIMARY_INDEX_SYMBOL,
        "instrument_name": PRIMARY_INDEX_NAME,
        "start_date": daily_cov.get("start_date_display", "N/A"),
        "end_date": daily_cov.get("end_date_display", "N/A"),
        "coverage_display": f"{daily_cov.get('start_date_display', 'N/A')} → {daily_cov.get('end_date_display', 'N/A')}",
        "timezone": f"MYT ({DISPLAY_TIMEZONE})",
        "active_timezone": "MYT (UTC+8)",
        "total_sessions": len(daily_df),
        "resolution": resolution,
        "total_intraday_bars": intra_cov.get("total_bars", 0),
        "volume_symbol": vol_sym,
        "volume_instrument_name": VOLUME_INSTRUMENTS.get(vol_sym, {}).get("name", vol_sym),
        "has_valid_volume": data["has_valid_volume"],
        "tse_session_hours": "08:00 - 10:30 & 11:30 - 14:30 MYT",
        "period": period,
        "weekday": weekday,
    }
    return JSONResponse(clean_for_json(resp))


@app.get("/api/overview/metrics")
async def get_overview_metrics(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    daily_df = data["daily_df"]
    if weekday != "All" and not daily_df.empty:
        daily_df = daily_df[daily_df["DayOfWeek"] == weekday]

    if daily_df.empty:
        return JSONResponse({
            "avg_daily_return": 0.0,
            "avg_daily_return_str": "0.00%",
            "median_return": 0.0,
            "median_return_str": "0.00%",
            "daily_volatility": 0.0,
            "daily_volatility_str": "0.00%",
            "annualized_volatility": 0.0,
            "annualized_volatility_str": "Ann: 0.0%",
            "avg_daily_range": 0.0,
            "avg_daily_range_str": "0.00%",
            "positive_days_pct": 0.0,
            "positive_days_pct_str": "0.0%",
            "negative_days_pct": 0.0,
            "negative_days_pct_str": "Neg: 0.0%",
            "total_sessions": 0,
            "total_sessions_str": "0",
            "active_period": f"Period: {period}",
        })

    rets = daily_df["Return_Pct"].dropna()
    ranges = daily_df["Range_Pct"].dropna()

    avg_ret = float(rets.mean()) if not rets.empty else 0.0
    med_ret = float(rets.median()) if not rets.empty else 0.0
    vol_daily = float(rets.std()) if len(rets) > 1 else 0.0
    vol_annual = float(vol_daily * np.sqrt(250)) if not np.isnan(vol_daily) else 0.0
    avg_range = float(ranges.mean()) if not ranges.empty else 0.0
    pos_pct = float((rets > 0).mean() * 100.0) if not rets.empty else 0.0
    neg_pct = float((rets < 0).mean() * 100.0) if not rets.empty else 0.0

    return JSONResponse(clean_for_json({
        "avg_daily_return": avg_ret,
        "avg_daily_return_str": f"{avg_ret:+.2f}%",
        "median_return": med_ret,
        "median_return_str": f"{med_ret:+.2f}%",
        "daily_volatility": vol_daily,
        "daily_volatility_str": f"{vol_daily:.2f}%",
        "annualized_volatility": vol_annual,
        "annualized_volatility_str": f"Ann: {vol_annual:.1f}%",
        "avg_daily_range": avg_range,
        "avg_daily_range_str": f"{avg_range:.2f}%",
        "positive_days_pct": pos_pct,
        "positive_days_pct_str": f"{pos_pct:.1f}%",
        "negative_days_pct": neg_pct,
        "negative_days_pct_str": f"Neg: {neg_pct:.1f}%",
        "total_sessions": len(daily_df),
        "total_sessions_str": f"{len(daily_df):,}",
        "active_period": f"Period: {period}",
    }))


@app.get("/api/overview/cumulative-chart")
async def get_cumulative_chart(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    daily_df = data["daily_df"]
    if weekday != "All" and not daily_df.empty:
        daily_df = daily_df[daily_df["DayOfWeek"] == weekday]

    fig = build_cumulative_return_chart(daily_df)
    return JSONResponse(json.loads(fig.to_json()))


@app.get("/api/overview/seasonality")
async def get_overview_seasonality(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    daily_df = data["daily_df"]
    if weekday != "All" and not daily_df.empty:
        daily_df = daily_df[daily_df["DayOfWeek"] == weekday]

    yr_df = compute_yearly_statistics(daily_df)
    mo_df = compute_monthly_statistics(daily_df)

    return JSONResponse({
        "yearly": clean_for_json(yr_df),
        "monthly": clean_for_json(mo_df),
    })


@app.get("/api/weekday/analysis")
async def get_weekday_analysis(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    daily_df = data["daily_df"].copy()
    intraday_df = data["intraday_df"].copy()
    has_valid_vol = data["has_valid_volume"]

    valid_weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    daily_df = daily_df[daily_df["DayOfWeek"].isin(valid_weekdays)]

    wk_stats = compute_weekday_statistics(daily_df, has_valid_volume=has_valid_vol)
    fig_comp = plot_weekday_comparisons(wk_stats)
    fig_box = plot_box_plots(
        daily_df,
        x_col="DayOfWeek",
        y_col="Return_Pct",
        title="Weekday Return Distributions & Outliers",
        ylabel="Session Return (%)"
    )
    fig_heatmap = plot_weekday_time_heatmap(
        intraday_df,
        value_col="Return_Pct",
        title="Mean Return (%) by Weekday & Time Slot (MYT)"
    )

    return JSONResponse({
        "comparisons_chart": json.loads(fig_comp.to_json()),
        "boxplots_chart": json.loads(fig_box.to_json()),
        "heatmap_chart": json.loads(fig_heatmap.to_json()),
    })


@app.get("/api/weekday/table")
async def get_weekday_table(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    daily_df = data["daily_df"].copy()
    has_valid_vol = data["has_valid_volume"]

    valid_weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    daily_df = daily_df[daily_df["DayOfWeek"].isin(valid_weekdays)]
    wk_stats = compute_weekday_statistics(daily_df, has_valid_volume=has_valid_vol)
    if not wk_stats.empty:
        if not isinstance(wk_stats.index, pd.RangeIndex):
            wk_stats = wk_stats.reset_index()
            wk_stats.rename(columns={wk_stats.columns[0]: "label"}, inplace=True)
        elif "Day of Week" in wk_stats.columns:
            wk_stats["label"] = wk_stats["Day of Week"]
        else:
            wk_stats = wk_stats.reset_index()
            wk_stats.rename(columns={wk_stats.columns[0]: "label"}, inplace=True)

        if len(wk_stats.columns) > 0 and wk_stats.columns[0] in ["index", "level_0"]:
            wk_stats.rename(columns={wk_stats.columns[0]: "label"}, inplace=True)

        wk_stats["Day of Week"] = wk_stats["label"]
        wk_stats["metric_label"] = wk_stats["label"]
        wk_stats["series"] = wk_stats["label"]
        cols = ["label"] + [c for c in wk_stats.columns if c not in ["label", "metric_label", "series"]] + ["metric_label", "series"]
        wk_stats = wk_stats[cols]

    return JSONResponse({
        "columns": list(wk_stats.columns),
        "data": clean_for_json(wk_stats),
    })


@app.get("/api/intraday/profile")
async def get_intraday_profile(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    intraday_df = data["intraday_df"].copy()
    has_valid_vol = data["has_valid_volume"]

    if weekday != "All" and not intraday_df.empty:
        intraday_df = intraday_df[intraday_df.index.day_name() == weekday]

    clean_intra = filter_tse_sessions(intraday_df, include_lunch=False)
    profile_df = compute_intraday_time_profile(clean_intra, has_valid_volume=has_valid_vol)
    fig_profile = plot_intraday_profile(profile_df)

    # Standard Intraday Time Windows
    bucket_records = []
    for start_t, end_t, label in STANDARD_TIME_WINDOWS_MYT:
        win_bars = get_custom_window_bars(clean_intra, start_t, end_t)
        if win_bars.empty:
            continue
        sess_returns = []
        sess_ranges = []
        for s_date, grp in win_bars.groupby(win_bars.index.date):
            grp_sorted = grp.sort_index()
            if grp_sorted.empty:
                continue
            o = grp_sorted["Open"].iloc[0]
            h = grp_sorted["High"].max()
            l = grp_sorted["Low"].min()
            c = grp_sorted["Close"].iloc[-1]
            ret_pct = ((c - o) / o) * 100.0
            rng_pct = ((h - l) / o) * 100.0
            sess_returns.append(ret_pct)
            sess_ranges.append(rng_pct)

        s_rets = pd.Series(sess_returns).dropna()
        s_rngs = pd.Series(sess_ranges).dropna()
        n = len(s_rets)
        if n == 0:
            continue

        pos_pct = (s_rets > 0).mean() * 100.0
        neg_pct = (s_rets < 0).mean() * 100.0

        bucket_records.append({
            "Time Window (MYT)": f"{start_t} – {end_t}",
            "Segment Description": label,
            "Sample Size (n)": n,
            "Avg Return (%)": float(s_rets.mean()),
            "Median Return (%)": float(s_rets.median()),
            "Avg Abs Move (%)": float(s_rets.abs().mean()),
            "Volatility (Std %)": float(s_rets.std()) if n > 1 else None,
            "Avg Range (%)": float(s_rngs.mean()),
            "Median Range (%)": float(s_rngs.median()),
            "Positive Sessions (%)": float(pos_pct),
            "Negative Sessions (%)": float(neg_pct),
        })

    return JSONResponse({
        "profile_chart": json.loads(fig_profile.to_json()),
        "time_windows": clean_for_json(bucket_records),
    })


@app.get("/api/gaps/analysis")
async def get_gaps_analysis(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    daily_df = data["daily_df"].copy()
    intraday_df = data["intraday_df"].copy()

    if weekday != "All":
        if not daily_df.empty:
            daily_df = daily_df[daily_df["DayOfWeek"] == weekday]
        if not intraday_df.empty:
            intraday_df = intraday_df[intraday_df.index.day_name() == weekday]

    gaps_df = calculate_opening_gaps(daily_df, intraday_df=intraday_df)

    metrics = {}
    fig_gap_dist = go.Figure()
    fig_fill = go.Figure()
    fig_ttf = None

    if not gaps_df.empty:
        gaps_pct = gaps_df["Gap_Pct"].dropna()
        abs_gaps = gaps_df["Abs_Gap_Pct"].dropna()
        avg_gap = float(gaps_pct.mean())
        med_gap = float(gaps_pct.median())
        avg_abs_gap = float(abs_gaps.mean())
        gap_up_pct = float((gaps_pct > 0).mean() * 100.0)
        gap_down_pct = float((gaps_pct < 0).mean() * 100.0)

        total_gapped = len(gaps_df[gaps_df["Gap_Pct"] != 0])
        filled_count = int(gaps_df["Gap_Filled"].sum())
        fill_rate_pct = float(filled_count / total_gapped * 100.0) if total_gapped > 0 else 0.0

        up_gaps = gaps_df[gaps_df["Is_Gap_Up"]]
        down_gaps = gaps_df[gaps_df["Is_Gap_Down"]]
        up_fill_rate = float(up_gaps["Gap_Filled"].mean() * 100.0) if not up_gaps.empty else 0.0
        down_fill_rate = float(down_gaps["Gap_Filled"].mean() * 100.0) if not down_gaps.empty else 0.0

        metrics = {
            "avg_gap": f"{avg_gap:+.2f}%",
            "median_gap": f"{med_gap:+.2f}%",
            "avg_abs_gap": f"{avg_abs_gap:.2f}%",
            "gap_up_pct": f"{gap_up_pct:.1f}%",
            "fill_rate_pct": f"{fill_rate_pct:.1f}%",
            "total_gaps": f"{len(gaps_df):,}",
            "up_fill_rate": f"{up_fill_rate:.1f}%",
            "down_fill_rate": f"{down_fill_rate:.1f}%",
        }

        fig_gap_dist = plot_distribution_histogram(
            gaps_pct,
            title="Opening Gap Percentage Distribution (% from Prev Close)",
            xlabel="Opening Gap (%)",
            bins=45
        )

        fig_fill.add_trace(
            go.Bar(
                x=["Overall Gaps", "Gap Ups Only", "Gap Downs Only"],
                y=[fill_rate_pct, up_fill_rate, down_fill_rate],
                marker_color=[COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER],
                text=[f"{fill_rate_pct:.1f}%", f"{up_fill_rate:.1f}%", f"{down_fill_rate:.1f}%"],
                textposition="auto",
            )
        )
        fig_fill.update_layout(
            yaxis_title="Historical Gap Fill Frequency (%)",
            yaxis_range=[0, 100],
            height=420,
        )
        _apply_dark_theme(fig_fill, "TSE Opening Gap Fill Frequency by Direction")

        fill_times = gaps_df["Time_To_Fill_Min"].dropna()
        if not fill_times.empty:
            fill_times_valid = fill_times[fill_times >= 0].astype(int)
            if not fill_times_valid.empty:
                fig_ttf = plot_distribution_histogram(
                    fill_times_valid,
                    title="Elapsed Minutes to Complete Gap Fill",
                    xlabel="Minutes Elapsed from 08:00 MYT Open",
                    bins=25,
                    show_zero_line=False,
                    non_negative=True,
                )

    # Opening Range Analysis (5m, 15m, 30m, 60m)
    or_summary_rows = []
    fig_or_ratio = None
    if not intraday_df.empty:
        or_dict = calculate_opening_ranges(intraday_df, windows_minutes=[5, 15, 30, 60])
        fig_or_ratio = go.Figure()
        for win_min, df_w in or_dict.items():
            if df_w.empty:
                continue
            rets_w = df_w["OR_Return_Pct"].dropna()
            ranges_w = df_w["OR_Range_Pct"].dropna()
            ratios_w = df_w["OR_Ratio_Pct"].dropna()
            n = len(df_w)

            or_summary_rows.append({
                "Opening Window": f"First {win_min} Minutes" if win_min < 60 else "First 60 Minutes",
                "Sample Size (n)": n,
                "Avg Return (%)": float(rets_w.mean()),
                "Median Return (%)": float(rets_w.median()),
                "Volatility (Std %)": float(rets_w.std()) if n > 1 else None,
                "Avg Range (%)": float(ranges_w.mean()),
                "Median Range (%)": float(ranges_w.median()),
                "Avg % of Full-Day Range": float(ratios_w.mean()),
                "Median % of Full-Day Range": float(ratios_w.median()),
                "Positive Window (%)": float((rets_w > 0).mean() * 100.0),
            })
            fig_or_ratio.add_trace(
                go.Box(
                    y=ratios_w,
                    name=f"{win_min}m Window",
                    boxmean=True,
                )
            )
        fig_or_ratio.update_layout(
            yaxis_title="Opening Range as % of Full-Day High-Low Range",
            height=420,
        )
        _apply_dark_theme(fig_or_ratio, "Opening Range vs Full-Day Range Expansion Ratio (%)")

    return JSONResponse({
        "metrics": metrics,
        "gap_distribution_chart": json.loads(fig_gap_dist.to_json()),
        "gap_fill_chart": json.loads(fig_fill.to_json()),
        "time_to_fill_chart": json.loads(fig_ttf.to_json()) if fig_ttf else None,
        "opening_ranges_table": clean_for_json(or_summary_rows),
        "opening_range_chart": json.loads(fig_or_ratio.to_json()) if fig_or_ratio else None,
    })


@app.get("/api/volatility/excursions")
async def get_volatility_excursions(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    daily_df = data["daily_df"].copy()
    intraday_df = data["intraday_df"].copy()
    volume_df = data["volume_df"].copy()

    if weekday != "All":
        if not daily_df.empty:
            daily_df = daily_df[daily_df["DayOfWeek"] == weekday]
        if not intraday_df.empty:
            intraday_df = intraday_df[intraday_df.index.day_name() == weekday]

    if "MFE_Pct" not in daily_df.columns or "MAE_Pct" not in daily_df.columns:
        daily_df = calculate_bar_hl_range(daily_df)

    # 1. Rolling Volatility
    rolling_df = calculate_rolling_volatility(daily_df, windows=[20, 60, 120])
    fig_rolling = plot_rolling_volatility_chart(rolling_df)

    # 2. Return & Range Quantiles
    rets = daily_df["Return_Pct"].dropna()
    ranges = daily_df["Range_Pct"].dropna()
    vol_dist = compute_distribution_metrics(rets, label="Daily Session Return (%)")
    range_dist = compute_distribution_metrics(ranges, label="Daily High-Low Range (%)")

    vol_quant_df = pd.DataFrame([vol_dist, range_dist])
    if not isinstance(vol_quant_df.index, pd.RangeIndex):
        vol_quant_df = vol_quant_df.reset_index()
        vol_quant_df.rename(columns={vol_quant_df.columns[0]: "label"}, inplace=True)
    elif "label" not in vol_quant_df.columns:
        if "Metric" in vol_quant_df.columns:
            vol_quant_df["label"] = vol_quant_df["Metric"]
        else:
            vol_quant_df = vol_quant_df.reset_index()
            vol_quant_df.rename(columns={vol_quant_df.columns[0]: "label"}, inplace=True)
    if len(vol_quant_df.columns) > 0 and vol_quant_df.columns[0] in ["index", "level_0"]:
        vol_quant_df.rename(columns={vol_quant_df.columns[0]: "label"}, inplace=True)
    vol_quant_df["metric_label"] = vol_quant_df["label"]
    vol_quant_df["series"] = vol_quant_df["label"]
    cols = ["label"] + [c for c in vol_quant_df.columns if c not in ["label", "metric_label", "series"]] + ["metric_label", "series"]
    vol_quant_df = vol_quant_df[cols]

    # 3. Morning vs Afternoon
    fig_m_vs_a = None
    m_vs_a_table = []
    if not intraday_df.empty:
        m_df, a_df = calculate_morning_vs_afternoon(intraday_df, volume_df)
        if not m_df.empty and not a_df.empty:
            fig_m_vs_a = plot_morning_vs_afternoon_comparison(m_df, a_df)
            m_rets = m_df["Return_Pct"].dropna()
            a_rets = a_df["Return_Pct"].dropna()
            m_rng = m_df["Range_Pct"].dropna()
            a_rng = a_df["Range_Pct"].dropna()
            m_vs_a_table = [
                {
                    "label": "Morning (08:00 – 10:30 MYT)",
                    "Session Segment": "Morning (08:00 – 10:30 MYT)",
                    "Duration": "2.5 Hours",
                    "Sessions (n)": len(m_rets),
                    "Avg Return (%)": float(m_rets.mean()),
                    "Median Return (%)": float(m_rets.median()),
                    "Volatility (Std %)": float(m_rets.std()),
                    "Avg Range (%)": float(m_rng.mean()),
                    "Median Range (%)": float(m_rng.median()),
                    "Positive Frequency (%)": float((m_rets > 0).mean() * 100.0),
                    "Negative Frequency (%)": float((m_rets < 0).mean() * 100.0),
                },
                {
                    "label": "Afternoon (11:30 – 14:30 MYT)",
                    "Session Segment": "Afternoon (11:30 – 14:30 MYT)",
                    "Duration": "3.0 Hours",
                    "Sessions (n)": len(a_rets),
                    "Avg Return (%)": float(a_rets.mean()),
                    "Median Return (%)": float(a_rets.median()),
                    "Volatility (Std %)": float(a_rets.std()),
                    "Avg Range (%)": float(a_rng.mean()),
                    "Median Range (%)": float(a_rng.median()),
                    "Positive Frequency (%)": float((a_rets > 0).mean() * 100.0),
                    "Negative Frequency (%)": float((a_rets < 0).mean() * 100.0),
                }
            ]

    # 4. MFE / MAE
    fig_mfe_mae = plot_mfe_mae_scatter(daily_df)
    mfe_s = daily_df["MFE_Pct"].dropna()
    mae_s = daily_df["MAE_Pct"].dropna()

    excursion_quantiles = []
    fig_mfe = None
    fig_mae = None
    mfe_mae_metrics = {}

    if not mfe_s.empty and not mae_s.empty:
        mfe_dist = compute_distribution_metrics(mfe_s, label="MFE (Max Upward % from Open)")
        mae_dist = compute_distribution_metrics(mae_s, label="MAE (Max Downward % from Open)")
        excursion_df = pd.DataFrame([mfe_dist, mae_dist])
        if not isinstance(excursion_df.index, pd.RangeIndex):
            excursion_df = excursion_df.reset_index()
            excursion_df.rename(columns={excursion_df.columns[0]: "label"}, inplace=True)
        elif "label" not in excursion_df.columns:
            if "Metric" in excursion_df.columns:
                excursion_df["label"] = excursion_df["Metric"]
            else:
                excursion_df = excursion_df.reset_index()
                excursion_df.rename(columns={excursion_df.columns[0]: "label"}, inplace=True)
        if len(excursion_df.columns) > 0 and excursion_df.columns[0] in ["index", "level_0"]:
            excursion_df.rename(columns={excursion_df.columns[0]: "label"}, inplace=True)
        excursion_df["metric_label"] = excursion_df["label"]
        excursion_df["series"] = excursion_df["label"]
        cols = ["label"] + [c for c in excursion_df.columns if c not in ["label", "metric_label", "series"]] + ["metric_label", "series"]
        excursion_quantiles = excursion_df[cols]

        fig_mfe = plot_distribution_histogram(mfe_s, "MFE Distribution (Max Upward % from Open)", "MFE (%)", bins=35, non_negative=True)
        fig_mae = plot_distribution_histogram(mae_s, "MAE Distribution (Max Downward % from Open)", "MAE (%)", bins=35)

        mfe_mae_metrics = {
            "avg_mfe": f"+{mfe_s.mean():.2f}%",
            "med_mfe": f"+{mfe_s.median():.2f}%",
            "avg_mae": f"{mae_s.mean():.2f}%",
            "med_mae": f"{mae_s.median():.2f}%",
        }

    return JSONResponse({
        "rolling_chart": json.loads(fig_rolling.to_json()),
        "volatility_quantiles": clean_for_json(vol_quant_df),
        "morning_vs_afternoon_chart": json.loads(fig_m_vs_a.to_json()) if fig_m_vs_a else None,
        "morning_vs_afternoon_table": clean_for_json(m_vs_a_table),
        "mfe_mae_chart": json.loads(fig_mfe_mae.to_json()),
        "mfe_mae_metrics": mfe_mae_metrics,
        "excursion_quantiles": clean_for_json(excursion_quantiles),
        "mfe_hist": json.loads(fig_mfe.to_json()) if fig_mfe else None,
        "mae_hist": json.loads(fig_mae.to_json()) if fig_mae else None,
    })


@app.get("/api/distributions/quantiles")
async def get_distributions_quantiles(
    period: str = Query("5Y"),
    resolution: str = Query("15m"),
    weekday: str = Query("All"),
    instrument: str = Query("1321.T"),
    force_reload: bool = Query(False)
):
    vol_sym = resolve_instrument(instrument)
    data = get_market_data(period, resolution, vol_sym, force_reload)
    daily_df = data["daily_df"].copy()
    if weekday != "All" and not daily_df.empty:
        daily_df = daily_df[daily_df["DayOfWeek"] == weekday]

    rets = daily_df["Return_Pct"].dropna()
    ranges = daily_df["Range_Pct"].dropna()
    abs_rets = rets.abs()

    m_ret = compute_distribution_metrics(rets, label="Session Return (%)")
    m_abs = compute_distribution_metrics(abs_rets, label="Absolute Move (%)")
    m_rng = compute_distribution_metrics(ranges, label="High-Low Range (%)")

    quant_df = pd.DataFrame([m_ret, m_abs, m_rng])
    if not isinstance(quant_df.index, pd.RangeIndex):
        quant_df = quant_df.reset_index()
        quant_df.rename(columns={quant_df.columns[0]: "label"}, inplace=True)
    elif "label" not in quant_df.columns:
        if "Metric" in quant_df.columns:
            quant_df["label"] = quant_df["Metric"]
        else:
            quant_df = quant_df.reset_index()
            quant_df.rename(columns={quant_df.columns[0]: "label"}, inplace=True)
    if len(quant_df.columns) > 0 and quant_df.columns[0] in ["index", "level_0"]:
        quant_df.rename(columns={quant_df.columns[0]: "label"}, inplace=True)
    quant_df["metric_label"] = quant_df["label"]
    quant_df["series"] = quant_df["label"]
    cols = ["label"] + [c for c in quant_df.columns if c not in ["label", "metric_label", "series"]] + ["metric_label", "series"]
    quant_df = quant_df[cols]

    thresholds = [0.25, 0.50, 0.75, 1.00, 1.50, 2.00]
    freq_df = compute_probability_frequencies(rets, thresholds=thresholds, ranges_pct=ranges)
    if not freq_df.empty:
        if not isinstance(freq_df.index, pd.RangeIndex):
            freq_df = freq_df.reset_index()
            freq_df.rename(columns={freq_df.columns[0]: "label"}, inplace=True)
        elif "label" not in freq_df.columns:
            if "Condition / Event" in freq_df.columns:
                freq_df["label"] = freq_df["Condition / Event"]
            elif "Move Category" in freq_df.columns:
                freq_df["label"] = freq_df["Move Category"]
            else:
                freq_df = freq_df.reset_index()
                freq_df.rename(columns={freq_df.columns[0]: "label"}, inplace=True)
        if len(freq_df.columns) > 0 and freq_df.columns[0] in ["index", "level_0"]:
            freq_df.rename(columns={freq_df.columns[0]: "label"}, inplace=True)
        freq_df["Move Category"] = freq_df["label"]
        freq_df["Condition / Event"] = freq_df["label"]
        freq_df["series"] = freq_df["label"]
        freq_df["metric_label"] = freq_df["label"]
        cols = ["label"] + [c for c in freq_df.columns if c not in ["label", "metric_label", "series", "Condition / Event", "Move Category"]] + ["Condition / Event", "Move Category", "metric_label", "series"]
        freq_df = freq_df[cols]

    fig_r = plot_distribution_histogram(
        rets,
        title="Nikkei 225 Session Return Distribution (%)",
        xlabel="Session Return (%)",
        bins=50,
    )
    fig_rng = plot_distribution_histogram(
        ranges,
        title="Nikkei 225 High-Low Range Distribution (%)",
        xlabel="Daily High-Low Range (%)",
        bins=50,
        show_zero_line=False,
    )

    return JSONResponse({
        "quantiles_table": clean_for_json(quant_df),
        "frequency_table": clean_for_json(freq_df),
        "return_histogram": json.loads(fig_r.to_json()),
        "range_histogram": json.loads(fig_rng.to_json()),
    })


@app.post("/api/refresh")
async def refresh_cache():
    """Force invalidate in-memory cache."""
    global _CACHE
    _CACHE.clear()
    return {"status": "success", "message": "Cache cleared successfully"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main.py:app", host="127.0.0.1", port=8000, reload=True)
