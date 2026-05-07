import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = json.load(open('reports/latest_results.json', encoding='utf-8'))

print('=== PITCHER MATRIX ===')
for p in d['pitchers']:
    flags = []
    if p.get('is_paradox'): flags.append('PARADOX')
    if p.get('is_hazard'): flags.append('HAZARD')
    if p.get('is_debut'): flags.append('DEBUT')
    if p.get('is_coors'): flags.append('COORS')
    if p.get('is_low_ceiling'): flags.append('LOW-K')
    flag_str = ' [' + ', '.join(flags) + ']' if flags else ''
    print(f'{p["alpha_score"]:6.1f}  Phys:{p["physics_score"]:5.1f}  Mkt:{p["market_score"]:5.1f}  {p["pitcher"]:22s} ({p["team"]:25s}) vs {p["opponent"]:25s} K:{p.get("k_line","-")} Outs:{p.get("outs_line","-")}{flag_str}')

print()
print('=== TEAMS MATRIX ===')
for t in d['teams']:
    flags = []
    if t.get('is_shark'): flags.append('SHARK')
    if t.get('is_whale'): flags.append('WHALE')
    if t.get('is_sharp'): flags.append('SHARP')
    if t.get('is_storm'): flags.append('STORM')
    if t.get('is_steam'): flags.append('STEAM')
    if t.get('is_burst'): flags.append('BURST')
    if t.get('is_gassed'): flags.append('GASSED')
    if t.get('trend') and t['trend'] != 'STABLE': flags.append(t['trend'])
    flag_str = ' [' + ', '.join(flags) + ']' if flags else ''
    print(f'{t["stack_score"]:6.1f}  Phys:{t["physics_score"]:5.1f}  Mkt:{t["market_score"]:5.1f}  xwOBA:{t["team_xwoba"]:.3f}  ML:{t["ml_move"]:+.1f}  TT:{t["tt_move"]:+.1f}  Div:{t["divergence"]:+.0f}  ITT:{t["implied_total"]:.2f}  {t["team"]:25s} vs {t["opp_pitcher"]:22s} ({t["opponent"]:25s}) BP:{t["bullpen_fatigue"]} {t.get("total_signal","")}{flag_str}')

print()
print('=== HITTER MATRIX (Top 20) ===')
for h in d['hitters'][:20]:
    flags = []
    if h.get('is_hot'): flags.append('HOT')
    if h.get('is_juiced_target'): flags.append('JUICED')
    if h.get('is_speed_target'): flags.append('SPEED')
    flag_str = ' [' + ', '.join(flags) + ']' if flags else ''
    print(f'{h["player_score"]:6.1f}  Phys:{h["physics_score"]:5.1f}  Mkt:{h["market_score"]:5.1f}  xwOBA:{h["matchup_xwoba"]:.3f}  AHR:{h["ahr_price"]:+5d}  {h["name"]:22s} ({h["team"]:25s}) vs {h["opp_pitcher"]:22s} Hit:{h.get("hit_line","-")}@{h.get("hits_price",0)}{flag_str}')
