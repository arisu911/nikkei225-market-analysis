"""
Unit tests for timezone conversions (JST -> MYT).
"""

import datetime
import pytest
import pandas as pd
import pytz
from src.timezone_utils import to_myt, is_timezone_aware, format_myt_timestamp


def test_jst_to_myt_timestamp_conversion():
    # 09:00 JST on 2026-08-25
    jst_tz = pytz.timezone("Asia/Tokyo")
    jst_dt = jst_tz.localize(datetime.datetime(2026, 8, 25, 9, 0, 0))
    
    myt_dt = to_myt(jst_dt)
    assert myt_dt.hour == 8
    assert myt_dt.minute == 0
    assert str(myt_dt.tzinfo) == "Asia/Kuala_Lumpur"


def test_tse_session_close_conversion():
    # 15:30 JST on 2026-08-25
    jst_tz = pytz.timezone("Asia/Tokyo")
    jst_dt = jst_tz.localize(datetime.datetime(2026, 8, 25, 15, 30, 0))
    
    myt_dt = to_myt(jst_dt)
    assert myt_dt.hour == 14
    assert myt_dt.minute == 30


def test_dataframe_index_timezone_conversion():
    dates = pd.date_range("2026-08-25 09:00", "2026-08-25 15:30", freq="30min", tz="Asia/Tokyo")
    df = pd.DataFrame({"Close": [100.0] * len(dates)}, index=dates)
    
    df_myt = to_myt(df)
    assert str(df_myt.index.tz) == "Asia/Kuala_Lumpur"
    assert df_myt.index[0].hour == 8
    assert df_myt.index[0].minute == 0
    assert df_myt.index[-1].hour == 14
    assert df_myt.index[-1].minute == 30


def test_naive_timestamp_localization():
    # Naive timestamp assumed to be JST
    naive_dt = datetime.datetime(2026, 8, 25, 9, 0, 0)
    myt_dt = to_myt(naive_dt, source_tz="Asia/Tokyo")
    assert myt_dt.hour == 8
    assert myt_dt.minute == 0
