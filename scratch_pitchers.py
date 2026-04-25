import json

with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

pitchers = data.get('pitchers', [])
pitchers.sort(key=lambda x: x.get('alpha_score', 0), reverse=True)

with open('scratch_pitchers_out.txt', 'w', encoding='utf-8') as out:
    out.write("--- TOP 10 PITCHERS ---\n")
    for p in pitchers[:10]:
        out.write(f"{p['pitcher']} ({p['team']}): Alpha {p['alpha_score']}, K-Line {p.get('k_line')}, ML Move {p.get('ml_move')}, Juiced: {p.get('is_juiced_target')}\n")
