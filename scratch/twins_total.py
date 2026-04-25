import json

with open('data/snapshot_20260417_181227.json', 'r') as f:
    snap = json.load(f)

print("--- CURRENT TOTAL ---")
for o in snap.get('odds', []):
    if 'Minnesota Twins' in [o.get('home_team'), o.get('away_team')]:
        print(f"Current Total: {o.get('total')}")

print("--- OPENING TOTAL ---")
try:
    with open('data/opening_lines.json', 'r') as f:
        open_data = json.load(f)
        for g in open_data:
            if 'Minnesota Twins' in [g.get('team_home'), g.get('team_away')]:
                print(f"Opening Total: {g.get('opening_total')}")
except Exception as e:
    print(f"Error reading opening lines: {e}")
