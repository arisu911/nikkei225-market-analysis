"""
Unit tests for TSE market session classification and filtering in MYT.
"""

import datetime
import pytest
import pandas as pd
from src.market_sessions import (
    classify_session_segment,
    filter_tse_sessions,
    get_morning_session_bars,
    get_afternoon_session_bars,
    get_opening_window_bars,
)


def test_classify_session_segment():
    assert classify_session_segment(datetime.time(8, 0)) == "Morning"
    assert classify_session_segment(datetime.time(9, 30)) == "Morning"
    assert classify_session_segment(datetime.time(10, 30)) == "Morning"
    assert classify_session_segment(datetime.time(11, 0)) == "Lunch"
    assert classify_session_segment(datetime.time(11, 30)) == "Afternoon"
    assert classify_session_segment(datetime.time(13, 0)) == "Afternoon"
    assert classify_session_segment(datetime.time(14, 30)) == "Afternoon"
    assert classify_session_segment(datetime.time(7, 45)) == "Off-Session"
    assert classify_session_segment(datetime.time(15, 0)) == "Off-Session"


def test_filter_tse_sessions_excludes_lunch_and_offhours():
    times = pd.date_range("2026-08-25 07:30", "2026-08-25 15:00", freq="15min", tz="Asia/Kuala_Lumpur")
    df = pd.DataFrame({"Close": range(len(times))}, index=times)
    
    filtered = filter_tse_sessions(df, include_lunch=False)
    
    # 07:30, 07:45 should not be in filtered
    assert datetime.time(7, 30) not in filtered.index.time
    assert datetime.time(7, 45) not in filtered.index.time
    
    # 10:45, 11:00, 11:15 (Lunch) should not be in filtered
    assert datetime.time(10, 45) not in filtered.index.time
    assert datetime.time(11, 0) not in filtered.index.time
    assert datetime.time(11, 15) not in filtered.index.time
    
    # 14:45, 15:00 should not be in filtered
    assert datetime.time(14, 45) not in filtered.index.time
    assert datetime.time(15, 0) not in filtered.index.time
    
    # 08:00 and 11:30 MUST be present
    assert datetime.time(8, 0) in filtered.index.time
    assert datetime.time(11, 30) in filtered.index.time
    assert datetime.time(14, 30) in filtered.index.time


def test_morning_and_afternoon_extraction():
    times = pd.date_range("2026-08-25 08:00", "2026-08-25 14:30", freq="30min", tz="Asia/Kuala_Lumpur")
    df = pd.DataFrame({"Close": range(len(times))}, index=times)
    
    morning = get_morning_session_bars(df)
    afternoon = get_afternoon_session_bars(df)
    
    assert all(t <= datetime.time(10, 30) for t in morning.index.time)
    assert all(t >= datetime.time(11, 30) for t in afternoon.index.time)


def test_opening_window_extraction():
    times = pd.date_range("2026-08-25 08:00", "2026-08-25 14:30", freq="5min", tz="Asia/Kuala_Lumpur")
    df = pd.DataFrame({"Close": range(len(times))}, index=times)
    
    op_30m = get_opening_window_bars(df, minutes=30)
    assert op_30m.index[0].time() == datetime.time(8, 0)
    assert op_30m.index[-1].time() == datetime.time(8, 30)
    assert len(op_30m) == 7 # 08:00, 08:05, 08:10, 08:15, 08:20, 08:25, 08:30
