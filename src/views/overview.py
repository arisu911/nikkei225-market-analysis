"""
Overview View: High-Level Market Statistics, Coverage, Long-Term Seasonality, and Data Quality.
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.statistics import compute_distribution_metrics, compute_monthly_statistics, compute_yearly_statistics
from src.charts import COLOR_PRIMARY, COLOR_SUCCESS, COLOR_DANGER, COLOR_WARNING, COLOR_PURPLE, _apply_dark_theme


def render_overview_page(
    daily_df: pd.DataFrame,
    intraday_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    coverage_info: dict,
    quality_report: dict,
    period_label: str
):
    st.markdown("## 📊 Nikkei 225 Market Overview & Data Coverage")
    st.caption("Descriptive statistical summary of the Nikkei 225 index and TSE market behavior. All timestamps displayed in **MYT (UTC+8)**.")

    if daily_df.empty:
        st.warning("⚠️ No historical data available for the selected parameters. Please check your data connection or adjust the period.")
        return

    # Top KPI Metrics Row
    rets = daily_df["Return_Pct"].dropna()
    ranges = daily_df["Range_Pct"].dropna()
    
    avg_ret = rets.mean()
    med_ret = rets.median()
    vol_daily = rets.std()
    vol_annual = vol_daily * np.sqrt(250) if not np.isnan(vol_daily) else np.nan
    avg_range = ranges.mean()
    pos_pct = (rets > 0).mean() * 100.0
    neg_pct = (rets < 0).mean() * 100.0
    total_sessions = len(daily_df)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.metric("Avg Daily Return", f"{avg_ret:+.2f}%", help="Mean return from session open (08:00 MYT) to session close (14:30 MYT)")
    with col2:
        st.metric("Median Return", f"{med_ret:+.2f}%", help="Median session return")
    with col3:
        st.metric("Daily Volatility (Std)", f"{vol_daily:.2f}%", f"Ann: {vol_annual:.1f}%" if not np.isnan(vol_annual) else None)
    with col4:
        st.metric("Avg Daily Range", f"{avg_range:.2f}%", help="Average (High - Low) / Open %")
    with col5:
        st.metric("Positive Days", f"{pos_pct:.1f}%", f"Neg: {neg_pct:.1f}%")
    with col6:
        st.metric("Total Sessions (n)", f"{total_sessions:,}", f"Period: {period_label}")

    st.markdown("---")

    # Data Coverage & Quality Diagnostic Expander
    with st.expander("🔍 **Data Coverage, Source Validation & Quality Diagnostics**", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("### 📡 Data Coverage Summary")
            cov_df = pd.DataFrame([
                {"Property": "Primary Index Symbol", "Value": coverage_info.get("symbol", "^N225")},
                {"Property": "Instrument Name", "Value": coverage_info.get("instrument_name", "Nikkei 225 Index")},
                {"Property": "Start Date (MYT)", "Value": coverage_info.get("start_date_display", "N/A")},
                {"Property": "End Date (MYT)", "Value": coverage_info.get("end_date_display", "N/A")},
                {"Property": "Total Daily Sessions (n)", "Value": f"{total_sessions:,}"},
                {"Property": "Intraday Resolution", "Value": coverage_info.get("interval", "N/A")},
                {"Property": "Total Intraday Bars", "Value": f"{coverage_info.get('total_bars', 0):,}"},
                {"Property": "Display Timezone", "Value": "Asia/Kuala_Lumpur (MYT, UTC+8)"},
            ])
            st.dataframe(cov_df, use_container_width=True, hide_index=True)

        with c2:
            st.markdown("### 🛡️ Data Quality Safeguards Report")
            qual_df = pd.DataFrame([
                {"Diagnostic Check": "Initial Raw Rows Downloaded", "Status": f"{quality_report.get('initial_rows', 0):,}"},
                {"Diagnostic Check": "Duplicate Timestamps Removed", "Status": f"{quality_report.get('duplicate_timestamps', 0)}"},
                {"Diagnostic Check": "Null / Missing OHLC Rows Filtered", "Status": f"{quality_report.get('null_ohlc_rows', 0)}"},
                {"Diagnostic Check": "Zero / Negative Price Rows Filtered", "Status": f"{quality_report.get('zero_or_negative_prices', 0)}"},
                {"Diagnostic Check": "Illogical Bars (High < Low)", "Status": f"{quality_report.get('illogical_ohlc_bars', 0)}"},
                {"Diagnostic Check": "Off-Session Bars Excluded", "Status": f"{quality_report.get('off_session_bars', 0):,}"},
                {"Diagnostic Check": "Lunch Break Bars Excluded (10:30-11:30)", "Status": f"{quality_report.get('lunch_bars_removed', 0):,}"},
                {"Diagnostic Check": "Anomalies Flagged", "Status": "None detected" if not quality_report.get("anomalies_detected") else "Yes (Handled)"},
            ])
            st.dataframe(qual_df, use_container_width=True, hide_index=True)

    # Cumulative Price Path & Daily Range Distribution
    tab1, tab2 = st.tabs(["📈 Cumulative Session Return Path", "📅 Long-Term Yearly & Monthly Seasonality"])

    with tab1:
        cum_df = daily_df.sort_index().copy()
        cum_df["Cumulative_Return_Pct"] = (1.0 + cum_df["Return_Pct"] / 100.0).cumprod() - 1.0
        cum_df["Cumulative_Return_Pct"] *= 100.0

        fig_cum = go.Figure()
        fig_cum.add_trace(
            go.Scatter(
                x=cum_df.index,
                y=cum_df["Cumulative_Return_Pct"],
                mode="lines",
                name="Cumulative Return %",
                line=dict(color=COLOR_PRIMARY, width=2.2),
                fill="tozeroy",
                fillcolor="rgba(88, 166, 255, 0.08)",
            )
        )
        fig_cum.update_layout(
            xaxis_title="Date (MYT)",
            yaxis_title="Cumulative Return (%)",
            height=420,
        )
        _apply_dark_theme(fig_cum, "Nikkei 225 Cumulative Session Return Over Selected Period")
        st.plotly_chart(fig_cum, use_container_width=True)

    with tab2:
        col_y, col_m = st.columns(2)
        with col_y:
            st.markdown("### 📆 Yearly Performance Summary")
            yr_df = compute_yearly_statistics(daily_df)
            if not yr_df.empty:
                st.dataframe(
                    yr_df.style.format({
                        "Annual Return (%)": "{:+.2f}%",
                        "Avg Daily Return (%)": "{:+.2f}%",
                        "Daily Volatility (%)": "{:.2f}%",
                        "Annualized Vol (%)": "{:.1f}%",
                        "Max Drawdown (%)": "{:.2f}%",
                        "Sessions (n)": "{:,}",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Insufficient data for annual breakdown.")

        with col_m:
            st.markdown("### 🗓️ Monthly Seasonality (Jan–Dec)")
            mo_df = compute_monthly_statistics(daily_df)
            if not mo_df.empty:
                st.dataframe(
                    mo_df.style.format({
                        "Avg Return (%)": "{:+.2f}%",
                        "Median Return (%)": "{:+.2f}%",
                        "Volatility (Std %)": "{:.2f}%",
                        "Avg Range (%)": "{:.2f}%",
                        "Positive Days (%)": "{:.1f}%",
                        "Sessions (n)": "{:,}",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.info("Insufficient data for monthly breakdown.")
