"""
Volatility, Morning vs Afternoon, and MFE/MAE Excursion Path Analysis View.
"""

import streamlit as st
import pandas as pd
import numpy as np

from src.calculations import (
    calculate_rolling_volatility,
    calculate_morning_vs_afternoon,
    calculate_bar_hl_range,
)
from src.statistics import compute_distribution_metrics
from src.charts import (
    plot_rolling_volatility_chart,
    plot_morning_vs_afternoon_comparison,
    plot_mfe_mae_scatter,
    plot_distribution_histogram,
)


def render_volatility_page(
    daily_df: pd.DataFrame,
    intraday_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    has_valid_volume: bool = True
):
    st.markdown("## 📈 Volatility, Session Comparison & Excursion Path Analysis")
    st.caption(
        "Descriptive metrics of Nikkei 225 price dispersion, rolling multi-session volatility regimes, "
        "Morning vs Afternoon session dynamics, and Maximum Favorable/Adverse Excursion (MFE/MAE) paths."
    )

    if daily_df.empty:
        st.warning("No historical daily data available for volatility analysis.")
        return

    # Ensure MFE and MAE columns exist on daily_df
    if "MFE_Pct" not in daily_df.columns or "MAE_Pct" not in daily_df.columns:
        daily_df = calculate_bar_hl_range(daily_df)

    tab_vol, tab_m_vs_a, tab_mfe_mae = st.tabs([
        "📊 Volatility Measures & Rolling Regimes",
        "⚖️ Morning vs Afternoon Session Comparison",
        "🎯 Maximum Excursion Path (MFE / MAE)"
    ])

    with tab_vol:
        # Volatility summary metrics
        rets = daily_df["Return_Pct"].dropna()
        ranges = daily_df["Range_Pct"].dropna()
        
        vol_dist = compute_distribution_metrics(rets, label="Daily Session Return (%)")
        range_dist = compute_distribution_metrics(ranges, label="Daily High-Low Range (%)")

        st.markdown("### 📋 Return and Range Volatility Quantile Profile")
        quant_df = pd.DataFrame([vol_dist, range_dist])
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

        # Rolling Volatility Line Chart
        st.markdown("### 🌊 Multi-Window Rolling Historical Volatility")
        rolling_df = calculate_rolling_volatility(daily_df, windows=[20, 60, 120])
        if not rolling_df.empty:
            st.plotly_chart(plot_rolling_volatility_chart(rolling_df), use_container_width=True)

    with tab_m_vs_a:
        st.markdown("### ⚖️ Morning (08:00–10:30 MYT) vs Afternoon (11:30–14:30 MYT)")
        st.caption("Direct comparative statistical assessment between the TSE Morning and Afternoon cash sessions.")

        if intraday_df.empty:
            st.info("Intraday dataset required for Morning vs Afternoon comparative breakdown.")
        else:
            m_df, a_df = calculate_morning_vs_afternoon(intraday_df, volume_df)
            
            if not m_df.empty and not a_df.empty:
                # Comparison table
                m_rets = m_df["Return_Pct"].dropna()
                a_rets = a_df["Return_Pct"].dropna()
                m_rng = m_df["Range_Pct"].dropna()
                a_rng = a_df["Range_Pct"].dropna()

                m_rec = {
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
                }

                a_rec = {
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

                comp_df = pd.DataFrame([m_rec, a_rec])
                st.dataframe(
                    comp_df.style.format({
                        "Sessions (n)": "{:,}",
                        "Avg Return (%)": "{:+.2f}%",
                        "Median Return (%)": "{:+.2f}%",
                        "Volatility (Std %)": "{:.2f}%",
                        "Avg Range (%)": "{:.2f}%",
                        "Median Range (%)": "{:.2f}%",
                        "Positive Frequency (%)": "{:.1f}%",
                        "Negative Frequency (%)": "{:.1f}%",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

                st.plotly_chart(plot_morning_vs_afternoon_comparison(m_df, a_df), use_container_width=True)

    with tab_mfe_mae:
        st.markdown("### 🎯 Maximum Favorable (MFE) vs Adverse (MAE) Excursions")
        st.caption(
            "Descriptive examination of the intraday path traveled from the 08:00 MYT open price. "
            "**MFE** represents the maximum upward excursion from open; **MAE** represents the maximum downward excursion."
        )

        mfe_s = daily_df["MFE_Pct"].dropna()
        mae_s = daily_df["MAE_Pct"].dropna()

        if not mfe_s.empty and not mae_s.empty:
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Avg MFE (Upward)", f"+{mfe_s.mean():.2f}%", help="Average maximum upward excursion from open")
            with col_m2:
                st.metric("Median MFE", f"+{mfe_s.median():.2f}%")
            with col_m3:
                st.metric("Avg MAE (Downward)", f"{mae_s.mean():.2f}%", help="Average maximum downward excursion from open")
            with col_m4:
                st.metric("Median MAE", f"{mae_s.median():.2f}%")

            st.markdown("---")

            # Excursion Quantile Profile Table
            st.markdown("#### 📋 MFE & MAE Excursion Quantile Profile")
            mfe_dist = compute_distribution_metrics(mfe_s, label="MFE (Max Upward % from Open)")
            mae_dist = compute_distribution_metrics(mae_s, label="MAE (Max Downward % from Open)")
            excursion_quant_df = pd.DataFrame([mfe_dist, mae_dist])
            st.dataframe(
                excursion_quant_df.style.format({
                    "Count (n)": "{:,}",
                    "Mean": "{:+.2f}%",
                    "Median": "{:+.2f}%",
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

            st.plotly_chart(plot_mfe_mae_scatter(daily_df), use_container_width=True)

            c_h1, c_h2 = st.columns(2)
            with c_h1:
                st.plotly_chart(
                    plot_distribution_histogram(mfe_s, "MFE Distribution (Max Upward % from Open)", "MFE (%)", bins=35, non_negative=True),
                    use_container_width=True
                )
            with c_h2:
                st.plotly_chart(
                    plot_distribution_histogram(mae_s, "MAE Distribution (Max Downward % from Open)", "MAE (%)", bins=35),
                    use_container_width=True
                )
        else:
            st.info("Insufficient data to compute MFE/MAE excursions.")
