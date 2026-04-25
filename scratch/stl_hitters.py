import json

with open('reports/latest_results.json', 'r') as f:
    results = json.load(f)

print("--- ST. LOUIS CARDINALS HITTERS ---")
hitters = [h for h in results['hitters'] if h['team'] == 'St. Louis Cardinals']
hitters.sort(key=lambda x: x['player_score'], reverse=True)

for h in hitters:
    print(f"Name: {h['name'].ljust(20)} | Score: {h['player_score']:>5} | xWOBA: {h.get('matchup_xwoba', 0):>6.4f} | Hot: {str(h['is_hot']).ljust(5)} | Sharp: {str(h['is_juiced_target']).ljust(5)} | Price: {h.get('ahr_price', 'N/A')}")
