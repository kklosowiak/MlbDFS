import json
with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)
for h in data['hitters']:
    if 'House' in h['name']:
        flags = []
        if h.get('is_hot'): flags.append('HOT')
        if h.get('is_juiced_target'): flags.append('TARGET')
        flag_str = ','.join(flags)
        print(f"{h['name']} ({h['team']}) - Alpha: {h.get('player_score',0):.1f} | xwOBA: {h.get('matchup_xwoba',0):.3f} | {flag_str}")
