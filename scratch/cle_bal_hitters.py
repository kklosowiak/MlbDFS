import sys; sys.stdout.reconfigure(encoding='utf-8')
import json
with open('reports/latest_results.json', encoding='utf-8') as f:
    data = json.load(f)

hitters = [h for h in data['hitters'] if h['team'] in ['Cleveland Guardians', 'Baltimore Orioles']]
for h in sorted(hitters, key=lambda x: x['player_score'], reverse=True)[:5]:
    print(f"{h['name']} ({h['team']}) | Score: {h['player_score']} | Physics: {h['physics_score']} | xwOBA: {h['matchup_xwoba']} | Hot: {h['is_hot']}")
