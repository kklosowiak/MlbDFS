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

print("--- SHARP TOTALS (OVERS & UNDERS) ---")
games = {} # Keep track by matchup to avoid printing twice
for t in results['teams']:
    if t['team'] in night_teams:
        game_id_tuple = tuple(sorted([t['team'], t['opponent']]))
        if game_id_tuple not in games:
            games[game_id_tuple] = {
                'matchup': f"{t['team']} vs {t['opponent']}",
                'tt_move': t['tt_move'],
                'is_sharp': t['is_sharp'],
                'is_storm': t.get('is_storm', False),
                'divergence': t['divergence']
            }
        else:
            if t['is_sharp'] and not games[game_id_tuple]['is_sharp']:
                games[game_id_tuple]['is_sharp'] = True
            
            if t['is_storm']:
                games[game_id_tuple]['is_storm'] = True

for game, data in games.items():
    direction = "OVER" if data['tt_move'] > 0 else ("UNDER" if data['tt_move'] < 0 else "FLAT")
    sharpness = "SHARP ACTION" if data['is_sharp'] else ""
    storm = "PERFECT STORM" if data['is_storm'] else ""
    print(f"{data['matchup']}: Move: {data['tt_move']} ({direction}) | Div: {data['divergence']}% | {sharpness} {storm}")
