import requests
import json
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('ODDS_API_KEY')
base_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb"

# Let's take the first upcoming game from the last sync if possible
# Or just fetch upcoming games first
try:
    odds_url = f"{base_url}/odds"
    params = {
        'apiKey': api_key,
        'regions': 'us',
        'markets': 'h2h',
        'oddsFormat': 'american'
    }
    resp = requests.get(odds_url, params=params)
    resp.raise_for_status()
    games = resp.json()
    
    if games:
        target_game = games[0]
        event_id = target_game['id']
        print(f"Testing Event: {target_game['home_team']} vs {target_game['away_team']} ({event_id})")
        
        # Now try to fetch ALL props for this event
        # Note: 'us' region might be limited. Let's try 'us,us2,eu,au' just to see what exists
        event_url = f"{base_url}/events/{event_id}/odds"
        prop_params = {
            'apiKey': api_key,
            'regions': 'us,us2',
            'markets': 'pitcher_strikeouts,player_home_runs,pitcher_outs,player_hits',
            'oddsFormat': 'american'
        }
        prop_resp = requests.get(event_url, params=prop_params)
        print(f"Status Code: {prop_resp.status_code}")
        if prop_resp.status_code == 200:
            print(json.dumps(prop_resp.json(), indent=2))
        else:
            print(f"Error: {prop_resp.text}")
    else:
        print("No games found.")
except Exception as e:
    print(f"Failed: {e}")
