import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = json.load(open('reports/latest_results.json', encoding='utf-8'))

print("=== ALL PIT HITTERS vs Andre Pallante ===\n")
print(f"{'OMEGA':>6s}  {'Phys':>5s}  {'Mkt':>5s}  {'Player':22s}  {'xwOBA':>6s}  {'AHR':>6s}  {'Hit Line':>10s}  {'Flags'}")
print("-" * 100)

pit = [h for h in d['hitters'] if h['team'] == 'Pittsburgh Pirates']
pit.sort(key=lambda x: x['player_score'], reverse=True)

for h in pit:
    flags = []
    if h.get('is_hot'): flags.append('HOT')
    if h.get('is_juiced_target'): flags.append('JUICED')
    if h.get('is_speed_target'): flags.append('SPEED')
    hit_str = f"{h.get('hit_line','-')}@{h.get('hits_price',0)}"
    print(f"{h['player_score']:6.1f}  {h['physics_score']:5.1f}  {h['market_score']:5.1f}  {h['name']:22s}  {h['matchup_xwoba']:.3f}  {h['ahr_price']:+6d}  {hit_str:>10s}  {' '.join(flags)}")

print("\n\n=== PALLANTE PROFILE ===")
for p in d['pitchers']:
    if 'Pallante' in p['pitcher']:
        print(f"  OMEGA: {p['alpha_score']} | Phys: {p['physics_score']} | Mkt: {p['market_score']}")
        print(f"  K: {p.get('k_line','-')} | Outs: {p.get('outs_line','-')}")
        print(f"  ERA: 4.26 | Flags: PARADOX, LOW-K")
        print(f"  Facing PIT stack: 96.8 OMEGA (WHALE + SHARP, +19 div)")
        print(f"  STL Bullpen: 100 GASSED")
        break
