import json
from datetime import datetime

with open('data/snapshot_20260411_094300.json', 'r') as f:
    d = json.load(f)

odds = d.get('odds', [])
print(f"Total games in snapshot: {len(odds)}")
for g in odds:
    away = g.get('away_team')
    home = g.get('home_team')
    commence_time = g.get('commence_time')
    print(f"{away} @ {home} | {commence_time}")

props = d.get('props', {})
print(f"\nGames with props: {len(props)}")
