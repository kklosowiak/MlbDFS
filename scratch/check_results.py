import json
with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

print('--- LOW CONFIDENCE PITCHERS ---')
for p in data.get('pitchers', []):
    if p.get('confidence') == 'low' or p.get('pitcher') == 'TBD' or 'Yesavage' in p.get('pitcher', ''):
        print(f"{p['pitcher']} ({p['team']}) - Confidence: {p.get('confidence', 'N/A')} - Score: {p.get('alpha_score')}")

print('\n--- TOP 5 TEAMS (Market Boost Check) ---')
for i, t in enumerate(data.get('teams', [])[:5]):
    print(f"{i+1}. {t['team']} - Score: {t['stack_score']} - xwOBA: {t.get('team_xwoba', 0):.3f} - Shark: {t.get('is_shark')} - Steam: {t.get('is_steam')} - Divergence: {t.get('divergence')}")
