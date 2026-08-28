"""
Day-of-Week Analysis View (Monday–Friday) for Nikkei 225 Market Behavior.
"""

import streamlit as st
import pandas as pd
import numpy as np

from src.statistics import compute_weekday_statistics
from src.charts import (
    plot_weekday_comparisons,
    plot_box_plots,
    plot_weekday_time_heatmap,
)


def render_weekday_page(
    daily_df: pd.DataFrame,
    intraday_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    has_valid_volume: bool = True,
    volume_symbol: str = "1321.T"
):
    st.markdown("## 📅 Day-of-Week Behavior Analysis (Monday – Friday)")
    st.caption(
        "Descriptive statistical breakdown of Nikkei 225 behavior across individual trading weekdays. "
        "All calculations represent historical descriptive statistics across the selected period."
    )

    if daily_df.empty:
        st.warning("No daily data available for day-of-week analysis.")
        return

    # Strictly filter to Monday through Friday (exclude weekends)
    valid_weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    daily_df = daily_df[daily_df["DayOfWeek"].isin(valid_weekdays)].copy()

    # Compute weekday statistics
    wk_stats = compute_weekday_statistics(daily_df, has_valid_volume=has_valid_volume)
    
    if wk_stats.empty:
        st.info("Insufficient data to compute weekday statistics.")
        return

    # 1. Monday-Friday KPI Comparison Charts
    st.plotly_chart(plot_weekday_comparisons(wk_stats), use_container_width=True)

    st.markdown("---")

    # 2. Comprehensive Tabular Statistics
    st.markdown("### 📋 Weekday Statistical Summary Table")
    st.caption("Includes Sample Size (n), Return Statistics, Volatility Quantiles, Range, and Volume.")

    format_dict = {
        "Sample Size (n)": "{:,}",
        "Avg Return (%)": "{:+.2f}%",
        "Median Return (%)": "{:+.2f}%",
        "Avg Abs Move (%)": "{:.2f}%",
        "Avg Range (%)": "{:.2f}%",
        "Median Range (%)": "{:.2f}%",
        "Max Return (%)": "{:+.2f}%",
        "Min Return (%)": "{:+.2f}%",
        "Positive Days (%)": "{:.1f}%",
        "Negative Days (%)": "{:.1f}%",
        "Std Dev (%)": "{:.2f}%",
        "25th Pct (%)": "{:+.2f}%",
        "75th Pct (%)": "{:+.2f}%",
        "90th Pct (%)": "{:+.2f}%",
        "95th Pct (%)": "{:+.2f}%",
    }
    if has_valid_volume and "Relative Volume" in wk_stats.columns:
        format_dict["Avg Volume"] = "{:,.0f}"
        format_dict["Median Volume"] = "{:,.0f}"
        format_dict["Relative Volume"] = "{:.2f}x"

    st.dataframe(
        wk_stats.style.format(format_dict),
        use_container_width=True,
        hide_index=True,
    )

    # Download CSV
    csv_data = wk_stats.to_csv(index=False).encode("utf-8")
    st.download_button(
        "📥 Download Weekday Statistics (CSV)",
        data=csv_data,
        file_name="nikkei225_weekday_statistics.csv",
        mime="text/csv",
    )

    st.markdown("---")

    # 3. Box Plots and Heatmap
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📦 Return Distribution by Weekday (Box Plots)")
        fig_box = plot_box_plots(
            daily_df,
            x_col="DayOfWeek",
            y_col="Return_Pct",
            title="Weekday Return Distributions & Outliers",
            ylabel="Session Return (%)",
        )
        st.plotly_chart(fig_box, use_container_width=True)

    with col2:
        st.markdown("### 🗺️ Weekday × Time Slot Heatmap")
        if not intraday_df.empty:
            fig_hm = plot_weekday_time_heatmap(
                intraday_df,
                value_col="Return_Pct",
                title="Mean Return (%) by Weekday & Time Slot (MYT)"
            )
            st.plotly_chart(fig_hm, use_container_width=True)
        else:
            st.info("Intraday dataset required for Weekday × Time Slot heatmap.")
