import json

with open('reports/latest_results.json', 'r') as f:
    results = json.load(f)

print('--- MATCHUP: PIRATES vs RAYS ---')
for t in results['teams']:
    if t['team'] in ['Pittsburgh Pirates', 'Tampa Bay Rays']:
        print(f"Team: {t['team']}")
        print(f"  ML Move: {t['ml_move']}")
        print(f"  Divergence: {t['divergence']}%")
        print(f"  Is Sharp: {t['is_sharp']}")

print('\n--- PITCHERS ---')
for p in results['pitchers']:
    if p['pitcher'] in ['Nick Martinez', 'Bubba Chandler']:
         print(f"Pitcher: {p['pitcher']} ({p['team']})")
         print(f"  Alpha: {p['alpha_score']}")
         print(f"  Divergence: {p['divergence']}%")
         print(f"  Sharp Target: {p['is_juiced_target']}")
