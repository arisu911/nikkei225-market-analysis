"""
Unit tests for statistical distributions, weekday metrics, and probability frequencies.
"""

import pytest
import pandas as pd
import numpy as np
from src.statistics import (
    compute_distribution_metrics,
    compute_weekday_statistics,
    compute_probability_frequencies,
    compute_monthly_statistics,
    compute_yearly_statistics,
)


def test_distribution_metrics():
    # Symmetric sequence: [-2, -1, 0, 1, 2]
    s = pd.Series([-2.0, -1.0, 0.0, 1.0, 2.0])
    metrics = compute_distribution_metrics(s, percentiles=[50], label="Test")
    
    assert metrics["Count (n)"] == 5
    assert pytest.approx(metrics["Mean"], 0.001) == 0.0
    assert pytest.approx(metrics["Median"], 0.001) == 0.0
    assert pytest.approx(metrics["Min"], 0.001) == -2.0
    assert pytest.approx(metrics["Max"], 0.001) == 2.0
    assert pytest.approx(metrics["P50"], 0.001) == 0.0


def test_weekday_statistics():
    # 2 Mondays (+1%, -1%), 1 Tuesday (+2%)
    dates = pd.to_datetime(["2026-08-17", "2026-08-24", "2026-08-18"]) # Mon, Mon, Tue
    df = pd.DataFrame({
        "Return_Pct": [1.0, -1.0, 2.0],
        "Range_Pct": [2.0, 2.0, 3.0],
        "DayOfWeek": ["Monday", "Monday", "Tuesday"],
    }, index=dates)

    wk_df = compute_weekday_statistics(df, has_valid_volume=False)
    mon_stats = wk_df[wk_df["Day of Week"] == "Monday"].iloc[0]
    tue_stats = wk_df[wk_df["Day of Week"] == "Tuesday"].iloc[0]

    assert mon_stats["Sample Size (n)"] == 2
    assert pytest.approx(mon_stats["Avg Return (%)"], 0.001) == 0.0
    assert pytest.approx(mon_stats["Positive Days (%)"], 0.001) == 50.0
    assert pytest.approx(mon_stats["Negative Days (%)"], 0.001) == 50.0

    assert tue_stats["Sample Size (n)"] == 1
    assert pytest.approx(tue_stats["Avg Return (%)"], 0.001) == 2.0
    assert pytest.approx(tue_stats["Positive Days (%)"], 0.001) == 100.0


def test_probability_frequencies():
    # 10 returns: 6 positive, 3 negative, 1 zero; 2 moves > 1.0%
    rets = pd.Series([1.5, 2.0, 0.5, 0.2, 0.1, 0.8, -0.4, -0.8, -1.2, 0.0])
    freq_df = compute_probability_frequencies(rets, thresholds=[1.0])
    
    pos_row = freq_df[freq_df["Condition / Event"].str.contains("Positive Return")].iloc[0]
    neg_row = freq_df[freq_df["Condition / Event"].str.contains("Negative Return")].iloc[0]
    th_row = freq_df[freq_df["Condition / Event"].str.contains("1.00%")].iloc[0]

    assert pos_row["Occurrences (Count)"] == 6
    assert pytest.approx(pos_row["Historical Frequency (%)"], 0.001) == 60.0

    assert neg_row["Occurrences (Count)"] == 3
    assert pytest.approx(neg_row["Historical Frequency (%)"], 0.001) == 30.0

    # |Move| > 1.0%: 1.5, 2.0, -1.2 -> 3 moves
    assert th_row["Occurrences (Count)"] == 3
    assert pytest.approx(th_row["Historical Frequency (%)"], 0.001) == 30.0
