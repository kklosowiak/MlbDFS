import json

with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

for h in data['hitters']:
    if 'Busch' in h['name']:
        print(f"Hitter: {h['name']} ({h['team']}) - Alpha: {h.get('player_score', 0):.1f} | xwOBA: {h.get('matchup_xwoba', 0):.3f} | Hot: {h.get('is_hot')} | Target: {h.get('is_juiced_target')}")

for p in data['pitchers']:
    if p['pitcher'] == 'Walker Buehler':
        print(f"Pitcher: {p['pitcher']} ({p['team']}) - Alpha: {p.get('alpha_score', 0):.1f} | K-line: {p.get('k_line')} | CSW: {p.get('csw', 0):.3f}")

for t in data['teams']:
    if t['team'] == 'Chicago Cubs':
        print(f"Stack: {t['team']} - Score: {t.get('stack_score', 0):.1f} | xwOBA: {t.get('team_xwoba', 0):.3f} | Trend: {t.get('trend')} | Sharp: {t.get('is_sharp')}")
