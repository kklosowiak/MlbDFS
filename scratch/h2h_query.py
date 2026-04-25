import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('reports/latest_results.json', 'r') as f:
    results = json.load(f)

print('--- HOUSTON VS ST. LOUIS SUMMARY ---')
for t in results['teams']:
    if t['team'] in ['Houston Astros', 'St. Louis Cardinals']:
        print(f"\n{t['team']} vs {t['opp_pitcher']}:")
        print(f"  Stack Score: {t['stack_score']}")
        print(f"  Divergence: {t['divergence']}% | Trend: {t['trend']}")
        print(f"  ML Move: {t['ml_move']}")
        print(f"  Weather: {t['weather_label']}")
        print(f"  Is Sharp Stack: {t['is_sharp']}")

print('\n--- TOP HITTERS ---')
hitters = [h for h in results['hitters'] if h['team'] in ['Houston Astros', 'St. Louis Cardinals']]
for h in hitters[:8]:
    print(f"{h['name']} ({h['team']}) - Score: {h['player_score']} | Matchup xWOBA: {h.get('matchup_xwoba', 0)} | Hot: {h['is_hot']} | Sharp: {h['is_juiced_target']}")
