import json

with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

for p in data['pitchers']:
    if p['pitcher'] == 'Davis Martin' or p['pitcher'] == 'Joe Ryan':
        print(f"{p['pitcher']} ({p['team']}) - Alpha: {p.get('alpha_score', 0):.1f} | K-line: {p.get('k_line')} | CSW: {p.get('csw', 0):.3f} | Opp: {p.get('opponent')}")
