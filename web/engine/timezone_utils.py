"""
Timezone Conversion and Normalization Utilities for Nikkei 225 Market Analysis.
Strictly ensures timezone-aware timestamps converted from JST (UTC+9) / UTC to MYT (UTC+8).
"""

from typing import Union
import pandas as pd
import pytz
import datetime
from config.settings import SOURCE_TIMEZONE, DISPLAY_TIMEZONE


MYT_TZ = pytz.timezone(DISPLAY_TIMEZONE)
JST_TZ = pytz.timezone(SOURCE_TIMEZONE)
UTC_TZ = pytz.UTC


def is_timezone_aware(obj: Union[datetime.datetime, pd.Timestamp, pd.DatetimeIndex]) -> bool:
    """Check if a datetime, Timestamp, or DatetimeIndex is timezone-aware."""
    if isinstance(obj, pd.DatetimeIndex):
        return obj.tz is not None
    elif isinstance(obj, (pd.Timestamp, datetime.datetime)):
        return obj.tzinfo is not None and obj.tzinfo.utcoffset(obj) is not None
    return False


def ensure_timezone_aware(
    dt_index: pd.DatetimeIndex,
    assumed_tz: str = SOURCE_TIMEZONE
) -> pd.DatetimeIndex:
    """
    Ensure a DatetimeIndex is timezone-aware.
    If naive, localize to assumed_tz; if aware, keep as is.
    """
    if dt_index.tz is None:
        return dt_index.tz_localize(assumed_tz)
    return dt_index


def to_myt(
    data: Union[pd.DataFrame, pd.Series, pd.DatetimeIndex, pd.Timestamp, datetime.datetime],
    source_tz: str = SOURCE_TIMEZONE
) -> Union[pd.DataFrame, pd.Series, pd.DatetimeIndex, pd.Timestamp, datetime.datetime]:
    """
    Convert a timezone-aware or naive datetime object, Series, or DataFrame index to Malaysia Time (MYT, UTC+8).
    Uses proper timezone conversions rather than naive offset subtraction.
    """
    if isinstance(data, pd.DataFrame):
        df = data.copy()
        if isinstance(df.index, pd.DatetimeIndex):
            if df.index.tz is None:
                df.index = df.index.tz_localize(source_tz).tz_convert(DISPLAY_TIMEZONE)
            else:
                df.index = df.index.tz_convert(DISPLAY_TIMEZONE)
        return df

    elif isinstance(data, pd.Series):
        s = data.copy()
        if isinstance(s.index, pd.DatetimeIndex):
            if s.index.tz is None:
                s.index = s.index.tz_localize(source_tz).tz_convert(DISPLAY_TIMEZONE)
            else:
                s.index = s.index.tz_convert(DISPLAY_TIMEZONE)
        elif pd.api.types.is_datetime64_any_dtype(s):
            if s.dt.tz is None:
                s = s.dt.tz_localize(source_tz).dt.tz_convert(DISPLAY_TIMEZONE)
            else:
                s = s.dt.tz_convert(DISPLAY_TIMEZONE)
        return s

    elif isinstance(data, pd.DatetimeIndex):
        if data.tz is None:
            return data.tz_localize(source_tz).tz_convert(DISPLAY_TIMEZONE)
        return data.tz_convert(DISPLAY_TIMEZONE)

    elif isinstance(data, (pd.Timestamp, datetime.datetime)):
        if isinstance(data, datetime.datetime) and not isinstance(data, pd.Timestamp):
            data = pd.Timestamp(data)
        if data.tzinfo is None:
            return data.tz_localize(source_tz).tz_convert(DISPLAY_TIMEZONE)
        return data.tz_convert(DISPLAY_TIMEZONE)

    return data


def format_myt_timestamp(dt: Union[pd.Timestamp, datetime.datetime], include_time: bool = True) -> str:
    """Format a timestamp into standard MYT string."""
    if dt is None:
        return "N/A"
    dt_myt = to_myt(dt)
    if include_time:
        return dt_myt.strftime("%Y-%m-%d %H:%M:%S MYT")
    return dt_myt.strftime("%Y-%m-%d")


def get_session_date_myt(dt: Union[pd.Timestamp, datetime.datetime]) -> datetime.date:
    """Return the date in MYT for any given timestamp."""
    dt_myt = to_myt(dt)
    return dt_myt.date()
