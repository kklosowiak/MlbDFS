import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
from utils.normalization import normalize_player_name

def inject_roster_truth():
    cache_path = "data/statcast_cache.json"
    with open(cache_path, 'r') as f:
        cache = json.load(f)
        
    # Key 2026 Roster Injectors
    players_to_fix = [
        ("Paul Goldschmidt", "New York Yankees", "hitter"),
        ("Willy Adames", "San Francisco Giants", "hitter"),
        ("Cody Bellinger", "New York Yankees", "hitter"),
        ("Max Fried", "New York Yankees", "pitcher"),
        ("Trevor McDonald", "San Francisco Giants", "pitcher"),
        ("Chase Petty", "Cincinnati Reds", "pitcher")
    ]
    
    for name, team, p_type in players_to_fix:
        norm = normalize_player_name(name)
        print(f"Injecting/Verifying {name} on {team}...")
        
        # Try 2026 first, fallback to 2025
        found = False
        for season in [2026, 2025]:
            try:
                search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={name}&sportId=1"
                resp = requests.get(search_url, timeout=10).json()
                if resp.get('people'):
                    pid = resp['people'][0]['id']
                    group = "hitting" if p_type == "hitter" else "pitching"
                    stats_url = f"https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&season={season}&group={group}"
                    s_resp = requests.get(stats_url, timeout=10).json()
                    stats_list = s_resp.get('stats', [])
                    if stats_list and stats_list[0].get('splits'):
                        stat = stats_list[0]['splits'][0]['stat']
                        if p_type == "hitter":
                            cache[norm] = {
                                "type": "hitter",
                                "team": team,
                                "ops": float(stat.get('ops', 0.750)),
                                "rolling_ops": 0.0,
                                "pa": int(stat.get('plateAppearances', 0)),
                                "rolling_pa": 0,
                                "k": int(stat.get('strikeOuts', 0)),
                                "rolling_k": 0,
                                "timestamp": f"{season}_PROXY_INJECTED"
                            }
                        else:
                            cache[norm] = {
                                "type": "pitcher",
                                "team": team,
                                "era": float(stat.get('era', 4.00)),
                                "rolling_era": 0.0,
                                "k": int(stat.get('strikeOuts', 0)),
                                "rolling_k": 0,
                                "ip": float(stat.get('inningsPitched', 0.0)),
                                "timestamp": f"{season}_PROXY_INJECTED"
                            }
                        print(f"  Applied {season} stats.")
                        found = True
                        break
            except Exception as e:
                print(f"  Error fetching {name}: {e}")
        
        if not found:
            print(f"  WARNING: Could not find stats for {name}. Using placeholder.")
            if p_type == "hitter":
                cache[norm] = {"type": "hitter", "team": team, "ops": 0.750, "pa": 100, "k": 20}
            else:
                cache[norm] = {"type": "pitcher", "team": team, "era": 4.00, "ip": 10.0, "k": 10}

    with open(cache_path, 'w') as f:
        json.dump(cache, f, indent=4)
    print("Unified cache updated with 2026 Truth.")

if __name__ == "__main__":
    inject_roster_truth()
