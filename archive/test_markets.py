import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ODDS_API_KEY")
event_id = "7852034521d5a37d9d67116eba334699" # CIN @ MIA

markets_to_test = [
    "pitcher_strikeouts",
    "player_strikeouts",
    "batter_home_runs",
    "player_home_runs",
    "batter_hits",
    "batter_total_bases",
    "pitcher_outs"
]

print(f"Testing markets for event {event_id}...")

for m in markets_to_test:
    url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{event_id}/odds"
    params = {
        'apiKey': api_key,
        'regions': 'us',
        'markets': m,
        'bookmakers': 'draftkings,fanduel'
    }
    resp = requests.get(url, params=params)
    print(f"Market: {m:20} | Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        bm = data.get('bookmakers', [])
        print(f"  - SUCCESS: Found {len(bm)} bookmakers with this market.")
