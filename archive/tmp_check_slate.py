import json, os, glob

snapshot_file = max(glob.glob('data/snapshot_*.json'), key=os.path.getctime)
with open(snapshot_file, 'r') as f:
    data = json.load(f)

for event in data['odds']:
    print(f"{event['home_team']} vs {event['away_team']} - {event['commence_time']}")
