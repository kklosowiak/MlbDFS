from pybaseball import pitching_stats, playerid_lookup, statcast_pitcher
from datetime import datetime
import pandas as pd

def test_pybaseball():
    print("Testing pybaseball.pitching_stats(2026)...")
    try:
        df = pitching_stats(2026, qual=0)
        if df is not None and not df.empty:
            print(f"SUCCESS: pitching_stats(2026) returned {len(df)} rows.")
            print(df.head())
        else:
            print("FAILURE: pitching_stats(2026) returned empty DataFrame.")
    except Exception as e:
        print(f"ERROR: pitching_stats(2026) failed: {e}")

    print("\nTesting playerid_lookup('Kershaw', 'Clayton')...")
    try:
        p_info = playerid_lookup('Kershaw', 'Clayton')
        if not p_info.empty:
            print("SUCCESS: playerid_lookup found Kershaw.")
            print(p_info)
            p_id = p_info.at[0, 'key_mlbam']
            
            print(f"\nTesting statcast_pitcher for ID {p_id}...")
            data = statcast_pitcher('2024-03-20', '2026-04-17', player_id=p_id)
            if not data.empty:
                print(f"SUCCESS: statcast_pitcher returned {len(data)} rows.")
            else:
                print("FAILURE: statcast_pitcher returned empty.")
        else:
            print("FAILURE: playerid_lookup returned empty.")
    except Exception as e:
        print(f"ERROR: playerid_lookup or statcast_pitcher failed: {e}")

if __name__ == "__main__":
    test_pybaseball()
