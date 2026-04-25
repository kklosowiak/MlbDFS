import json

with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

# Main Slate Teams (7:10 PM EST and later)
# STL @ HOU (23:11), ATL @ PHI (23:16), TEX @ SEA (23:16), TOR @ ARI (00:11), LAD @ COL (00:11), SD @ LAA (01:39)
main_slate_teams = [
    'St. Louis Cardinals', 'Houston Astros', 
    'Atlanta Braves', 'Philadelphia Phillies', 
    'Texas Rangers', 'Seattle Mariners', 
    'Toronto Blue Jays', 'Arizona Diamondbacks', 
    'Los Angeles Dodgers', 'Colorado Rockies', 
    'San Diego Padres', 'Los Angeles Angels'
]

print("--- TOP PITCHERS (Main Slate) ---")
pitchers = [p for p in data.get('pitchers', []) if p.get('team') in main_slate_teams]
for p in sorted(pitchers, key=lambda x: x.get('alpha_score', 0), reverse=True):
    print(f"{p.get('pitcher')} ({p.get('team')}): {p.get('alpha_score', 0):.1f} Alpha | Div: {p.get('divergence', 0)} | ML Move: {p.get('ml_move', 0)}")

print("\n--- TOP STACKS (Main Slate) ---")
teams = [t for t in data.get('teams', []) if t.get('team') in main_slate_teams]
for t in sorted(teams, key=lambda x: x.get('stack_score', 0), reverse=True):
    print(f"{t.get('team')}: {t.get('stack_score', 0):.1f} Stack Score | Div: {t.get('divergence', 0)} | Trend: {t.get('trend')} | Sharp/Whale: {t.get('is_sharp')}/{t.get('is_whale')}")

print("\n--- TOP ONE-OFFS (Main Slate) ---")
hitters = [h for h in data.get('hitters', []) if h.get('team') in main_slate_teams]
for h in sorted(hitters, key=lambda x: x.get('hitter_alpha', 0), reverse=True)[:10]:
    print(f"{h.get('name')} ({h.get('team')}): {h.get('hitter_alpha', 0):.1f} Alpha | Matchup: {h.get('opp_pitcher_name')}")
