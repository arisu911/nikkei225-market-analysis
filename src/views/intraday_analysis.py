"""
Intraday Analysis View: Time-of-Day Progression, Multi-Resolution Buckets, and Custom Window Explorer.
"""

import streamlit as st
import pandas as pd
import numpy as np

from config.settings import STANDARD_TIME_WINDOWS_MYT
from src.market_sessions import get_custom_window_bars, filter_tse_sessions
from src.statistics import compute_intraday_time_profile
from src.charts import plot_intraday_profile, plot_distribution_histogram


def render_intraday_page(
    intraday_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    has_valid_volume: bool = True,
    current_resolution: str = "5m"
):
    st.markdown("## ⏱️ Intraday Market Behavior & Time-of-Day Profile")
    st.caption(
        "Detailed statistical profile of how the Nikkei 225 moves throughout the Tokyo Stock Exchange session. "
        "All timestamps displayed in **MYT (UTC+8)** with the 10:30–11:30 MYT lunch break filtered out."
    )

    if intraday_df.empty:
        st.warning("⚠️ No intraday data is available for the selected parameters. (Note: Free Yahoo Finance intraday history is limited to ~60 days for 5m/15m/30m and ~730 days for 60m).")
        return

    # Filter to active TSE sessions
    clean_intra = filter_tse_sessions(intraday_df, include_lunch=False)

    # Calculate time-of-day progression profile
    profile_df = compute_intraday_time_profile(clean_intra, has_valid_volume=has_valid_volume)

    # 1. Main Time-of-Day Line Charts (4 subplots)
    st.plotly_chart(plot_intraday_profile(profile_df), use_container_width=True)

    st.markdown("---")

    # 2. Standard Intraday Time Buckets Table
    st.markdown("### 🕒 Standard Intraday Time Windows Analysis (MYT)")
    st.caption("Aggregated statistical behavior across defined institutional time segments.")

    bucket_records = []

    for start_t, end_t, label in STANDARD_TIME_WINDOWS_MYT:
        # Extract bars for this window
        win_bars = get_custom_window_bars(clean_intra, start_t, end_t)
        if win_bars.empty:
            continue

        # Group by date to calculate window return and range per session
        sess_returns = []
        sess_ranges = []
        sess_vols = []

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
            if "Volume" in grp_sorted.columns:
                sess_vols.append(grp_sorted["Volume"].sum())

        s_rets = pd.Series(sess_returns).dropna()
        s_rngs = pd.Series(sess_ranges).dropna()
        n = len(s_rets)
        if n == 0:
            continue

        pos_pct = (s_rets > 0).mean() * 100.0
        neg_pct = (s_rets < 0).mean() * 100.0

        rec = {
            "Time Window (MYT)": f"{start_t} – {end_t}",
            "Segment Description": label,
            "Sample Size (n)": n,
            "Avg Return (%)": float(s_rets.mean()),
            "Median Return (%)": float(s_rets.median()),
            "Avg Abs Move (%)": float(s_rets.abs().mean()),
            "Volatility (Std %)": float(s_rets.std()) if n > 1 else np.nan,
            "Avg Range (%)": float(s_rngs.mean()),
            "Median Range (%)": float(s_rngs.median()),
            "Positive Sessions (%)": float(pos_pct),
            "Negative Sessions (%)": float(neg_pct),
        }
        bucket_records.append(rec)

    bucket_df = pd.DataFrame(bucket_records)
    if not bucket_df.empty:
        st.dataframe(
            bucket_df.style.format({
                "Sample Size (n)": "{:,}",
                "Avg Return (%)": "{:+.2f}%",
                "Median Return (%)": "{:+.2f}%",
                "Avg Abs Move (%)": "{:.2f}%",
                "Volatility (Std %)": "{:.2f}%",
                "Avg Range (%)": "{:.2f}%",
                "Median Range (%)": "{:.2f}%",
                "Positive Sessions (%)": "{:.1f}%",
                "Negative Sessions (%)": "{:.1f}%",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")

    # 3. Custom Intraday Window Calculator
    st.markdown("### 🎛️ Custom Intraday Window Inspector")
    st.caption("Select any arbitrary custom start and end time (MYT) within TSE hours to inspect exact statistical behavior.")

    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        cust_start = st.time_input("Start Time (MYT)", value=pd.to_datetime("08:00").time())
    with c2:
        cust_end = st.time_input("End Time (MYT)", value=pd.to_datetime("09:15").time())

    start_str = cust_start.strftime("%H:%M")
    end_str = cust_end.strftime("%H:%M")

    if cust_start >= cust_end:
        st.error("Start time must be strictly before end time.")
    else:
        cust_bars = get_custom_window_bars(clean_intra, start_str, end_str)
        if cust_bars.empty:
            st.info(f"No trading bars found in window {start_str}–{end_str} (Make sure the window falls within 08:00–10:30 or 11:30–14:30 MYT).")
        else:
            cust_rets = []
            for s_date, grp in cust_bars.groupby(cust_bars.index.date):
                grp_sorted = grp.sort_index()
                o = grp_sorted["Open"].iloc[0]
                c = grp_sorted["Close"].iloc[-1]
                cust_rets.append(((c - o) / o) * 100.0)

            s_cust = pd.Series(cust_rets).dropna()
            if not s_cust.empty:
                col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
                with col_k1:
                    st.metric("Avg Window Return", f"{s_cust.mean():+.2f}%")
                with col_k2:
                    st.metric("Median Return", f"{s_cust.median():+.2f}%")
                with col_k3:
                    st.metric("Window Volatility", f"{s_cust.std():.2f}%")
                with col_k4:
                    st.metric("Positive Frequency", f"{(s_cust > 0).mean() * 100:.1f}%")
                with col_k5:
                    st.metric("Sessions Analyzed", f"{len(s_cust):,}")

                fig_cust = plot_distribution_histogram(
                    s_cust,
                    title=f"Custom Window Return Distribution ({start_str} – {end_str} MYT)",
                    xlabel="Window Return (%)"
                )
                st.plotly_chart(fig_cust, use_container_width=True)
