"""
Statistical Distributions & Historical Probability-Style Frequency View.
"""

import streamlit as st
import pandas as pd
import numpy as np

from src.statistics import compute_distribution_metrics, compute_probability_frequencies
from src.charts import plot_distribution_histogram


def render_distributions_page(
    daily_df: pd.DataFrame,
    intraday_df: pd.DataFrame
):
    st.markdown("## 📊 Statistical Distributions & Movement Frequencies")
    st.caption(
        "Examines the full probability-style historical empirical distributions for Nikkei 225 returns, ranges, and absolute excursions. "
        "All figures reflect **historical empirical frequencies**, strictly non-predictive."
    )

    if daily_df.empty:
        st.warning("No daily data available for distribution analysis.")
        return

    rets = daily_df["Return_Pct"].dropna()
    ranges = daily_df["Range_Pct"].dropna()
    abs_rets = rets.abs()

    # 1. Comprehensive Percentile Table
    st.markdown("### 📋 Full Empirical Quantile Breakdown")
    m_ret = compute_distribution_metrics(rets, label="Session Return (%)")
    m_abs = compute_distribution_metrics(abs_rets, label="Absolute Move (%)")
    m_rng = compute_distribution_metrics(ranges, label="High-Low Range (%)")

    quant_df = pd.DataFrame([m_ret, m_abs, m_rng])
    st.dataframe(
        quant_df.style.format({
            "Count (n)": "{:,}",
            "Mean": "{:.2f}%",
            "Median": "{:.2f}%",
            "Std Dev": "{:.2f}%",
            "Min": "{:+.2f}%",
            "Max": "{:+.2f}%",
            "Skewness": "{:.2f}",
            "Kurtosis": "{:.2f}",
            "P10": "{:+.2f}%",
            "P25": "{:+.2f}%",
            "P50": "{:+.2f}%",
            "P75": "{:+.2f}%",
            "P90": "{:+.2f}%",
            "P95": "{:+.2f}%",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("---")

    # 2. Historical Frequency & Threshold Explorer
    st.markdown("### 🎲 Historical Movement Frequency Tables")
    st.caption("Historical sample frequencies of experiencing directional and large price moves.")

    col_t1, col_t2 = st.columns([2, 1])
    with col_t2:
        st.markdown("#### ⚙️ Custom Move Threshold")
        cust_th = st.slider("Absolute Move Threshold (%)", min_value=0.10, max_value=5.00, value=0.75, step=0.05)

    with col_t1:
        thresholds = sorted(list(set([0.25, 0.50, 1.00, 1.50, 2.00, cust_th])))
        freq_df = compute_probability_frequencies(rets, thresholds=thresholds)

        st.dataframe(
            freq_df.style.format({
                "Historical Frequency (%)": "{:.1f}%",
                "Occurrences (Count)": "{:,}",
                "Sample Size (n)": "{:,}",
            }),
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("---")

    # 3. Interactive Distribution Histograms
    col_h1, col_h2 = st.columns(2)
    with col_h1:
        fig_r = plot_distribution_histogram(
            rets,
            title="Nikkei 225 Session Return Distribution (%)",
            xlabel="Session Return (%)",
            bins=50,
        )
        st.plotly_chart(fig_r, use_container_width=True)

    with col_h2:
        fig_rng = plot_distribution_histogram(
            ranges,
            title="Nikkei 225 High-Low Range Distribution (%)",
            xlabel="Daily High-Low Range (%)",
            bins=50,
            show_zero_line=False,
        )
        st.plotly_chart(fig_rng, use_container_width=True)
