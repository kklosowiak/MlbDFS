from pybaseball import statcast_pitching, pitching_stats
from datetime import datetime
import pandas as pd

def test_alternatives():
    print("Testing statcast_pitching('2026-04-01', '2026-04-17')...")
    try:
        # statcast_pitching returns a leaderboard for a date range
        df = statcast_pitching('2026-04-01', '2026-04-17')
        if df is not None and not df.empty:
            print(f"SUCCESS: statcast_pitching returned {len(df)} rows.")
            print(df.columns)
            print(df.head())
        else:
            print("FAILURE: statcast_pitching returned empty.")
    except Exception as e:
        print(f"ERROR: statcast_pitching failed: {e}")

    print("\nTesting pitching_stats(2025, qual=0)...")
    try:
        df = pitching_stats(2025, qual=0)
        if df is not None and not df.empty:
            print(f"SUCCESS: pitching_stats(2025) returned {len(df)} rows.")
        else:
            print("FAILURE: pitching_stats(2025) returned empty.")
    except Exception as e:
        print(f"ERROR: pitching_stats(2025) failed: {e}")

if __name__ == "__main__":
    test_alternatives()
