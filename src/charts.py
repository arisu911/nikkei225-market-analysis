"""
Interactive Plotly Visualizations for Nikkei 225 Quantitative Dashboard.
Designed with sleek, dark-mode institutional aesthetic, high readability, and clean tooltips.
"""

from typing import List, Optional
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Clean institutional color palette
THEME_BG = "#0e1117"
THEME_CARD_BG = "#161b22"
THEME_GRID = "#21262d"
COLOR_PRIMARY = "#58a6ff"       # Cyan/Blue
COLOR_SUCCESS = "#3fb950"       # Green
COLOR_DANGER = "#f85149"        # Red
COLOR_WARNING = "#d29922"       # Amber/Yellow
COLOR_PURPLE = "#bc8cff"        # Violet
COLOR_TEXT = "#e6edf3"
COLOR_MUTED = "#8b949e"


def _apply_dark_theme(fig: go.Figure, title: str = "") -> go.Figure:
    """Apply unified quantitative dark theme to any Plotly figure."""
    fig.update_layout(
        title=dict(
            text=f"<b>{title}</b>",
            font=dict(size=16, color=COLOR_TEXT, family="Segoe UI, Roboto, sans-serif"),
            x=0.02,
            y=0.96,
        ),
        paper_bgcolor=THEME_CARD_BG,
        plot_bgcolor=THEME_CARD_BG,
        font=dict(color=COLOR_TEXT, family="Segoe UI, Roboto, sans-serif"),
        margin=dict(l=40, r=30, t=55, b=40),
        legend=dict(
            bgcolor="rgba(22, 27, 34, 0.8)",
            bordercolor=THEME_GRID,
            borderwidth=1,
            font=dict(size=11, color=COLOR_TEXT),
        ),
        xaxis=dict(
            gridcolor=THEME_GRID,
            showgrid=True,
            zerolinecolor=THEME_GRID,
            tickfont=dict(size=11, color=COLOR_MUTED),
            title_font=dict(size=12, color=COLOR_TEXT),
        ),
        yaxis=dict(
            gridcolor=THEME_GRID,
            showgrid=True,
            zerolinecolor=THEME_GRID,
            tickfont=dict(size=11, color=COLOR_MUTED),
            title_font=dict(size=12, color=COLOR_TEXT),
        ),
        hoverlabel=dict(
            bgcolor="#1f242c",
            font_size=12,
            font_family="Segoe UI, Roboto, sans-serif",
        ),
    )
    return fig


def plot_intraday_profile(profile_df: pd.DataFrame) -> go.Figure:
    """
    Plot intraday time-of-day progression profile for Return, Volatility, and Range.
    """
    if profile_df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Average & Median Return by Time Slot (%)",
            "Volatility (Std Dev of Returns) by Time Slot",
            "Average & Median High-Low Range (%)",
            "Positive vs Negative Frequency (%)"
        ),
        vertical_spacing=0.15,
        horizontal_spacing=0.10,
    )

    x_times = profile_df["Time (MYT)"]

    # 1. Returns
    fig.add_trace(
        go.Scatter(
            x=x_times, y=profile_df["Avg Return (%)"],
            mode="lines+markers", name="Avg Return %",
            line=dict(color=COLOR_PRIMARY, width=2.5),
            marker=dict(size=5),
        ),
        row=1, col=1
    )
    fig.add_trace(
        go.Scatter(
            x=x_times, y=profile_df["Median Return (%)"],
            mode="lines", name="Median Return %",
            line=dict(color=COLOR_WARNING, width=1.8, dash="dot"),
        ),
        row=1, col=1
    )

    # 2. Volatility
    fig.add_trace(
        go.Scatter(
            x=x_times, y=profile_df["Volatility (Std)"],
            mode="lines+markers", name="Volatility (Std)",
            line=dict(color=COLOR_PURPLE, width=2.5),
            fill="tozeroy", fillcolor="rgba(188, 140, 255, 0.15)",
            marker=dict(size=5),
        ),
        row=1, col=2
    )

    # 3. Range
    fig.add_trace(
        go.Scatter(
            x=x_times, y=profile_df["Avg Range (%)"],
            mode="lines+markers", name="Avg Range %",
            line=dict(color=COLOR_SUCCESS, width=2.5),
            marker=dict(size=5),
        ),
        row=2, col=1
    )

    # 4. Pos/Neg %
    fig.add_trace(
        go.Bar(
            x=x_times, y=profile_df["Positive Bars (%)"],
            name="Positive %", marker_color=COLOR_SUCCESS, opacity=0.85
        ),
        row=2, col=2
    )
    fig.add_trace(
        go.Bar(
            x=x_times, y=profile_df["Negative Bars (%)"],
            name="Negative %", marker_color=COLOR_DANGER, opacity=0.85
        ),
        row=2, col=2
    )

    fig.update_layout(barmode="stack", height=650)
    return _apply_dark_theme(fig, "TSE Intraday Profile Across Time Slots (MYT)")


def plot_weekday_comparisons(weekday_df: pd.DataFrame) -> go.Figure:
    """
    Plot Monday–Friday comparative performance and volatility.
    """
    if weekday_df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=1, cols=3,
        subplot_titles=("Average & Median Return (%)", "Average Daily Range (%)", "Positive vs Negative Days (%)"),
        horizontal_spacing=0.08
    )

    days = weekday_df["Day of Week"]

    # Returns
    fig.add_trace(
        go.Bar(x=days, y=weekday_df["Avg Return (%)"], name="Avg Return %", marker_color=COLOR_PRIMARY),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(x=days, y=weekday_df["Median Return (%)"], name="Median Return %", marker_color=COLOR_WARNING),
        row=1, col=1
    )

    # Range
    fig.add_trace(
        go.Bar(x=days, y=weekday_df["Avg Range (%)"], name="Avg Range %", marker_color=COLOR_PURPLE),
        row=1, col=2
    )

    # Pos / Neg %
    fig.add_trace(
        go.Bar(x=days, y=weekday_df["Positive Days (%)"], name="Positive %", marker_color=COLOR_SUCCESS),
        row=1, col=3
    )
    fig.add_trace(
        go.Bar(x=days, y=weekday_df["Negative Days (%)"], name="Negative %", marker_color=COLOR_DANGER),
        row=1, col=3
    )

    fig.update_layout(barmode="group", height=400)
    return _apply_dark_theme(fig, "Day-of-Week (Monday–Friday) Comparative Statistics")


def plot_distribution_histogram(
    series: pd.Series,
    title: str,
    xlabel: str,
    bins: int = 40,
    show_zero_line: bool = True,
    non_negative: bool = False
) -> go.Figure:
    """
    Plot clean distribution histogram with mean and median markers.
    """
    clean_s = series.dropna()
    if clean_s.empty:
        return go.Figure()

    if non_negative:
        clean_s = clean_s[clean_s >= 0]
        if clean_s.empty:
            return go.Figure()

    mean_val = float(clean_s.mean())
    med_val = float(clean_s.median())

    fig = go.Figure()
    hist_kwargs = dict(
        x=clean_s,
        nbinsx=bins,
        name="Observations",
        marker_color=COLOR_PRIMARY,
        opacity=0.75,
    )
    if non_negative:
        hist_kwargs["xbins"] = dict(start=0)

    fig.add_trace(go.Histogram(**hist_kwargs))

    # Mean and median vertical lines
    mean_annot = f"Mean: {mean_val:.1f}m" if non_negative else f"Mean: {mean_val:.2f}%"
    med_annot = f"Median: {med_val:.1f}m" if non_negative else f"Median: {med_val:.2f}%"

    fig.add_vline(x=mean_val, line_width=2, line_dash="dash", line_color=COLOR_WARNING, annotation_text=mean_annot, annotation_position="top left")
    fig.add_vline(x=med_val, line_width=2, line_dash="dot", line_color=COLOR_SUCCESS, annotation_text=med_annot, annotation_position="top right")

    if show_zero_line and not non_negative:
        fig.add_vline(x=0, line_width=1.5, line_color=COLOR_MUTED)

    fig.update_layout(
        xaxis_title=xlabel,
        yaxis_title="Count of Sessions",
        height=420
    )
    if non_negative:
        fig.update_xaxes(rangemode="nonnegative")

    return _apply_dark_theme(fig, title)


def plot_box_plots(
    df: pd.DataFrame,
    x_col: str,
    y_col: str,
    title: str,
    ylabel: str = "Return (%)"
) -> go.Figure:
    """
    Generate box plots across categories (e.g. Day of Week or Time Buckets).
    """
    if df.empty or x_col not in df.columns or y_col not in df.columns:
        return go.Figure()

    df_clean = df.copy()
    if x_col == "DayOfWeek":
        valid_days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
        df_clean = df_clean[df_clean[x_col].isin(valid_days)]
        df_clean[x_col] = pd.Categorical(df_clean[x_col], categories=valid_days, ordered=True)
        df_clean = df_clean.sort_values(x_col)

    fig = px.box(
        df_clean,
        x=x_col,
        y=y_col,
        color=x_col,
        category_orders={x_col: ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]} if x_col == "DayOfWeek" else None,
        points="outliers",
        color_discrete_sequence=[COLOR_PRIMARY, COLOR_SUCCESS, COLOR_WARNING, COLOR_PURPLE, COLOR_DANGER],
    )
    fig.add_hline(y=0, line_width=1, line_color=COLOR_MUTED, line_dash="dash")
    if x_col == "DayOfWeek":
        fig.update_xaxes(
            categoryorder="array",
            categoryarray=["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"],
            title_text="Day of Week"
        )
    fig.update_layout(showlegend=False, yaxis_title=ylabel, height=450)
    return _apply_dark_theme(fig, title)


def plot_weekday_time_heatmap(
    intraday_df: pd.DataFrame,
    value_col: str = "Return_Pct",
    title: str = "Weekday × Time Slot Heatmap (Mean Return %)"
) -> go.Figure:
    """
    Plot 2D heatmap cross-tabulating Weekday vs Intraday Time Slot.
    """
    if intraday_df.empty:
        return go.Figure()

    df = intraday_df.copy()
    if "Time_Slot" not in df.columns:
        df["Time_Slot"] = [t.strftime("%H:%M") for t in df.index.time]
    if "DayOfWeek" not in df.columns:
        df["DayOfWeek"] = df.index.day_name()
    if value_col not in df.columns:
        df["Return_Pct"] = df["Close"].pct_change() * 100.0

    valid_weekdays = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
    df = df[df["DayOfWeek"].isin(valid_weekdays)]

    pivot = df.pivot_table(index="DayOfWeek", columns="Time_Slot", values=value_col, aggfunc="mean")
    
    # Strictly reindex weekdays to Mon-Fri
    ordered_days = [d for d in valid_weekdays if d in pivot.index]
    pivot = pivot.reindex(ordered_days)

    fig = go.Figure(
        data=go.Heatmap(
            z=pivot.values,
            x=pivot.columns,
            y=pivot.index,
            colorscale="RdBu",
            zmid=0.0,
            colorbar=dict(title=dict(text=value_col, side="right")),
        )
    )
    fig.update_layout(
        xaxis_title="Time of Day (MYT)",
        yaxis_title="Weekday",
        height=380
    )
    return _apply_dark_theme(fig, title)


def plot_morning_vs_afternoon_comparison(
    m_df: pd.DataFrame,
    a_df: pd.DataFrame
) -> go.Figure:
    """
    Plot side-by-side distribution and comparison for Morning vs Afternoon sessions.
    """
    if m_df.empty or a_df.empty:
        return go.Figure()

    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=("Session Return Distribution (%)", "Session Range Distribution (%)")
    )

    # Return distributions
    fig.add_trace(
        go.Box(y=m_df["Return_Pct"], name="Morning (08:00-10:30)", marker_color=COLOR_PRIMARY, boxmean=True),
        row=1, col=1
    )
    fig.add_trace(
        go.Box(y=a_df["Return_Pct"], name="Afternoon (11:30-14:30)", marker_color=COLOR_PURPLE, boxmean=True),
        row=1, col=1
    )

    # Range distributions
    fig.add_trace(
        go.Box(y=m_df["Range_Pct"], name="Morning (08:00-10:30)", marker_color=COLOR_PRIMARY, showlegend=False, boxmean=True),
        row=1, col=2
    )
    fig.add_trace(
        go.Box(y=a_df["Range_Pct"], name="Afternoon (11:30-14:30)", marker_color=COLOR_PURPLE, showlegend=False, boxmean=True),
        row=1, col=2
    )

    fig.update_layout(height=450)
    return _apply_dark_theme(fig, "Morning Session vs Afternoon Session Behavior")


def plot_mfe_mae_scatter(daily_df: pd.DataFrame) -> go.Figure:
    """
    Plot Maximum Favorable Excursion (MFE) vs Maximum Adverse Excursion (MAE) path scatter.
    """
    if daily_df.empty or "MFE_Pct" not in daily_df.columns or "MAE_Pct" not in daily_df.columns:
        return go.Figure()

    df_clean = daily_df.dropna(subset=["MFE_Pct", "MAE_Pct"]).copy()
    if df_clean.empty:
        return go.Figure()

    if "Return_Pct" not in df_clean.columns:
        df_clean["Return_Pct"] = ((df_clean["Close"] - df_clean["Open"]) / df_clean["Open"]) * 100.0

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df_clean["MAE_Pct"],
            y=df_clean["MFE_Pct"],
            mode="markers",
            marker=dict(
                size=7,
                color=df_clean["Return_Pct"],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title=dict(text="Final Return %", side="right")),
                opacity=0.8,
            ),
            text=[f"Date: {d.strftime('%Y-%m-%d') if hasattr(d, 'strftime') else str(d)[:10]}<br>Return: {r:+.2f}%<br>MFE: +{mfe:.2f}%<br>MAE: {mae:.2f}%" 
                  for d, r, mfe, mae in zip(df_clean.index, df_clean["Return_Pct"], df_clean["MFE_Pct"], df_clean["MAE_Pct"])],
            hoverinfo="text",
        )
    )

    fig.add_vline(x=0, line_width=1, line_color=COLOR_MUTED, line_dash="dash")
    fig.add_hline(y=0, line_width=1, line_color=COLOR_MUTED, line_dash="dash")

    fig.update_layout(
        xaxis_title="Maximum Adverse Excursion - MAE (%) [Down from Open]",
        yaxis_title="Maximum Favorable Excursion - MFE (%) [Up from Open]",
        height=500,
    )
    return _apply_dark_theme(fig, "Daily Intraday Path: MFE vs MAE from 08:00 MYT Open")


def plot_rolling_volatility_chart(rolling_df: pd.DataFrame) -> go.Figure:
    """
    Plot rolling historical volatility trend across sessions.
    """
    if rolling_df.empty:
        return go.Figure()

    fig = go.Figure()
    cols = [c for c in ["Vol_Annual_20d", "Vol_Annual_60d", "Vol_Annual_120d"] if c in rolling_df.columns]
    colors = [COLOR_PRIMARY, COLOR_WARNING, COLOR_PURPLE]

    for col, color in zip(cols, colors):
        label = col.replace("Vol_Annual_", "").replace("d", "-Session Annualized Vol (%)")
        fig.add_trace(
            go.Scatter(
                x=rolling_df.index,
                y=rolling_df[col],
                mode="lines",
                name=label,
                line=dict(width=2, color=color),
            )
        )

    fig.update_layout(
        xaxis_title="Date (MYT)",
        yaxis_title="Annualized Realized Volatility (%)",
        height=450,
    )
    return _apply_dark_theme(fig, "Rolling Historical Realized Volatility Trend")
