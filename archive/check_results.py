import json

d = json.load(open('reports/latest_results.json'))
print(f"Pitchers: {len(d.get('pitchers', []))}")
print(f"Teams: {len(d.get('teams', []))}")
print(f"Hitters: {len(d.get('hitters', []))}")

print("\n--- TOP PITCHERS ---")
for p in d['pitchers'][:15]:
    signals = []
    if p.get('is_juiced_target'): signals.append('TARGET')
    if p.get('is_shark'): signals.append('SHARK')
    sig_str = ' '.join(signals) if signals else '-'
    print(f"  {p['pitcher']:22s} | {p['team']:25s} | OMEGA: {p['alpha_score']:5.1f} | P:{p.get('physics_score',0):5.1f} M:{p.get('market_score',0):5.1f} | {sig_str}")

print("\n--- TOP TEAMS ---")
for t in d['teams'][:15]:
    signals = []
    if t.get('is_shark'): signals.append('SHARK')
    if t.get('is_gassed'): signals.append('GASSED')
    sig_str = ' '.join(signals) if signals else '-'
    print(f"  {t['team']:25s} vs {t.get('opp_pitcher','TBD'):20s} | OMEGA: {t['stack_score']:5.1f} | ML:{t.get('ml_move',0):+.0f} TT:{t.get('tt_move',0):+.1f} | {sig_str}")

print("\n--- TOP HITTERS ---")
for h in d['hitters'][:15]:
    signals = []
    if h.get('is_juiced_target'): signals.append('TARGET')
    if h.get('is_hot'): signals.append('HOT')
    if h.get('is_speed_target'): signals.append('SPEED')
    sig_str = ' '.join(signals) if signals else '-'
    print(f"  {h['name']:22s} | {h['team']:12s} | OMEGA: {h['player_score']:5.1f} | xwOBA:{h.get('matchup_xwoba',0):.3f} | {sig_str}")
