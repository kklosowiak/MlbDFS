import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

d = json.load(open('reports/latest_results.json', encoding='utf-8'))

# Build team lookup
team_map = {t['team']: t for t in d['teams']}

print("=== GAME-BY-GAME BREAKDOWN ===\n")

# Pair teams into games
paired = set()
for t in d['teams']:
    if t['team'] in paired:
        continue
    opp = t['opponent']
    t2 = team_map.get(opp)
    if not t2:
        continue
    paired.add(t['team'])
    paired.add(opp)
    
    # Determine which is higher rated
    fav = t if t['stack_score'] >= t2['stack_score'] else t2
    dog = t2 if fav == t else t
    
    print(f"{'='*80}")
    print(f"  {fav['team']} ({fav['stack_score']:.1f}) vs {dog['team']} ({dog['stack_score']:.1f})")
    print(f"  {fav['opp_pitcher']:20s} vs {dog['opp_pitcher']:20s}")
    print(f"{'='*80}")
    
    for side, label in [(fav, "FAVORED"), (dog, "OPPONENT")]:
        flags = []
        for flag in ['is_shark','is_whale','is_sharp','is_storm','is_steam','is_burst','is_gassed','is_fatigued']:
            if side.get(flag): flags.append(flag.replace('is_','').upper())
        trend = side.get('trend', 'STABLE')
        if trend != 'STABLE': flags.append(trend)
        
        print(f"\n  [{label}] {side['team']}")
        print(f"    Stack: {side['stack_score']:.1f} | Phys: {side['physics_score']:.1f} | Mkt: {side['market_score']:.1f}")
        print(f"    xwOBA: {side['team_xwoba']:.3f} | Power Conc: {side['power_concentration']:.3f}")
        print(f"    ITT: {side['implied_total']:.2f} | ML Move: {side['ml_move']:+.1f} | TT Move: {side['tt_move']:+.1f}")
        print(f"    Divergence: {side['divergence']:+.0f} | Confidence: {side.get('confidence','?')}")
        print(f"    Weather: {side['weather_label']} | Ump: {side['umpire_name']}")
        print(f"    Opp BP Fatigue: {side['bullpen_fatigue']:.1f} {'🔥 GASSED' if side.get('is_gassed') else ''}")
        print(f"    Total Signal: {side.get('total_signal','—')}")
        print(f"    Signals: {', '.join(flags) if flags else 'None'}")
    
    # Find hitters for both sides
    fav_hitters = [h for h in d['hitters'] if h['team'] == fav['team']][:5]
    dog_hitters = [h for h in d['hitters'] if h['team'] == dog['team']][:5]
    
    print(f"\n  Top Hitters ({fav['team']}):")
    for h in fav_hitters:
        flags = []
        if h.get('is_hot'): flags.append('HOT')
        if h.get('is_juiced_target'): flags.append('JUICED')
        if h.get('is_speed_target'): flags.append('SPEED')
        print(f"    {h['player_score']:5.1f}  {h['name']:20s} xwOBA:{h['matchup_xwoba']:.3f} AHR:{h['ahr_price']:+5d} Hit:{h.get('hit_line','-')}@{h.get('hits_price',0)} {' '.join(flags)}")
    
    print(f"\n  Top Hitters ({dog['team']}):")
    for h in dog_hitters:
        flags = []
        if h.get('is_hot'): flags.append('HOT')
        if h.get('is_juiced_target'): flags.append('JUICED')
        if h.get('is_speed_target'): flags.append('SPEED')
        print(f"    {h['player_score']:5.1f}  {h['name']:20s} xwOBA:{h['matchup_xwoba']:.3f} AHR:{h['ahr_price']:+5d} Hit:{h.get('hit_line','-')}@{h.get('hits_price',0)} {' '.join(flags)}")
    
    print()

# Pitcher detailed view
print("\n=== PITCHER DETAILED VIEW ===\n")
for p in d['pitchers']:
    flags = []
    if p.get('is_paradox'): flags.append('PARADOX')
    if p.get('is_hazard'): flags.append('HAZARD')
    if p.get('is_debut'): flags.append('DEBUT')
    if p.get('is_low_ceiling'): flags.append('LOW-K')
    
    # Get opponent stack rating
    opp_stack = team_map.get(p['opponent'], {})
    opp_score = opp_stack.get('stack_score', 0)
    
    print(f"  {p['alpha_score']:6.1f}  {p['pitcher']:22s} ({p['team']})")
    print(f"         vs {p['opponent']} (Stack: {opp_score:.1f})")
    print(f"         Phys:{p['physics_score']:.1f} | Mkt:{p['market_score']:.1f} | K:{p.get('k_line','-')} | Outs:{p.get('outs_line','-')}")
    print(f"         Flags: {', '.join(flags) if flags else 'Clean'}")
    print()
