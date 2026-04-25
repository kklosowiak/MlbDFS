import json

with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

teams = data.get('teams', [])
games = {}
for t in teams:
    team = t['team']
    opp = t['opponent']
    key = tuple(sorted([team, opp]))
    if key not in games:
        games[key] = {}
    games[key][team] = t

with open('scratch_totals_out.txt', 'w', encoding='utf-8') as out:
    for k, v in games.items():
        t_names = list(v.keys())
        t1 = t_names[0]
        t2 = t_names[1] if len(t_names) > 1 else None
        
        t1_data = v[t1]
        t2_data = v.get(t2, {}) if t2 else {}
        
        t1_sig = t1_data.get('total_signal', '')
        t2_sig = t2_data.get('total_signal', '')
        # Prefer the non-empty signal
        total_sig = t1_sig if t1_sig else t2_sig
        
        t1_implied = t1_data.get('implied_total', 0)
        t2_implied = t2_data.get('implied_total', 0)
        game_total = t1_implied + t2_implied
        
        out.write(f"{t1} vs {t2 if t2 else 'Unknown'} | Projected Total: {game_total:.1f} | Signal: {total_sig if total_sig else 'NONE (Balanced)'}\n")
