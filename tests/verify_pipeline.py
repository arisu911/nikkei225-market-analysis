"""
Verification script for data loader and calculations pipeline.
"""
from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from src.data_loader import YFinanceDataProvider, get_dataset_coverage_report
from src.data_cleaner import validate_and_clean_dataset
from src.calculations import (
    calculate_returns,
    calculate_bar_hl_range,
    calculate_daily_summary_from_intraday,
    calculate_opening_gaps,
    calculate_opening_ranges,
    calculate_morning_vs_afternoon,
    calculate_rolling_volatility,
)
from src.statistics import (
    compute_distribution_metrics,
    compute_weekday_statistics,
    compute_intraday_time_profile,
    compute_probability_frequencies,
    compute_monthly_statistics,
    compute_yearly_statistics,
)

def run_verification():
    print("1. Testing Daily Data Fetch & Clean...")
    provider = YFinanceDataProvider()
    daily_raw = provider.fetch_daily("^N225", period="1y")
    daily_clean, daily_qual = validate_and_clean_dataset(daily_raw, is_intraday=False)
    daily_clean = calculate_returns(daily_clean, "Close")
    daily_clean = calculate_bar_hl_range(daily_clean)
    daily_clean["DayOfWeek"] = daily_clean.index.day_name()
    
    print(f"   Daily clean rows: {len(daily_clean)}, Quality: {daily_qual}")
    
    print("2. Testing Intraday Data Fetch & Clean...")
    intra_raw = provider.fetch_intraday("^N225", interval="5m")
    intra_clean, intra_qual = validate_and_clean_dataset(intra_raw, is_intraday=True, remove_lunch=True)
    print(f"   Intraday clean rows: {len(intra_clean)}, Quality: {intra_qual}")

    print("3. Testing Weekday & Distribution Statistics...")
    wk_stats = compute_weekday_statistics(daily_clean, has_valid_volume=False)
    print(f"   Weekday stats shape: {wk_stats.shape}")

    print("4. Testing Opening Gaps & Opening Ranges...")
    gaps = calculate_opening_gaps(daily_clean, intraday_df=intra_clean)
    print(f"   Gaps calculated: {len(gaps)}")
    if not intra_clean.empty:
        or_dict = calculate_opening_ranges(intra_clean, [5, 15, 30, 60])
        print(f"   Opening ranges: {[k for k in or_dict.keys()]}")

    print("5. Testing Morning vs Afternoon...")
    if not intra_clean.empty:
        m_df, a_df = calculate_morning_vs_afternoon(intra_clean)
        print(f"   Morning rows: {len(m_df)}, Afternoon rows: {len(a_df)}")

    print("6. Testing Intraday Time Profile...")
    if not intra_clean.empty:
        profile = compute_intraday_time_profile(intra_clean, has_valid_volume=False)
        print(f"   Profile rows: {len(profile)}")

    print("7. Testing Probability Frequencies...")
    freq = compute_probability_frequencies(daily_clean["Return_Pct"])
    print(f"   Frequency conditions: {len(freq)}")

    print("ALL PIPELINE STEPS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_verification()
