"""Early Slate Teams Matrix Audit — April 29, 2026
Cross-references today's OMEGA output against yesterday's post-mortem lessons."""

import json
import os

EARLY_SLATE = [
    'Los Angeles Angels', 'Chicago White Sox',
    'Tampa Bay Rays', 'Cleveland Guardians',
    'Seattle Mariners', 'Minnesota Twins',
    'New York Yankees', 'Texas Rangers',
    'Boston Red Sox', 'Toronto Blue Jays',
    'Miami Marlins', 'Los Angeles Dodgers'
]

results = json.load(open('reports/latest_results.json'))

print("=" * 120)
print("  OMEGA EARLY SLATE TEAMS MATRIX — April 29, 2026 (1:00 PM ET)")
print("=" * 120)

teams = [t for t in results['teams'] if t['team'] in EARLY_SLATE]
teams.sort(key=lambda x: x['stack_score'], reverse=True)

for t in teams:
    flags = []
    if t['is_shark']: flags.append('🦈SHARK')
    if t['is_whale']: flags.append('🐋WHALE')
    if t['is_sharp']: flags.append('📐SHARP')
    if t['is_storm']: flags.append('⛈️STORM')
    if t['is_steam']: flags.append('🔥STEAM')
    if t['is_burst']: flags.append('💥BURST')
    if t['trend'] != 'STABLE': flags.append(f"📈{t['trend']}")
    flag_str = ' '.join(flags) if flags else '—'
    
    print(f"\n{'—'*80}")
    print(f"  {t['team']:<25} vs {t['opponent']}")
    print(f"  Stack Score: {t['stack_score']:>6.1f}  |  Physics: {t['physics_score']:>5.1f}  |  Market: {t['market_score']:>5.1f}")
    print(f"  xwOBA: {t['team_xwoba']:.3f}  |  Concentration: {t['power_concentration']:.3f}")
    print(f"  ITT: {t['implied_total']:>5.2f}  |  ML Move: {t['ml_move']:>5.1f}  |  TT Move: {t['tt_move']:>5.2f}")
    print(f"  Divergence: {t['divergence']:>4}  |  Opp Pitcher: {t['opp_pitcher']}")
    print(f"  Bullpen Fatigue: {t['bullpen_fatigue']:.0f}  |  Gassed: {t['is_gassed']}  |  Fatigued: {t['is_fatigued']}")
    print(f"  Weather: {t['weather_label']}  |  Umpire: {t['umpire_name']}")
    print(f"  Signals: {flag_str}")

# ITT Sanity Gate check
print(f"\n{'='*120}")
print("  POST-MORTEM PATCH AUDIT (v7.3 Fixes from 4/28)")
print(f"{'='*120}")

print("\n  [1] ITT Sanity Gate (sub-4.0 ITT + score > 90 = -15% damper):")
for t in teams:
    if t['implied_total'] < 4.0:
        status = "🔴 GATE ACTIVE (dampened)" if t['stack_score'] > 76.5 else "🟢 Low ITT but score already reasonable"
        print(f"      {t['team']:<25} ITT: {t['implied_total']:.2f}  Score: {t['stack_score']:.1f}  — {status}")

no_low_itt = all(t['implied_total'] >= 4.0 for t in teams)
if no_low_itt:
    print("      ✅ No sub-4.0 ITT stacks on this slate. Gate idle.")

# Yesterday's false positive check
print("\n  [2] Yesterday's False Positives — Same Team Repeat Check:")
yesterday_false_positives = {
    'Minnesota Twins': {'score': 102.2, 'runs': 1, 'issue': 'ITT was 3.92, STORM misfired'},
    'Los Angeles Angels': {'score': 80.2, 'runs': 2, 'issue': 'SHARP signal, team underperformed'},
    'Toronto Blue Jays': {'score': 51.8, 'runs': 3, 'issue': 'Low score, still underperformed'},
    'Boston Red Sox': {'score': 56.5, 'runs': 0, 'issue': 'Zeroed out completely'},
    'Miami Marlins': {'score': 72.5, 'runs': 2, 'issue': 'Mid-score, underperformed'},
}
for t in teams:
    if t['team'] in yesterday_false_positives:
        yest = yesterday_false_positives[t['team']]
        print(f"      {t['team']:<25} Yesterday: Score {yest['score']:.1f} → {yest['runs']} runs ({yest['issue']})")
        print(f"      {'':25} Today:     Score {t['stack_score']:.1f} | ITT: {t['implied_total']:.2f}")

# Yesterday's actual winners that were underranked
print("\n  [3] Yesterday's Surprise Winners — Are We Catching Them Today?")
yesterday_surprises = {
    'Chicago White Sox': {'score': 59.2, 'runs': 5, 'lesson': 'Low-ranked but produced. Murakami/Montgomery hit.'},
    'Seattle Mariners': {'score': 58.1, 'runs': 7, 'lesson': 'Bottom-ranked, exploded for 7. Model missed entirely.'},
    'New York Yankees': {'score': 62.9, 'runs': 3, 'lesson': 'Moderate but Schlittler dominated as pitcher.'},
}
for t in teams:
    if t['team'] in yesterday_surprises:
        yest = yesterday_surprises[t['team']]
        print(f"      {t['team']:<25} Yesterday: Score {yest['score']:.1f} → {yest['runs']} runs ({yest['lesson']})")
        print(f"      {'':25} Today:     Score {t['stack_score']:.1f} | xwOBA: {t['team_xwoba']:.3f}")

# Hitter audit for early slate
print(f"\n{'='*120}")
print("  EARLY SLATE TOP HITTERS")
print(f"{'='*120}")

hitters = [h for h in results['hitters'] if h['team'] in EARLY_SLATE]
hitters.sort(key=lambda x: x['player_score'], reverse=True)
for h in hitters[:20]:
    tags = []
    if h['is_hot']: tags.append('🔥HOT')
    if h['is_juiced_target']: tags.append('🎯JUICED')
    if h['is_speed_target']: tags.append('⚡SPEED')
    tag_str = ' '.join(tags) if tags else ''
    print(f"  {h['name']:<22} {h['team']:<22} vs {h['opp_pitcher']:<20} Score: {h['player_score']:>5.1f} | xwOBA: {h['matchup_xwoba']:.3f} | AHR: {h['ahr_price']:>5} {tag_str}")

# Pitchers for early slate
print(f"\n{'='*120}")
print("  EARLY SLATE PITCHERS")
print(f"{'='*120}")

pitchers = [p for p in results['pitchers'] if p['team'] in EARLY_SLATE]
pitchers.sort(key=lambda x: x['alpha_score'], reverse=True)
for p in pitchers:
    flags = []
    if p['is_paradox']: flags.append('⚠️PARADOX')
    if p['is_hazard']: flags.append('🔴HAZARD')
    if p['is_low_ceiling']: flags.append('📉LOW-K')
    if p['is_juiced_target']: flags.append('🎯JUICED')
    flag_str = ' '.join(flags) if flags else ''
    print(f"  {p['pitcher']:<22} {p['team']:<22} Alpha: {p['alpha_score']:>6.1f} | K: {p['k_line']} | Outs: {p['outs_line']} | CSW: {p['csw']:.3f} | Conf: {p['confidence']:<4} {flag_str}")
