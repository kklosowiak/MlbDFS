import requests
from datetime import datetime
import os
import sys

# Add current dir to path for imports
sys.path.append(os.getcwd())

from utils.normalization import normalize_player_name

api_url = "https://statsapi.mlb.com/api/v1/schedule"
params = {
    'sportId': 1,
    'date': '2026-04-26',
    'hydrate': 'lineups'
}

response = requests.get(api_url, params=params)
data = response.json()

for date in data.get('dates', []):
    for game in date.get('games', []):
        home_team = game['teams']['home']['team']['name']
        away_team = game['teams']['away']['team']['name']
        print(f"Game: {away_team} @ {home_team}")
        lineups = game.get('lineups', {})
        for side in ['away', 'home']:
            team_name = game['teams'][side]['team']['name']
            players = lineups.get(f'{side}Players', [])
            print(f"  {team_name} Lineup:")
            for i, p in enumerate(players):
                print(f"    {i+1}. {p['fullName']}")
