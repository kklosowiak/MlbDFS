import json

with open('reports/latest_results.json', 'r') as f:
    results = json.load(f)

targets = ['Logan Gilbert', 'Jacob deGrom', 'Tyler Glasnow', 'Joe Ryan', 'Cam Schlittler', 'Ranger Suarez']
pitchers = [p for p in results['pitchers'] if p['pitcher'] in targets]
pitchers.sort(key=lambda x: x['alpha_score'], reverse=True)

print('--- PITCHER COMPARISON ---')
for p in pitchers:
    print(f"{p['pitcher']} ({p['team']}) - Alpha: {p['alpha_score']} | Div: {p['divergence']}% | Sharp: {p['is_juiced_target']}")
