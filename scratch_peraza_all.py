import json

with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for h in data.get('hitters', []):
    if 'Peraza' in h['name']:
        print(f"{h['name']} ({h['team']}): Score {h['player_score']}")
