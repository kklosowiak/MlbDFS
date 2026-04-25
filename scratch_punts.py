import json

with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

hitters = data.get('hitters', [])
targets = ['Josh Naylor', 'Chase Meidroth', 'Escarra', 'J.C. Escarra', 'JC Escarra']

with open('scratch_punts_out.txt', 'w', encoding='utf-8') as out:
    for h in hitters:
        if any(t.lower() in h['name'].lower() for t in targets):
            out.write(f"{h['name']} ({h['team']}): Score {h['player_score']}, xwOBA {h['matchup_xwoba']}, Hot: {h['is_hot']}\n")
