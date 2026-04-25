import json

with open('reports/latest_results.json', 'r') as f:
    results = json.load(f)

# Teams playing at 23:05 UTC (7:05pm EST) or later
night_teams = [
    "New York Yankees", "Kansas City Royals",
    "Miami Marlins", "Milwaukee Brewers",
    "Boston Red Sox", "Detroit Tigers",
    "Minnesota Twins", "Cincinnati Reds",
    "Houston Astros", "St. Louis Cardinals",
    "Colorado Rockies", "Los Angeles Dodgers",
    "Los Angeles Angels", "San Diego Padres",
    "Arizona Diamondbacks", "Toronto Blue Jays",
    "Athletics", "Chicago White Sox",
    "Seattle Mariners", "Texas Rangers"
]

print("--- NIGHT PITCHERS (TOP 8) ---")
pitchers = [p for p in results['pitchers'] if p['team'] in night_teams]
pitchers.sort(key=lambda x: x['alpha_score'], reverse=True)
for p in pitchers[:8]:
    print(f"{p['pitcher']} ({p['team']}) - Alpha: {p['alpha_score']} | Div: {p['divergence']}% | Sharp: {p['is_juiced_target']} | ML Move: {p['ml_move']}")

print("\n--- NIGHT STACKS (TOP 8) ---")
stacks = [t for t in results['teams'] if t['team'] in night_teams]
for t in stacks[:8]:
    print(f"{t['team']} - Score: {t['stack_score']} | Div: {t['divergence']}% ({t['trend']}) | Sharp: {t['is_sharp']} | ML Move: {t['ml_move']}")

print("\n--- NIGHT HITTERS (TOP 10) ---")
hitters = [h for h in results['hitters'] if h['team'] in night_teams]
for h in hitters[:10]:
    print(f"{h['name']} ({h['team']}) - Score: {h['player_score']} | Hot: {h['is_hot']} | Sharp: {h['is_juiced_target']}")
