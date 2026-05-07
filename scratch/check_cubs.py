import json
with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

print('CUBS LINEUP:')
cubs_hitters = [h for h in data['hitters'] if h['team'] == 'Chicago Cubs']
cubs_hitters.sort(key=lambda x: x.get('player_score', 0), reverse=True)

for h in cubs_hitters:
    flags = []
    if h.get('is_hot'): flags.append('HOT')
    if h.get('is_juiced_target'): flags.append('TARGET')
    flag_str = ','.join(flags)
    print(f"{h['name']} - Alpha: {h.get('player_score',0):.1f} | xwOBA: {h.get('matchup_xwoba',0):.3f} | {flag_str}")
