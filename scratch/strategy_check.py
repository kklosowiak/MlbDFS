import json

with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

# Teams in the 4:05pm slate
slate_teams = ['Tampa Bay Rays', 'Pittsburgh Pirates', 'Chicago White Sox', 'Athletics', 'San Francisco Giants', 'Washington Nationals', 'Milwaukee Brewers', 'Miami Marlins', 'Detroit Tigers', 'Boston Red Sox']

print("--- TOP PITCHERS (4:05 PM Slate) ---")
pitchers = [p for p in data.get('pitchers', []) if p.get('team') in slate_teams]
for p in sorted(pitchers, key=lambda x: x.get('alpha_score', 0), reverse=True):
    print(f"{p.get('pitcher')} ({p.get('team')}): {p.get('alpha_score', 0):.1f} Alpha | Div: {p.get('divergence', 0)} | Weather: {p.get('weather_label')}")

print("\n--- TOP STACKS (4:05 PM Slate) ---")
teams = [t for t in data.get('teams', []) if t.get('team') in slate_teams]
for t in sorted(teams, key=lambda x: x.get('stack_score', 0), reverse=True):
    print(f"{t.get('team')}: {t.get('stack_score', 0):.1f} Stack Score | Div: {t.get('divergence', 0)} | Trend: {t.get('trend')} | Sharp/Whale: {t.get('is_sharp')}/{t.get('is_whale')}")

print("\n--- TOP ONE-OFF CANDIDATES (OAK, MIA, WSH) ---")
target_teams = ['Athletics', 'Miami Marlins', 'Washington Nationals']
hitters = [h for h in data.get('hitters', []) if h.get('team') in target_teams]
for h in sorted(hitters, key=lambda x: x.get('hitter_alpha', 0), reverse=True)[:10]:
    print(f"{h.get('name')} ({h.get('team')}): {h.get('hitter_alpha', 0):.1f} Alpha | Opp Pitcher: {h.get('opp_pitcher_name')}")
