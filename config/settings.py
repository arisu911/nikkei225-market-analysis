"""
Nikkei 225 Market Behavior Research Configuration Settings
All timezone, TSE market session, instrument, and analysis parameters are defined here.
"""

from pathlib import Path
import datetime

# ==========================================
# Paths Configuration
# ==========================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
CACHE_DATA_DIR = DATA_DIR / "cache"

# Ensure directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DATA_DIR.mkdir(parents=True, exist_ok=True)

# ==========================================
# Timezone Configuration
# ==========================================
SOURCE_TIMEZONE = "Asia/Tokyo"        # JST (UTC+9)
DISPLAY_TIMEZONE = "Asia/Kuala_Lumpur" # MYT (UTC+8)

# ==========================================
# TSE Regular Cash Market Sessions (in MYT: UTC+8)
# ==========================================
# Japan JST: Morning 09:00–11:30, Lunch 11:30–12:30, Afternoon 12:30–15:30
# Malaysia MYT: Morning 08:00–10:30, Lunch 10:30–11:30, Afternoon 11:30–14:30
TSE_SESSIONS_MYT = {
    "morning_open": datetime.time(8, 0),
    "morning_close": datetime.time(10, 30),
    "lunch_start": datetime.time(10, 30),
    "lunch_end": datetime.time(11, 30),
    "afternoon_open": datetime.time(11, 30),
    "afternoon_close": datetime.time(14, 30),
}

# String representations for display
MORNING_SESSION_LABEL = "Morning Session (08:00 - 10:30 MYT)"
AFTERNOON_SESSION_LABEL = "Afternoon Session (11:30 - 14:30 MYT)"
LUNCH_BREAK_LABEL = "Lunch Break (10:30 - 11:30 MYT - Excluded)"

# ==========================================
# Standard Intraday Time Buckets (MYT)
# ==========================================
STANDARD_TIME_WINDOWS_MYT = [
    ("08:00", "08:05", "Opening 5m"),
    ("08:00", "08:15", "Opening 15m"),
    ("08:00", "08:30", "Opening 30m"),
    ("08:00", "09:00", "Opening 60m"),
    ("08:00", "10:30", "Entire Morning Session"),
    ("11:30", "12:00", "Afternoon Re-open 30m"),
    ("11:30", "12:30", "Afternoon First 60m"),
    ("12:30", "13:00", "Early Afternoon (12:30-13:00)"),
    ("13:00", "13:30", "Mid Afternoon (13:00-13:30)"),
    ("13:30", "14:00", "Late Afternoon (13:30-14:00)"),
    ("14:00", "14:30", "Closing 30m (14:00-14:30)"),
]

OPENING_WINDOWS_MINUTES = [5, 15, 30, 60]

# Supported intraday resolutions
SUPPORTED_RESOLUTIONS = ["5m", "10m", "15m", "30m", "60m"]
DEFAULT_RESOLUTION = "5m"

# ==========================================
# Instruments & Volume Proxy Definitions
# ==========================================
# Primary Index: Price, returns, volatility, range, gaps, MFE, MAE
PRIMARY_INDEX_SYMBOL = "^N225"
PRIMARY_INDEX_NAME = "Nikkei 225 Index (^N225)"

# Linked Tradable Instruments: Volume, Relative Volume, Trading Activity
VOLUME_INSTRUMENTS = {
    "1321.T": {
        "name": "NEXT FUNDS Nikkei 225 ETF (TSE: 1321)",
        "exchange": "Tokyo Stock Exchange (TSE)",
        "currency": "JPY",
        "description": "Nomura NEXT FUNDS Nikkei 225 ETF - Primary TSE tradable volume proxy",
        "default": True,
    },
    "1329.T": {
        "name": "iShares Core Nikkei 225 ETF (TSE: 1329)",
        "exchange": "Tokyo Stock Exchange (TSE)",
        "currency": "JPY",
        "description": "BlackRock iShares Core Nikkei 225 ETF",
        "default": False,
    },
    "NKD=F": {
        "name": "Nikkei 225 Futures USD (CME: NKD)",
        "exchange": "Chicago Mercantile Exchange (CME)",
        "currency": "USD",
        "description": "CME Nikkei 225 Index Futures (US Trading Hours)",
        "default": False,
    },
}

DEFAULT_VOLUME_SYMBOL = "1321.T"

# ==========================================
# Analysis Periods
# ==========================================
ANALYSIS_PERIODS = {
    "1Y": {"days": 365, "label": "1 Year"},
    "3Y": {"days": 365 * 3, "label": "3 Years"},
    "5Y": {"days": 365 * 5, "label": "5 Years"},
    "10Y": {"days": 365 * 10, "label": "10 Years"},
    "Custom": {"days": None, "label": "Custom Date Range"},
}

DEFAULT_PERIOD = "1Y"

# ==========================================
# Statistical Thresholds & Parameters
# ==========================================
DEFAULT_PROBABILITY_THRESHOLDS = [0.25, 0.50, 1.00, 1.50, 2.00] # in percentage %
ROLLING_VOLATILITY_WINDOWS = [20, 60, 120] # in trading sessions

PERCENTILES = [10, 25, 50, 75, 90, 95]
WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
