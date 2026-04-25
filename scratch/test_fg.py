from pybaseball import fg_pitching_data
import pandas as pd

def test_fg_pitching():
    print("Testing fg_pitching_data(2026)...")
    try:
        df = fg_pitching_data(2026)
        if df is not None and not df.empty:
            print(f"SUCCESS: fg_pitching_data return {len(df)} rows.")
            print(df.columns)
        else:
            print("FAILURE: fg_pitching_data returned empty.")
    except Exception as e:
        print(f"ERROR: fg_pitching_data failed: {e}")

if __name__ == "__main__":
    test_fg_pitching()
