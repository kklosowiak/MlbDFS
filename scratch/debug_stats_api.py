import requests
import json

url = "https://statsapi.mlb.com/api/v1/stats"
params = {
    'stats': 'season',
    'group': 'hitting',
    'sportId': 1,
    'season': 2026,
    'limit': 10
}

response = requests.get(url, params=params)
data = response.json()

# Look at the first few splits
if 'stats' in data and data['stats']:
    splits = data['stats'][0].get('splits', [])
    for s in splits:
        print(f"Player: {s.get('player', {}).get('fullName')} | Team: {s.get('team', {}).get('name')}")
