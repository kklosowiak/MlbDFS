import json

with open('data/snapshot_20260417_150219.json', 'r') as f:
    data = json.load(f)

print("GAME TIMES:")
for odds in data['odds']:
    print(odds['commence_time'], odds['home_team'], "vs", odds['away_team'])
