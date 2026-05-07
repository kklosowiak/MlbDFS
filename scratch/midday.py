import json

with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

print('--- TOP 5 PITCHERS ---')
for p in data.get('pitchers', [])[:5]:
    flags = []
    if p.get('is_debut'): flags.append('DEBUT')
    if p.get('is_paradox'): flags.append('PARADOX')
    if p.get('is_hazard'): flags.append('HAZARD')
    print(f"{p['pitcher']} ({p['team']}) - Alpha: {p.get('alpha_score', 0):.1f} | K-line: {p.get('k_line', '-')} | Flags: {','.join(flags)}")

print('\n--- TOP 5 TEAMS (STACKS) ---')
for t in data.get('teams', [])[:5]:
    flags = []
    if t.get('is_shark'): flags.append('SHARK')
    if t.get('is_steam'): flags.append('STEAM')
    if t.get('is_storm'): flags.append('STORM')
    if t.get('is_whale'): flags.append('WHALE')
    if t.get('is_sharp'): flags.append('SHARP')
    print(f"{t['team']} vs {t.get('opp_pitcher')} - Score: {t.get('stack_score', 0):.1f} | xwOBA: {t.get('team_xwoba', 0):.3f} | Trend: {t.get('trend')} | Flags: {','.join(flags)}")

print('\n--- TOP 5 HITTERS ---')
for h in data.get('hitters', [])[:5]:
    flags = []
    if h.get('is_hot'): flags.append('HOT')
    if h.get('is_juiced_target'): flags.append('TARGET')
    print(f"{h['name']} ({h['team']}) - Alpha: {h.get('player_score', 0):.1f} | xwOBA: {h.get('matchup_xwoba', 0):.3f} | Flags: {','.join(flags)}")
