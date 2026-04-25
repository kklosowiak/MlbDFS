import sys; sys.stdout.reconfigure(encoding='utf-8')
import json
with open('reports/latest_results.json', encoding='utf-8') as f:
    data = json.load(f)

for team_name in ['Cleveland Guardians', 'Baltimore Orioles']:
    team = next((t for t in data['teams'] if team_name in t['team']), None)
    if team:
        print(f"{team['team']} | Omega: {team['stack_score']} | Physics: {team['physics_score']} | Market: {team['market_score']} | ITT: {team['implied_total']} | Trend: {team['trend']}")
