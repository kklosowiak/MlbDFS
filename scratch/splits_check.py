import json

with open('data/snapshot_20260417_175700.json', 'r') as f:
    snapshot = json.load(f)

splits = snapshot.get('splits', {})
print("--- RAW SPLITS: PIRATES vs RAYS ---")

for code in ['PIT', 'TB']:
    data = splits.get(code, {})
    print(f"Team Code: {code}")
    print(f"  Cash %: {data.get('cash_pct')}")
    print(f"  Ticket %: {data.get('ticket_pct')}")
    print(f"  Gap (Cash - Tickets): {int(data.get('cash_pct', 0)) - int(data.get('ticket_pct', 0))}%")
