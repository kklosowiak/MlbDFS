"""Diagnose WHY pitchers are hitting 'low' confidence."""
import sys, os, json
sys.path.append(os.getcwd())
from utils.normalization import normalize_player_name

# 1. Check statcast_cache for pitcher entries
cache = json.load(open("data/statcast_cache.json"))
pitchers_in_cache = {k: v for k, v in cache.items() if v.get('type') == 'pitcher'}

# 2. Today's slate pitchers (from probable_pitchers.json)
prob = json.load(open("data/probable_pitchers.json"))
print(f"=== TODAY'S STARTERS ({len(prob)} teams) ===")

master_names = [
    "Luis Castillo", "Max Fried", "Ranger Suarez", "Dylan Cease",
    "Jack Leiter", "Randy Vasquez", "Jack Kochanowicz"
]
master_norms = [normalize_player_name(n) for n in master_names]

for team, pitcher in prob.items():
    norm = normalize_player_name(pitcher)
    in_cache = norm in pitchers_in_cache
    in_master = norm in master_norms
    
    cache_data = pitchers_in_cache.get(norm, {})
    ip = cache_data.get('ip', 0)
    era = cache_data.get('era', '-')
    k = cache_data.get('k', 0)
    
    if in_master:
        status = "HIGH (master_matrix)"
    elif in_cache and ip > 5.0:
        status = f"SHOULD BE MED (cache: ERA={era}, K={k}, IP={ip})"
    elif in_cache:
        status = f"LOW - cache has 0 IP (ERA={era}, K={k}, IP={ip})"
    else:
        status = "LOW - NOT IN CACHE AT ALL"
    
    print(f"  {team}: {pitcher} ({norm}) -- {status}")
