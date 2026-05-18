import requests
import json
import os
import sys
from datetime import datetime, timedelta, timezone

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import config

if not config.validate():
    print("API Key not found in .env")
    sys.exit(1)

print("="*80)
print("MLB SLATE TIME & DATE DEEP ANALYSIS")
print("="*80)

# Fetch from Odds API
url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events"
params = {
    'apiKey': config.ODDS_API_KEY
}

try:
    response = requests.get(url, params=params)
    response.raise_for_status()
    events = response.json()
    print(f"Total MLB events returned from Odds API: {len(events)}\n")
    
    from zoneinfo import ZoneInfo
    et_tz = ZoneInfo("America/New_York")
    
    now_utc = datetime.now(timezone.utc)
    now_et = now_utc.astimezone(et_tz)
    print(f"Current UTC time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"Current ET time:  {now_et.strftime('%Y-%m-%d %I:%M:%S %p %Z')}\n")
    
    print(f"{'Event ID':<35} | {'Away vs Home':<45} | {'Commence (UTC)':<20} | {'Commence (ET)':<20} | {'Status':<10}")
    print("-"*135)
    
    for e in events:
        c_time = e['commence_time']
        dt_utc = datetime.fromisoformat(c_time.replace('Z', '+00:00'))
        dt_et = dt_utc.astimezone(et_tz)
        
        # Temporal Slate Filter check
        hours_diff = (dt_utc - now_utc).total_seconds() / 3600.0
        
        status = "KEEP"
        if dt_utc < (now_utc - timedelta(hours=1)):
            status = "EXC_PAST"
        elif dt_utc > (now_utc + timedelta(hours=24)):
            status = "EXC_FUTURE"
            
        print(f"{e['id']:<35} | {e['away_team'] + ' @ ' + e['home_team']:<45} | {dt_utc.strftime('%m-%d %H:%M'):<20} | {dt_et.strftime('%m-%d %I:%M %p'):<20} | {status:<10} ({hours_diff:+.1f}h)")
        
except Exception as err:
    print(f"Error querying Odds API: {err}")

print("="*80)
