import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from utils.normalization import normalize_player_name

def patch_cache():
    cache_path = "data/statcast_cache.json"
    if not os.path.exists(cache_path):
        print("Error: Cache not found.")
        return
        
    with open(cache_path, 'r') as f:
        cache = json.load(f)
    
    # 1. Patch Pitchers (Trevor McDonald and Chase Petty)
    pitchers = [
        ("Trevor McDonald", "San Francisco Giants"),
        ("Chase Petty", "Cincinnati Reds")
    ]
    
    for name, team in pitchers:
        norm = normalize_player_name(name)
        print(f"Patching Pitcher: {name}...")
        # Fetch 2025 stats
        try:
            search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={name}&sportId=1"
            resp = requests.get(search_url, timeout=10).json()
            if resp.get('people'):
                pid = resp['people'][0]['id']
                stats_url = f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&season=2025&group=pitching"
                s_resp = requests.get(stats_url, timeout=10).json()
                splits = s_resp.get('stats', [{}])[0].get('splits', [])
                if splits:
                    stat = splits[0]['stat']
                    cache[norm] = {
                        "type": "pitcher",
                        "team": team,
                        "era": float(stat.get('era', '4.00')),
                        "rolling_era": 0.0,
                        "k": int(stat.get('strikeOuts', 0)),
                        "rolling_k": 0,
                        "ip": float(stat.get('inningsPitched', '0.0')),
                        "timestamp": "2025_PROXY_INJECTED"
                    }
                    print(f"  Success: {name} (2025 Proxy: IP={stat.get('inningsPitched')})")
        except Exception as e:
            print(f"  Failed {name}: {e}")

    # 2. Patch Hitter Blind Spots (Cubs/Padres)
    # This is more complex, but we can look for anyone in the 2026 cache with 0 PA and try 2025.
    low_teams = ["Chicago Cubs", "San Diego Padres"]
    hitter_count = 0
    for name, data in cache.items():
        if data.get('type') == 'hitter' and data.get('team') in low_teams and data.get('pa', 0) == 0:
            # Try to fetch 2025 data
            try:
                search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={name}&sportId=1"
                resp = requests.get(search_url, timeout=10).json()
                if resp.get('people'):
                    pid = resp['people'][0]['id']
                    stats_url = f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&season=2025&group=hitting"
                    s_resp = requests.get(stats_url, timeout=10).json()
                    splits = s_resp.get('stats', [{}])[0].get('splits', [])
                    if splits:
                        stat = splits[0]['stat']
                        data['ops'] = float(stat.get('ops', 0.0))
                        data['pa'] = int(stat.get('plateAppearances', 0))
                        data['k'] = int(stat.get('strikeOuts', 0))
                        data['timestamp'] = "2025_PROXY_INJECTED"
                        hitter_count += 1
            except: pass
            
    print(f"Patched {hitter_count} hitters with 2025 proxy data.")
    
    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=4)
    print("Cache updated and saved.")

if __name__ == "__main__":
    patch_cache()
