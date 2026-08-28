"""
Nikkei 225 Intraday Market Behavior Research Dashboard
Single-Page Application (SPA) with custom Sidebar Navigation.
All display timestamps are strictly presented in Malaysia Time (MYT, UTC+8).
"""

import sys
from pathlib import Path
import datetime

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import streamlit as st
import pandas as pd
import numpy as np

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
)
from src.data_loader import YFinanceDataProvider, get_dataset_coverage_report
from src.data_cleaner import validate_and_clean_dataset
from src.timezone_utils import to_myt
from src.market_sessions import filter_tse_sessions, resample_ohlcv_intraday
from src.calculations import calculate_daily_summary_from_intraday, calculate_returns, calculate_bar_hl_range

# Import Single-Page Application View Renderers
from src.views import (
    render_overview_page,
    render_weekday_page,
    render_intraday_page,
    render_opening_page,
    render_volatility_page,
    render_distributions_page,
)


# ==========================================
# Streamlit App Configuration & Safeguard Styling
# ==========================================
st.set_page_config(
    page_title="Nikkei 225 Market Behavior Research",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Hide Streamlit's default native sidebar navigation as a fallback safeguard
st.markdown('<style>[data-testid="stSidebarNav"] {display: none;}</style>', unsafe_allow_html=True)

# Custom CSS for modern quantitative theme
st.markdown("""
<style>
    /* Metric Cards */
    div[data-testid="stMetricValue"] {
        font-size: 1.55rem;
        font-weight: 700;
        color: #58a6ff;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 0.85rem;
        font-weight: 600;
        color: #8b949e;
    }
    /* Coverage Banner */
    .coverage-banner {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
        padding: 12px 18px;
        margin-bottom: 20px;
    }
    .badge {
        display: inline-block;
        padding: 2px 8px;
        font-size: 12px;
        font-weight: 600;
        border-radius: 12px;
        background-color: #238636;
        color: #ffffff;
        margin-right: 6px;
    }
    .badge-info {
        background-color: #1f6feb;
    }
</style>
""", unsafe_allow_html=True)


# ==========================================
# Cached Data Pipeline
# ==========================================
@st.cache_data(ttl=3600, show_spinner="Fetching & Processing Market Data...")
def load_all_market_data(
    period_key: str,
    resolution: str,
    volume_symbol: str,
    custom_start: str = None,
    custom_end: str = None,
    force_reload: bool = False
):
    """
    Unified cached data pipeline:
    1. Downloads/caches daily data for ^N225 across full multi-year period.
    2. Downloads/caches intraday data for ^N225 at requested resolution.
    3. Downloads/caches volume proxy instrument (e.g. 1321.T).
    4. Cleans, sanitizes, and normalizes all timestamps to MYT (UTC+8).
    5. Returns processed DataFrames and coverage metadata.
    """
    provider = YFinanceDataProvider()

    # 1. Fetch Daily Data
    raw_daily = provider.fetch_daily(PRIMARY_INDEX_SYMBOL, period="max", force_reload=force_reload)
    clean_daily, daily_qual = validate_and_clean_dataset(raw_daily, is_intraday=False)

    # 2. Fetch Intraday Data
    raw_intra = provider.fetch_intraday(PRIMARY_INDEX_SYMBOL, interval=resolution, force_reload=force_reload)
    clean_intra, intra_qual = validate_and_clean_dataset(raw_intra, is_intraday=True, remove_lunch=True)

    # If 10m is requested, resample 5m bars
    if resolution == "10m" and not clean_intra.empty:
        clean_intra = resample_ohlcv_intraday(clean_intra, target_rule="10min")

    # 3. Fetch Volume Proxy Instrument if requested
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
    if period_key == "Custom" and custom_start and custom_end:
        start_ts = pd.to_datetime(custom_start).tz_localize(DISPLAY_TIMEZONE)
        end_ts = pd.to_datetime(custom_end).tz_localize(DISPLAY_TIMEZONE)
        clean_daily = clean_daily[(clean_daily.index >= start_ts) & (clean_daily.index <= end_ts)]
    elif period_key in ANALYSIS_PERIODS and ANALYSIS_PERIODS[period_key]["days"] is not None:
        days = ANALYSIS_PERIODS[period_key]["days"]
        cutoff = clean_daily.index[-1] - pd.Timedelta(days=days) if not clean_daily.empty else now
        clean_daily = clean_daily[clean_daily.index >= cutoff]

    # Calculate returns, ranges, MFE/MAE for daily data
    if not clean_daily.empty:
        clean_daily = calculate_returns(clean_daily, "Close")
        clean_daily = calculate_bar_hl_range(clean_daily)
        clean_daily["DayOfWeek"] = clean_daily.index.day_name()
        # Strictly keep Monday through Friday
        clean_daily = clean_daily[clean_daily["DayOfWeek"].isin(WEEKDAYS)]

    # Coverage reports
    daily_cov = get_dataset_coverage_report(clean_daily, PRIMARY_INDEX_SYMBOL, PRIMARY_INDEX_NAME, "1d")
    intra_cov = get_dataset_coverage_report(clean_intra, PRIMARY_INDEX_SYMBOL, PRIMARY_INDEX_NAME, resolution)

    return {
        "daily_df": clean_daily,
        "intraday_df": clean_intra,
        "volume_df": clean_vol,
        "has_valid_volume": has_valid_vol,
        "daily_cov": daily_cov,
        "intra_cov": intra_cov,
        "daily_qual": daily_qual,
        "intra_qual": intra_qual,
    }


# ==========================================
# Sidebar Navigation & Global Controls
# ==========================================
def render_sidebar():
    st.sidebar.markdown("## 🇯🇵 **Nikkei 225 Research**")
    st.sidebar.caption("Descriptive & Statistical Behavior Dashboard\n**Display Timezone: MYT (UTC+8)**")
    st.sidebar.markdown("---")

    # Custom Single-Page Navigation Selector (Single Source of Truth)
    nav_page = st.sidebar.radio(
        "📍 **Research Module**",
        [
            "📊 Market Overview",
            "📅 Day of Week Analysis",
            "⏱️ Intraday & Time Profile",
            "🌅 Opening & Gap Analysis",
            "📈 Volatility & MFE/MAE",
            "🎲 Statistical Distributions",
        ],
        index=0
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚙️ **Global Parameters**")

    # 1. Period Selector
    period_options = list(ANALYSIS_PERIODS.keys())
    selected_period = st.sidebar.selectbox("Analysis Period", period_options, index=0)

    custom_start, custom_end = None, None
    if selected_period == "Custom":
        c_start = st.sidebar.date_input("Start Date", value=datetime.date.today() - datetime.timedelta(days=365))
        c_end = st.sidebar.date_input("End Date", value=datetime.date.today())
        custom_start = str(c_start)
        custom_end = str(c_end)

    # 2. Weekday Filter
    weekday_options = ["All"] + WEEKDAYS
    selected_weekday = st.sidebar.selectbox("Filter Weekday", weekday_options, index=0)

    # 3. Intraday Resolution Selector
    selected_res = st.sidebar.selectbox("Intraday Resolution", SUPPORTED_RESOLUTIONS, index=0)

    # 4. Volume Proxy Selector
    vol_options = {k: v["name"] for k, v in VOLUME_INSTRUMENTS.items()}
    vol_options["NONE"] = "None / Disabled (Index Only)"
    selected_vol_key = st.sidebar.selectbox(
        "Tradable Volume Instrument",
        list(vol_options.keys()),
        format_func=lambda x: vol_options[x],
        index=0,
        help="Nikkei 225 (^N225) is an un-traded index with no direct exchange volume. Select a TSE ETF (e.g. 1321.T) for volume analysis."
    )

    st.sidebar.markdown("---")
    force_reload = st.sidebar.button("🔄 Force Refresh Data Cache")

    st.sidebar.markdown(
        """
        <div style="font-size: 11px; color: #8b949e; margin-top: 15px;">
        <b>TSE Cash Hours in MYT:</b><br>
        • Morning: 08:00 – 10:30<br>
        • Lunch: 10:30 – 11:30 (Filtered)<br>
        • Afternoon: 11:30 – 14:30
        </div>
        """,
        unsafe_allow_html=True
    )

    return {
        "page": nav_page,
        "period": selected_period,
        "custom_start": custom_start,
        "custom_end": custom_end,
        "weekday": selected_weekday,
        "resolution": selected_res,
        "volume_symbol": selected_vol_key if selected_vol_key != "NONE" else None,
        "force_reload": force_reload,
    }


# ==========================================
# Main Application Flow
# ==========================================
def main():
    params = render_sidebar()

    # Load data via cached pipeline
    data_bundle = load_all_market_data(
        period_key=params["period"],
        resolution=params["resolution"],
        volume_symbol=params["volume_symbol"],
        custom_start=params["custom_start"],
        custom_end=params["custom_end"],
        force_reload=params["force_reload"]
    )

    daily_df = data_bundle["daily_df"]
    intraday_df = data_bundle["intraday_df"]
    volume_df = data_bundle["volume_df"]
    has_valid_vol = data_bundle["has_valid_volume"]
    daily_cov = data_bundle["daily_cov"]
    intra_cov = data_bundle["intra_cov"]
    daily_qual = data_bundle["daily_qual"]

    # Apply Weekday filter if selected
    if params["weekday"] != "All" and not daily_df.empty:
        daily_df = daily_df[daily_df["DayOfWeek"] == params["weekday"]]
        if not intraday_df.empty:
            intraday_df = intraday_df[intraday_df.index.day_name() == params["weekday"]]

    # Universal Data Coverage & Integrity Banner
    st.markdown(
        f"""
        <div class="coverage-banner">
            <span class="badge badge-info">Coverage: {daily_cov.get('start_date_display', 'N/A')} → {daily_cov.get('end_date_display', 'N/A')}</span>
            <span class="badge">Timezone: {DISPLAY_TIMEZONE} (UTC+8)</span>
            <span class="badge badge-info">Sessions: {len(daily_df):,}</span>
            <span class="badge">Intraday Resolution: {params['resolution']} ({intra_cov.get('total_bars', 0):,} bars)</span>
            {f"<span class='badge'>Volume Proxy: {params['volume_symbol']}</span>" if has_valid_vol else "<span class='badge' style='background:#6e7681;'>Volume: Index Only</span>"}
        </div>
        """,
        unsafe_allow_html=True
    )

    # Conditionally Render Selected Module based on Custom Sidebar Radio
    page = params["page"]

    if "Market Overview" in page:
        render_overview_page(
            daily_df=daily_df,
            intraday_df=intraday_df,
            volume_df=volume_df,
            coverage_info=daily_cov,
            quality_report=daily_qual,
            period_label=params["period"],
        )

    elif "Day of Week" in page:
        render_weekday_page(
            daily_df=daily_df,
            intraday_df=intraday_df,
            volume_df=volume_df,
            has_valid_volume=has_valid_vol,
            volume_symbol=params["volume_symbol"] or "None",
        )

    elif "Intraday" in page:
        render_intraday_page(
            intraday_df=intraday_df,
            volume_df=volume_df,
            has_valid_volume=has_valid_vol,
            current_resolution=params["resolution"],
        )

    elif "Opening & Gap" in page:
        render_opening_page(
            daily_df=daily_df,
            intraday_df=intraday_df,
            volume_df=volume_df,
            has_valid_volume=has_valid_vol,
        )

    elif "Volatility & MFE/MAE" in page:
        render_volatility_page(
            daily_df=daily_df,
            intraday_df=intraday_df,
            volume_df=volume_df,
            has_valid_volume=has_valid_vol,
        )

    elif "Statistical Distributions" in page:
        render_distributions_page(
            daily_df=daily_df,
            intraday_df=intraday_df,
        )


if __name__ == "__main__":
    main()
