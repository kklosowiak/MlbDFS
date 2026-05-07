import json
from datetime import datetime

with open('data/snapshot_20260426_124348.json', 'r') as f:
    data = json.load(f)

for game in data.get('odds', []):
    print(f"{game['home_team']} vs {game['away_team']} | {game['commence_time']}")
