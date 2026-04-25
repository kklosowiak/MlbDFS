import json

with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

hitters = data.get('hitters', [])
filtered = [h for h in hitters if h['team'] not in ['Detroit Tigers', 'Cincinnati Reds']]
filtered.sort(key=lambda x: x.get('player_score', 0), reverse=True)

with open('scratch_hitters_out.txt', 'w', encoding='utf-8') as out:
    out.write("--- TOP ONE-OFF HITTERS ---\n")
    for h in filtered[:15]:
        out.write(f"{h['name']} ({h['team']}): Score {h['player_score']}, xwOBA {h['matchup_xwoba']}, Hot: {h['is_hot']}, Juiced: {h['is_juiced_target']}\n")
