import json
with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)
for p in data['pitchers']:
    print(f"{p['pitcher']} ({p['team']}) - {p['confidence']}")
