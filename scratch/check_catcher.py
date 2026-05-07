import sys
sys.path.append('.')
import json
from utils.normalization import normalize_player_name

with open('data/statcast_cache.json', 'r') as f:
    cache = json.load(f)

for p in ['Drew Romo', 'Tyler Heineman']:
    norm = normalize_player_name(p)
    data = cache.get(norm)
    if data:
        ops = data.get('ops', 0)
        roll_ops = data.get('rolling_ops', 0)
        xwoba = ops / 2.5
        roll_xwoba = roll_ops / 2.5
        print(f"{p} ({data.get('team')}): Season xwOBA: {xwoba:.3f} | Rolling: {roll_xwoba:.3f} | PA: {data.get('pa')}")
    else:
        print(f"{p}: No data in cache")
