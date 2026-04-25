import json

with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

teams = ['Tampa Bay Rays', 'Pittsburgh Pirates', 'Chicago White Sox', 'Athletics', 'San Francisco Giants', 'Washington Nationals', 'Milwaukee Brewers', 'Miami Marlins', 'Detroit Tigers', 'Boston Red Sox']

print('--- TOP SPs FOR 4:05PM SLATE ---')
for p in sorted(data.get('pitchers', []), key=lambda x: x.get('alpha_score', 0), reverse=True):
    if p.get('team') in teams:
        print(f"{p.get('pitcher')} ({p.get('team')}): {p.get('alpha_score', 0)} Alpha - Weather: {p.get('weather_label', '')}")

print('\n--- TOP STACKS FOR 4:05PM SLATE ---')
for t in sorted(data.get('teams', []), key=lambda x: x.get('stack_score', 0), reverse=True):
    if t.get('team') in teams:
        sp = t.get('opp_pitcher', 'Unknown')
        print(f"{t.get('team')}: {t.get('stack_score', 0):.1f} Stack Score - Opp SP: {sp}")

print('\n--- TOP HITTER PROPS ---')
hitters = [h for h in data.get('hitters', []) if h.get('team') in teams]
for h in sorted(hitters, key=lambda x: x.get('hitter_alpha', 0), reverse=True)[:10]:
    print(f"{h.get('name')} ({h.get('team')}): {h.get('hitter_alpha', 0):.1f} Alpha - Matchup: {h.get('opp_pitcher_name')} - TB Odds: {h.get('tb_odds')}")
