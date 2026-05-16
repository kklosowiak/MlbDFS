import json
import os

snapshot_path = "data/snapshot_20260515_170958.json"
with open(snapshot_path, 'r') as f:
    snapshot = json.load(f)

print("--- CONFIRMED LINEUPS (5:22 PM ET) ---")
for team, players in snapshot.get('rosters', {}).items():
    # Sort by order if available
    lineup = [p for p in players if p.get('order')]
    if lineup:
        lineup.sort(key=lambda x: x['order'])
        print(f"\n[{team}]:")
        for p in lineup:
            print(f"  {p['order']}. {p['name']} ({p['position']})")
    else:
        print(f"\n[{team}]: No confirmed lineup found in snapshot.")
