import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('reports/latest_results.json', 'r') as f:
    results = json.load(f)

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

print("============ NIGHT PITCHERS (SHARP ACTION) ============")
sharp_pitchers = [p for p in results['pitchers'] if p['is_juiced_target'] and p['team'] in night_teams]
sharp_pitchers.sort(key=lambda x: x['alpha_score'], reverse=True)
for p in sharp_pitchers:
    print(f"{p['pitcher']} ({p['team']}) - Alpha: {p['alpha_score']:.1f} | Div: {p['divergence']}% | ML Move: {p['ml_move']}")

print("\n============ NIGHT TEAMS/STACKS (SHARP ACTION) ============")
sharp_teams = [t for t in results['teams'] if t['is_sharp'] and t['team'] in night_teams]
sharp_teams.sort(key=lambda x: x['stack_score'], reverse=True)
for t in sharp_teams:
    print(f"{t['team']} - Stack Score: {t['stack_score']} | Div: {t['divergence']}% ({t['trend']}) | Opp: {t['opp_pitcher']}")

print("\n============ NIGHT HITTERS (SHARP ACTION / TOP 12) ============")
sharp_hitters = [h for h in results['hitters'] if h['is_juiced_target'] and h['team'] in night_teams]
sharp_hitters.sort(key=lambda x: x['player_score'], reverse=True)
for h in sharp_hitters[:12]:
    status = "HOT 🔥" if h['is_hot'] else "COLD ❄️"
    print(f"{h['name']} ({h['team']}) - Score: {h['player_score']} | Matchup xWOBA: {h.get('matchup_xwoba', 0)} | {status}")
