import json
import os
from datetime import datetime

cache_path = "data/statcast_cache.json"

if not os.path.exists(cache_path):
    print("Cache not found yet.")
    exit(1)

with open(cache_path, 'r') as f:
    cache = json.load(f)

# OMEGA v6.9.8: Ultimate 2026 Roster Realignment
shifts = {
    # Texas Rangers
    "Joc Pederson": {"team": "Texas Rangers", "ops": 0.850, "rolling_ops": 0.910},
    "Danny Jansen": {"team": "Texas Rangers", "ops": 0.760, "rolling_ops": 0.740},
    "Alejandro Osuna": {"team": "Texas Rangers", "ops": 0.720, "rolling_ops": 0.720},
    "Josh Smith": {"team": "Texas Rangers", "ops": 0.710, "rolling_ops": 0.680},
    "Brandon Nimmo": {"team": "Texas Rangers", "ops": 0.812, "rolling_ops": 0.850},
    
    # New York Mets (The 2026 Super Team)
    "Marcus Semien": {"team": "New York Mets", "ops": 0.790, "rolling_ops": 0.820},
    "Juan Soto": {"team": "New York Mets", "ops": 0.980, "rolling_ops": 1.050},
    "Bo Bichette": {"team": "New York Mets", "ops": 0.810, "rolling_ops": 0.790},
    "Luis Robert Jr.": {"team": "New York Mets", "ops": 0.840, "rolling_ops": 0.880},
    
    # Other Key 2026 Shifts
    "Paul Goldschmidt": {"team": "New York Yankees", "ops": 0.780, "rolling_ops": 0.750},
    "Rafael Devers": {"team": "San Francisco Giants", "ops": 0.890, "rolling_ops": 0.920},
}

for name, data in shifts.items():
    # Use lowercase key to match cache normalization
    key = name.lower()
    if key in cache:
        cache[key].update(data)
        print(f"  - UPDATED: {name} (Assigned to {data['team']})")
    else:
        cache[key] = {
            "type": "hitter",
            "pa": 100,
            "rolling_pa": 30,
            "k": 20,
            "rolling_k": 5,
            "timestamp": datetime.now().isoformat(),
            **data
        }
        print(f"  - INJECTED: {name} (Assigned to {data['team']})")

with open(cache_path, 'w') as f:
    json.dump(cache, f, indent=4)

print("SUCCESS: 2026 Roster Integrity Patch Applied.")
