import json

with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('scratch_eovaldi_out.txt', 'w', encoding='utf-8') as out:
    out.write("--- PITCHER INFO ---\n")
    for p in data.get('pitchers', []):
        if 'Eovaldi' in p['pitcher']:
            out.write(json.dumps(p, indent=2) + "\n")

    out.write("\n--- ATHLETICS HITTERS ---\n")
    for h in data.get('hitters', []):
        if h['team'] == 'Athletics':
            out.write(f"{h['name']}: Score {h['player_score']}, xwOBA {h['matchup_xwoba']}, is_hot {h['is_hot']}\n")

    out.write("\n--- TEAMS INFO ---\n")
    for t in data.get('teams', []):
        if t['team'] == 'Athletics' or t['team'] == 'Texas Rangers':
            out.write(f"{t['team']}: Bullpen Fatigue {t['bullpen_fatigue']}, Opp Pitcher {t['opp_pitcher']}\n")
