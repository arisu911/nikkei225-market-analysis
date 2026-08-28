"""
Opening Behavior & Opening Gap Analysis View (08:00 MYT TSE Open).
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

from src.calculations import calculate_opening_gaps, calculate_opening_ranges
from src.charts import (
    plot_distribution_histogram,
    _apply_dark_theme,
    COLOR_PRIMARY,
    COLOR_SUCCESS,
    COLOR_DANGER,
)


def render_opening_page(
    daily_df: pd.DataFrame,
    intraday_df: pd.DataFrame,
    volume_df: pd.DataFrame,
    has_valid_volume: bool = True
):
    st.markdown("## 🌅 Opening Behavior & Gap Analysis (08:00 MYT)")
    st.caption(
        "Descriptive statistical examination of the Tokyo Stock Exchange cash equity opening session at **08:00 MYT (09:00 JST)**. "
        "Examines opening gaps, gap-fill tendencies, and 5m, 15m, 30m, and 60m opening range expansions."
    )

    if daily_df.empty:
        st.warning("No daily data available for opening gap analysis.")
        return

    # 1. Opening Gap Calculations
    gaps_df = calculate_opening_gaps(daily_df, intraday_df=intraday_df)

    tab_gaps, tab_or = st.tabs(["🚀 Opening Gap & Gap-Fill Analysis", "⏱️ Opening Range Analysis (5m, 15m, 30m, 60m)"])

    with tab_gaps:
        if not gaps_df.empty:
            gaps_pct = gaps_df["Gap_Pct"].dropna()
            abs_gaps = gaps_df["Abs_Gap_Pct"].dropna()
            
            avg_gap = gaps_pct.mean()
            med_gap = gaps_pct.median()
            avg_abs_gap = abs_gaps.mean()
            
            gap_up_pct = (gaps_pct > 0).mean() * 100.0
            gap_down_pct = (gaps_pct < 0).mean() * 100.0
            
            # Gap fill stats
            total_gapped = len(gaps_df[gaps_df["Gap_Pct"] != 0])
            filled_count = gaps_df["Gap_Filled"].sum()
            fill_rate_pct = (filled_count / total_gapped * 100.0) if total_gapped > 0 else 0.0

            # Gap fill by direction
            up_gaps = gaps_df[gaps_df["Is_Gap_Up"]]
            down_gaps = gaps_df[gaps_df["Is_Gap_Down"]]
            
            up_fill_rate = (up_gaps["Gap_Filled"].mean() * 100.0) if not up_gaps.empty else np.nan
            down_fill_rate = (down_gaps["Gap_Filled"].mean() * 100.0) if not down_gaps.empty else np.nan

            col1, col2, col3, col4, col5, col6 = st.columns(6)
            with col1:
                st.metric("Avg Opening Gap", f"{avg_gap:+.2f}%")
            with col2:
                st.metric("Median Gap", f"{med_gap:+.2f}%")
            with col3:
                st.metric("Avg Absolute Gap", f"{avg_abs_gap:.2f}%")
            with col4:
                st.metric("Gap Up Frequency", f"{gap_up_pct:.1f}%")
            with col5:
                st.metric("Overall Fill Rate", f"{fill_rate_pct:.1f}%", help="Frequency where intraday price touched or crossed previous day close")
            with col6:
                st.metric("Total Gaps Analyzed", f"{len(gaps_df):,}")

            st.markdown("---")

            # Gap Fill Definition & Visualizations
            st.info(
                "💡 **Definition of Gap-Fill in this research:**\n\n"
                "- **Gap Up** ($Open_{08:00} > Close_{prev}$): Considered filled if the intraday $Low \\le Close_{prev}$.\n"
                "- **Gap Down** ($Open_{08:00} < Close_{prev}$): Considered filled if the intraday $High \\ge Close_{prev}$."
            )

            c_g1, c_g2 = st.columns(2)
            with c_g1:
                fig_gap_dist = plot_distribution_histogram(
                    gaps_pct,
                    title="Opening Gap Percentage Distribution (% from Prev Close)",
                    xlabel="Opening Gap (%)",
                    bins=45
                )
                st.plotly_chart(fig_gap_dist, use_container_width=True)

            with c_g2:
                # Gap Fill Comparison Bar
                fig_fill = go.Figure()
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
                st.plotly_chart(fig_fill, use_container_width=True)

            # Time to gap fill if intraday data available
            fill_times = gaps_df["Time_To_Fill_Min"].dropna()
            if not fill_times.empty:
                fill_times_valid = fill_times[fill_times >= 0].astype(int)
                if not fill_times_valid.empty:
                    st.markdown("### ⏱️ Time-to-Fill Distribution (Minutes from 08:00 MYT Open)")
                    fig_ttf = plot_distribution_histogram(
                        fill_times_valid,
                        title="Elapsed Minutes to Complete Gap Fill",
                        xlabel="Minutes Elapsed from 08:00 MYT Open",
                        bins=25,
                        show_zero_line=False,
                        non_negative=True,
                    )
                    st.plotly_chart(fig_ttf, use_container_width=True)

    with tab_or:
        if intraday_df.empty:
            st.info("Intraday dataset required to compute 5m, 15m, 30m, and 60m opening ranges.")
        else:
            or_dict = calculate_opening_ranges(intraday_df, windows_minutes=[5, 15, 30, 60])
            
            st.markdown("### 📊 Opening Window Performance & Range Expansion Summary")
            or_summary_rows = []
            
            for win_min, df_w in or_dict.items():
                if df_w.empty:
                    continue
                rets_w = df_w["OR_Return_Pct"].dropna()
                ranges_w = df_w["OR_Range_Pct"].dropna()
                ratios_w = df_w["OR_Ratio_Pct"].dropna()
                n = len(df_w)

                or_summary_rows.append({
                    "Opening Window": f"First {win_min} Minutes (08:00 – 08:{win_min:02d} MYT)" if win_min < 60 else "First 60 Minutes (08:00 – 09:00 MYT)",
                    "Sample Size (n)": n,
                    "Avg Return (%)": float(rets_w.mean()),
                    "Median Return (%)": float(rets_w.median()),
                    "Volatility (Std %)": float(rets_w.std()) if n > 1 else np.nan,
                    "Avg Range (%)": float(ranges_w.mean()),
                    "Median Range (%)": float(ranges_w.median()),
                    "Avg % of Full-Day Range": float(ratios_w.mean()),
                    "Median % of Full-Day Range": float(ratios_w.median()),
                    "Positive Window (%)": float((rets_w > 0).mean() * 100.0),
                })

            if or_summary_rows:
                or_sum_df = pd.DataFrame(or_summary_rows)
                st.dataframe(
                    or_sum_df.style.format({
                        "Sample Size (n)": "{:,}",
                        "Avg Return (%)": "{:+.2f}%",
                        "Median Return (%)": "{:+.2f}%",
                        "Volatility (Std %)": "{:.2f}%",
                        "Avg Range (%)": "{:.2f}%",
                        "Median Range (%)": "{:.2f}%",
                        "Avg % of Full-Day Range": "{:.1f}%",
                        "Median % of Full-Day Range": "{:.1f}%",
                        "Positive Window (%)": "{:.1f}%",
                    }),
                    use_container_width=True,
                    hide_index=True,
                )

                # Ratio comparison chart
                fig_or_ratio = go.Figure()
                for win_min, df_w in or_dict.items():
                    if not df_w.empty:
                        fig_or_ratio.add_trace(
                            go.Box(
                                y=df_w["OR_Ratio_Pct"].dropna(),
                                name=f"{win_min}m Window",
                                boxmean=True,
                            )
                        )
                fig_or_ratio.update_layout(
                    yaxis_title="Opening Range as % of Full-Day High-Low Range",
                    height=450,
                )
                _apply_dark_theme(fig_or_ratio, "Opening Range vs Full-Day Range Expansion Ratio (%)")
                st.plotly_chart(fig_or_ratio, use_container_width=True)
