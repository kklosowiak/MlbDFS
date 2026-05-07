import json
with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)
for t in data['teams']:
    if t['team'] == 'Chicago Cubs':
        print(f"Cubs game total signal: '{t.get('total_signal', 'None')}'")
