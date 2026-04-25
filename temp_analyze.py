import json

with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

with open('temp_out.txt', 'w', encoding='utf-8') as out:
    pitchers = data.get('pitchers', [])
    out.write('--- PITCHERS ---\n')
    for p in pitchers[:5]: # Top 5 pitchers
        out.write(f'{p["pitcher"]}: Alpha {p["alpha_score"]}, ML Move {p["ml_move"]}, Div {p["divergence"]}\n')
        
    teams = data.get('teams', [])
    games = {}
    for t in teams:
        team = t['team']
        opp = t['opponent']
        key = tuple(sorted([team, opp]))
        if key not in games:
            games[key] = {}
        games[key][team] = t
        
    out.write('\n--- GAMES ---\n')
    for k, v in games.items():
        t_names = list(v.keys())
        t1 = t_names[0]
        t2 = t_names[1] if len(t_names) > 1 else None
        
        t1_data = v[t1]
        t2_data = v.get(t2, {}) if t2 else {}
        
        total = t1_data.get('total_signal', '') or t2_data.get('total_signal', '')
        
        out.write(f'\n{t1} vs {t2 if t2 else "Unknown"}\n')
        out.write(f'{t1}: Score {t1_data.get("stack_score")}, Div {t1_data.get("divergence")}, ML {t1_data.get("ml_move")}, Whale {t1_data.get("is_whale")}, Storm {t1_data.get("is_storm")}, Trend {t1_data.get("trend")}\n')
        if t2_data:
            out.write(f'{t2}: Score {t2_data.get("stack_score")}, Div {t2_data.get("divergence")}, ML {t2_data.get("ml_move")}, Whale {t2_data.get("is_whale")}, Storm {t2_data.get("is_storm")}, Trend {t2_data.get("trend")}\n')
        out.write(f'Total Signal: {total}\n')
