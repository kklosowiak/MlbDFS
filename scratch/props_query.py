import json
import io
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('reports/latest_results.json', 'r') as f:
    results = json.load(f)

pitchers = results.get('pitchers', [])

# Filter for pitchers with valid odds
k_props = [p for p in pitchers if isinstance(p.get('k_odds'), (int, float)) and p['k_odds'] < 0]
k_props.sort(key=lambda x: x['k_odds'])  # Sort from most negative (most juiced) to least

outs_props = [p for p in pitchers if isinstance(p.get('outs_odds'), (int, float)) and p['outs_odds'] < 0]
outs_props.sort(key=lambda x: x['outs_odds'])

print("TOP STRIKEOUT PROPS (Most Juiced to the Over)")
for p in k_props[:5]:
    sharp_tag = "SHARP" if p['is_juiced_target'] else ""
    print(f"{p['pitcher']} ({p['team']}) | Line: {p['k_line']} | Odds: {p['k_odds']} | OMEGA Alpha: {p['alpha_score']:.1f} | {sharp_tag}")

print("\nTOP OUTS PROPS (Most Juiced to the Over)")
for p in outs_props[:5]:
    sharp_tag = "SHARP" if p['is_juiced_target'] else ""
    print(f"{p['pitcher']} ({p['team']}) | Line: {p['outs_line']} | Odds: {p['outs_odds']} | OMEGA Alpha: {p['alpha_score']:.1f} | {sharp_tag}")
