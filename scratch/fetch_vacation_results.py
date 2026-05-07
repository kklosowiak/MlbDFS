import sys
import os
sys.path.append(os.getcwd())
from utils.audit_engine import AuditEngine

import json

ae = AuditEngine()
all_results = {}
for d in ['2026-04-30', '2026-05-01', '2026-05-02', '2026-05-03']:
    print(f"Fetching {d}...")
    all_results[d] = ae.fetch_results(d)

with open('scratch/vacation_actuals.json', 'w') as f:
    json.dump(all_results, f, indent=4)
print("Done")
