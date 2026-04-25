import json

with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

# Teams for the 4:05pm slate
teams = ['Tampa Bay Rays', 'Pittsburgh Pirates', 'Chicago White Sox', 'Athletics', 'San Francisco Giants', 'Washington Nationals', 'Milwaukee Brewers', 'Miami Marlins', 'Detroit Tigers', 'Boston Red Sox']

print('--- UPDATED STACKS (4:05PM SLATE) ---')
for t in sorted(data.get('teams', []), key=lambda x: x.get('stack_score', 0), reverse=True):
    if t.get('team') in teams:
        sp = t.get('opp_pitcher', 'Unknown')
        print(f"{t.get('team')}: {t.get('stack_score', 0):.1f} Stack Score | Move: {t.get('ml_move', 0)} ML | Div: {t.get('divergence', 0)} | Trend: {t.get('trend')} | Opp SP: {sp}")

print('\n--- UPDATED PITCHERS (4:05PM SLATE) ---')
for p in sorted(data.get('pitchers', []), key=lambda x: x.get('alpha_score', 0), reverse=True):
    if p.get('team') in teams:
        print(f"{p.get('pitcher')} ({p.get('team')}): {p.get('alpha_score', 0):.1f} Alpha | Move: {p.get('ml_move', 0)} ML | Div: {p.get('divergence', 0)}")
