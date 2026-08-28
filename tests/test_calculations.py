"""
Unit tests for quantitative financial calculations (returns, gaps, MFE/MAE, opening ranges).
Tested against manually constructed fixtures.
"""

import datetime
import pytest
import pandas as pd
import numpy as np
from src.calculations import (
    calculate_returns,
    calculate_bar_hl_range,
    calculate_daily_summary_from_intraday,
    calculate_opening_gaps,
    calculate_opening_ranges,
    calculate_rolling_volatility,
)


def test_calculate_returns():
    df = pd.DataFrame({"Close": [100.0, 105.0, 102.0]})
    res = calculate_returns(df, "Close")
    assert np.isnan(res["Return_Pct"].iloc[0])
    assert pytest.approx(res["Return_Pct"].iloc[1], 0.001) == 5.0
    assert pytest.approx(res["Return_Pct"].iloc[2], 0.001) == -2.85714
    assert res["Is_Positive"].iloc[1] == True
    assert res["Is_Negative"].iloc[2] == True


def test_mfe_and_mae_calculation():
    # Day with Open=100, High=108, Low=95, Close=105
    times = pd.date_range("2026-08-25 08:00", "2026-08-25 14:30", freq="30min", tz="Asia/Kuala_Lumpur")
    df = pd.DataFrame({
        "Open": [100.0] + [102.0] * (len(times) - 1),
        "High": [102.0, 108.0] + [103.0] * (len(times) - 2),
        "Low": [99.0, 95.0] + [100.0] * (len(times) - 2),
        "Close": [101.0] * (len(times) - 1) + [105.0],
        "Volume": [1000] * len(times),
    }, index=times)

    summary = calculate_daily_summary_from_intraday(df)
    row = summary.iloc[0]
    
    assert row["Open"] == 100.0
    assert row["High"] == 108.0
    assert row["Low"] == 95.0
    assert row["Close"] == 105.0
    
    # MFE = High - Open = 108 - 100 = 8 (8.0%)
    assert pytest.approx(row["MFE"], 0.001) == 8.0
    assert pytest.approx(row["MFE_Pct"], 0.001) == 8.0
    
    # MAE = Low - Open = 95 - 100 = -5 (-5.0%)
    assert pytest.approx(row["MAE"], 0.001) == -5.0
    assert pytest.approx(row["MAE_Pct"], 0.001) == -5.0
    
    # Return = (105 - 100) / 100 = 5.0%
    assert pytest.approx(row["Return_Pct"], 0.001) == 5.0
    # Range = 108 - 95 = 13.0
    assert pytest.approx(row["Range"], 0.001) == 13.0


def test_opening_gap_and_gap_fill_logic():
    # Day 1: Close = 100
    # Day 2: Open = 105 (Gap Up +5%), Low = 98 (Touches prev close 100 -> FILLED)
    # Day 3: Open = 110 (Gap Up vs Day 2 Close 105), Low = 108 (Does NOT touch 105 -> NOT FILLED)
    # Day 4: Open = 100 (Gap Down vs Day 3 Close 110), High = 112 (Touches prev close 110 -> FILLED)
    dates = pd.to_datetime(["2026-08-20", "2026-08-21", "2026-08-24", "2026-08-25"])
    daily_df = pd.DataFrame({
        "Open": [98.0, 105.0, 110.0, 100.0],
        "High": [102.0, 108.0, 115.0, 112.0],
        "Low": [96.0, 98.0, 108.0, 99.0],
        "Close": [100.0, 105.0, 110.0, 108.0],
    }, index=dates)

    gaps = calculate_opening_gaps(daily_df)
    
    # Day 2 (index 0 in gaps since first row has no prev close)
    assert pytest.approx(gaps.iloc[0]["Gap_Pct"], 0.001) == 5.0
    assert gaps.iloc[0]["Is_Gap_Up"] == True
    assert gaps.iloc[0]["Gap_Filled"] == True # Low 98 <= Prev Close 100

    # Day 3
    assert pytest.approx(gaps.iloc[1]["Gap_Pct"], 0.001) == 4.7619 # (110-105)/105 * 100
    assert gaps.iloc[1]["Gap_Filled"] == False # Low 108 > Prev Close 105

    # Day 4
    assert pytest.approx(gaps.iloc[2]["Gap_Pct"], 0.001) == -9.0909 # (100-110)/110 * 100
    assert gaps.iloc[2]["Is_Gap_Down"] == True
    assert gaps.iloc[2]["Gap_Filled"] == True # High 112 >= Prev Close 110


def test_opening_ranges_and_ratio():
    times = pd.date_range("2026-08-25 08:00", "2026-08-25 14:30", freq="5min", tz="Asia/Kuala_Lumpur")
    df = pd.DataFrame({
        "Open": [100.0] * len(times),
        "High": [100.0] * len(times),
        "Low": [100.0] * len(times),
        "Close": [100.0] * len(times),
        "Volume": [100] * len(times),
    }, index=times)
    
    # Set opening 30m high = 104, low = 98 (Range = 6)
    df.loc[df.index <= "2026-08-25 08:30", "High"] = 104.0
    df.loc[df.index <= "2026-08-25 08:30", "Low"] = 98.0
    # Set afternoon high = 110, low = 95 (Full day Range = 15)
    df.loc[df.index >= "2026-08-25 12:00", "High"] = 110.0
    df.loc[df.index >= "2026-08-25 12:00", "Low"] = 95.0

    or_dict = calculate_opening_ranges(df, windows_minutes=[30])
    or_30 = or_dict[30].iloc[0]
    
    assert or_30["OR_Range"] == 6.0
    assert or_30["Full_Day_Range"] == 15.0
    assert pytest.approx(or_30["OR_Ratio_Pct"], 0.001) == (6.0 / 15.0) * 100.0 # 40%
