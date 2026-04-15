import os
import sys
import json
from datetime import datetime

# Path setup
sys.path.append(os.getcwd())

from data.weather_fetcher import WeatherFetcher
from data.statcast_bridge import StatcastBridge

def verify_live_data():
    print("="*50)
    print("   OMEGA v6.1: DEEP SYSTEM VERIFICATION (v2)")
    print("="*50)
    
    # 1. Weather Verification
    print("[CHECK 1]: Testing Weather Fetcher (Live API)...")
    wf = WeatherFetcher()
    # Removing icons from print to avoid UnicodeEncodeError in powershell
    w_bal = wf.get_alpha_modifier("Baltimore Orioles")
    w_lad = wf.get_alpha_modifier("Los Angeles Dodgers")
    
    print(f"  - BAL Weather Alpha: {w_bal['label'].encode('ascii', 'ignore').decode()}")
    print(f"  - LAD Weather Alpha: {w_lad['label'].encode('ascii', 'ignore').decode()}")
    
    # 2. Statcast Bridge Verification
    print("\n[CHECK 2]: Testing Statcast Bridge Resilience...")
    sb = StatcastBridge()
    mom = sb.get_player_momentum("Aaron Judge")
    if mom:
        print(f"  - SUCCESS: Statcast Cache responsive (Judge ops: {mom.get('ops')})")
    else:
        print("  - WARNING: Statcast cache missing or pending refresh.")

    # 3. Roster Integrity Check
    print("\n[CHECK 3]: Roster Logic Verification...")
    with open("data/probable_pitchers.json", "r") as f:
        probables = json.load(f)
    print(f"  - Houston Check: {probables.get('Houston Astros')} (Expected: Cody Bolton)")
    print(f"  - Dodgers Check: {probables.get('Los Angeles Dodgers')} (Expected: Roki Sasaki)")
    print(f"  - Brewers Check: {probables.get('Milwaukee Brewers')} (Expected: Brandon Woodruff)")

if __name__ == "__main__":
    verify_live_data()
