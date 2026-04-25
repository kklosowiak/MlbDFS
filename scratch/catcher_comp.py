import json

with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

print("--- PLAYER COMPARISON ---")
for h in data.get('hitters', []):
    if 'Hunter Goodman' in h.get('name') or 'Realmuto' in h.get('name'):
        print(f"Name: {h.get('name')}")
        print(f"Team: {h.get('team')}")
        print(f"Alpha: {h.get('player_score')}")
        print(f"xwOBA: {h.get('matchup_xwoba')}")
        print(f"Juiced: {h.get('is_juiced_target')}")
        print("-" * 20)
