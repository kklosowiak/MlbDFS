import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('ODDS_API_KEY')
base_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb"

event_id = "d52d861ea5ed462b15486ffb7493bbc4" # Pirates vs Padres
print(f"Testing Individual Markets for Event: {event_id}")

markets = ["pitcher_strikeouts", "player_home_runs", "pitcher_outs", "player_hits"]

for m in markets:
    url = f"{base_url}/events/{event_id}/odds"
    params = {
        'apiKey': api_key,
        'regions': 'us',
        'markets': m,
        'oddsFormat': 'american'
    }
    resp = requests.get(url, params=params)
    print(f"Market: {m} | Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"  - SUCCESS: Found data for {len(data.get('bookmakers', []))} bookmakers.")
    else:
        print(f"  - FAILED: {resp.text}")
