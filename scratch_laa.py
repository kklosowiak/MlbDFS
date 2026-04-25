import json

with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

laa_lineup = [
    "Zach Neto", "Mike Trout", "Jo Adell", "Jorge Soler", 
    "Oswald Peraza", "Nolan Schanuel", "Vaughn Grissom", 
    "Logan O'Hoppe", "Bryce Teodosio", "O. Peraza", "N. Schanuel", "V. Grissom", "L. O'Hoppe", "B. Teodosio"
]

with open('scratch_laa_out.txt', 'w', encoding='utf-8') as out:
    for h in data.get('hitters', []):
        if h['team'] == 'Los Angeles Angels':
            # Check if hitter is in lineup, match partials if needed
            matched = any(n.split()[-1].lower() in h['name'].lower() for n in laa_lineup)
            if matched:
                out.write(f"{h['name']}: Score {h['player_score']}, xwOBA {h['matchup_xwoba']}, Hot: {h['is_hot']}, Juiced: {h['is_juiced_target']}\n")

