import sys
sys.path.append('.')
import json
from utils.normalization import normalize_player_name

with open('data/statcast_cache.json', 'r') as f:
    data = json.load(f)

norm_name = normalize_player_name('Moises Ballesteros')
stats = data.get(norm_name)
if stats:
    xwoba = stats.get('ops', 0) / 2.5
    print(f"Found {norm_name}: {xwoba:.3f} xwOBA, PA: {stats.get('pa')}")
else:
    print('Moises Ballesteros not found in cache.')
