import json

with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for h in data.get('hitters', []):
    if h['team'] == 'Los Angeles Angels' and 'Peraza' in h['name']:
        print(f"{h['name']}: Score {h['player_score']}, xwOBA {h['matchup_xwoba']}, Hot: {h['is_hot']}, Juiced: {h['is_juiced_target']}")
