import json
with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)
top = sorted(data['teams'], key=lambda x: x.get('stack_score',0), reverse=True)[:5]
for t in top:
    print(f"{t['team']}: {t.get('stack_score',0):.1f} | xwOBA: {t.get('team_xwoba',0):.3f} | {t.get('opp_pitcher')}")
