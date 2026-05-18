import json
try:
    with open('reports/latest_results.json', 'r', encoding='utf-8') as f:
        res = json.load(f)
    traps = [p for p in res.get('pitchers', []) if p.get('is_trap')]
    for p in traps:
        print(f"{p['pitcher']}: k_odds={p.get('k_odds')}, outs_line={p.get('outs_line')}, outs_odds={p.get('outs_odds')}, ml_move={p.get('ml_move')}")
except Exception as e:
    print("Error:", e)
