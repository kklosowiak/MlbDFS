import json
data = json.load(open('reports/latest_results.json'))
pitchers = data.get('pitchers', [])

high = [p for p in pitchers if p.get('confidence') == 'high']
med = [p for p in pitchers if p.get('confidence') == 'med']
low = [p for p in pitchers if p.get('confidence') == 'low']

print(f"HIGH: {len(high)} | MED: {len(med)} | LOW: {len(low)}")
print()
for p in pitchers:
    print(f"  {p['pitcher']:25s} conf={p.get('confidence','?'):4s}  score={p.get('alpha_score',0)}")
