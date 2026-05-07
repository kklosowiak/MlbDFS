import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = json.load(open('reports/latest_results.json', encoding='utf-8'))

print("=== ALL WSH HITTERS vs David Peterson ===\n")
print(f"{'OMEGA':>6s}  {'Phys':>5s}  {'Mkt':>5s}  {'Player':22s}  {'xwOBA':>6s}  {'AHR':>6s}  {'Hit Line':>10s}  {'Flags'}")
print("-" * 100)

wsh = [h for h in d['hitters'] if h['team'] == 'Washington Nationals']
wsh.sort(key=lambda x: x['player_score'], reverse=True)

for h in wsh:
    flags = []
    if h.get('is_hot'): flags.append('HOT')
    if h.get('is_juiced_target'): flags.append('JUICED')
    if h.get('is_speed_target'): flags.append('SPEED')
    hit_str = f"{h.get('hit_line','-')}@{h.get('hits_price',0)}"
    print(f"{h['player_score']:6.1f}  {h['physics_score']:5.1f}  {h['market_score']:5.1f}  {h['name']:22s}  {h['matchup_xwoba']:.3f}  {h['ahr_price']:+6d}  {hit_str:>10s}  {' '.join(flags)}")

# Also check statcast momentum for WSH hitters
print("\n\n=== STATCAST MOMENTUM (WSH Hitters) ===\n")
from data.statcast_bridge import StatcastBridge
bridge = StatcastBridge('data')
cache = bridge._load_cache()

wsh_names = [h['name'].lower() for h in wsh]
for name, data in cache.items():
    if data.get('type') != 'hitter':
        continue
    # Check if name matches any WSH hitter
    name_lower = name.lower()
    for wh in wsh:
        if wh['name'].lower() in name_lower or name_lower in wh['name'].lower():
            ops = data.get('ops', 0)
            avg = data.get('avg', 0)
            slg = data.get('slg', 0)
            k_rate = data.get('r_k_rate', 0)
            s_k_rate = data.get('s_k_rate', 0)
            hot = "🔥 HOT" if ops > 0.900 else ""
            vision = "👁 VISION" if s_k_rate > 0 and k_rate < (s_k_rate * 0.8) else ""
            print(f"  {wh['name']:22s}  OPS:{ops:.3f}  AVG:{avg:.3f}  SLG:{slg:.3f}  K%:{k_rate:.1f}%  sK%:{s_k_rate:.1f}%  {hot} {vision}")
            break

# Peterson info
print("\n\n=== DAVID PETERSON PROFILE ===\n")
for p in d['pitchers']:
    if 'Peterson' in p['pitcher']:
        print(f"  OMEGA: {p['alpha_score']}")
        print(f"  Physics: {p['physics_score']} | Market: {p['market_score']}")
        print(f"  K: {p.get('k_line','-')} | Outs: {p.get('outs_line','-')}")
        flags = []
        if p.get('is_paradox'): flags.append('PARADOX')
        if p.get('is_hazard'): flags.append('HAZARD')
        if p.get('is_low_ceiling'): flags.append('LOW-K')
        print(f"  Flags: {', '.join(flags)}")
        print(f"  ERA: 5.06 | K: 24 | IP: 26.2")
        break

# Peterson statcast
for name, data in cache.items():
    if 'peterson' in name.lower() and data.get('type') == 'pitcher':
        print(f"\n  Statcast: ERA:{data.get('era','?')} WHIP:{data.get('whip','?')} K/9:{data.get('k9','?')}")
        print(f"  Barrel%: {data.get('barrel_pct','?')} HardHit%: {data.get('hard_hit_pct','?')}")
        break
