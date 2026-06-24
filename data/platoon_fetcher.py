import os
import sys
import json
import requests
import time
import random
from datetime import datetime

# Support for standalone execution
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from utils.normalization import normalize_player_name

class PlatoonFetcher:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        self.cache_path = os.path.join(data_dir, "platoon_cache.json")
        self.api_url = "https://statsapi.mlb.com/api/v1"

    def fetch_platoon_data(self, season=2026):
        print(f"\n[PLATOONS]: Fetching Team & Pitcher Platoon Splits for {season}...")
        cache = {
            "teams": {},
            "pitchers": {},
            "timestamp": datetime.now().isoformat()
        }

        # 1. Fetch All Teams
        print("  - Fetching active MLB teams...")
        try:
            teams_resp = requests.get(f"{self.api_url}/teams?sportId=1", timeout=10)
            teams_data = teams_resp.json().get('teams', [])
            team_ids = {t['id']: t['name'] for t in teams_data if t.get('sport', {}).get('id') == 1}
        except Exception as e:
            print(f"  - ERROR fetching teams: {e}")
            team_ids = {}

        # 2. Fetch Team Splits
        print("  - Fetching Team Splits vs LHP / RHP...")
        for t_id, t_name in team_ids.items():
            try:
                params = {"stats": "statSplits", "group": "hitting", "sitCodes": "vl,vr", "season": season}
                resp = requests.get(f"{self.api_url}/teams/{t_id}/stats", params=params, timeout=10)
                splits = resp.json().get('stats', [])[0].get('splits', []) if resp.json().get('stats') else []
                
                team_cache = {"vl": {}, "vr": {}}
                for s in splits:
                    code = s.get('split', {}).get('code')
                    stat = s.get('stat', {})
                    if code in ['vl', 'vr']:
                        team_cache[code] = {
                            "ops": float(stat.get('ops', '0.000')),
                            "avg": float(stat.get('avg', '0.000')),
                            "slg": float(stat.get('slg', '0.000')),
                            "wOBA_proxy": (float(stat.get('obp', '0.000')) * 0.4) + (float(stat.get('slg', '0.000')) * 0.6), # Approximation
                            "pa": int(stat.get('plateAppearances', 0))
                        }
                cache['teams'][t_name] = team_cache
                time.sleep(random.uniform(0.1, 0.3))
            except Exception as e:
                pass

        # 3. Fetch Probable Pitchers to get their IDs
        probables_path = os.path.join(self.data_dir, "probable_pitchers.json")
        try:
            with open(probables_path, 'r') as f:
                probables = json.load(f)
        except:
            probables = {}

        print(f"  - Fetching Pitcher Splits vs LHH / RHH for {len(probables)} probables...")
        seen_pitchers = set()
        for team, pitcher_name in probables.items():
            if team.endswith("_time") or pitcher_name in ["TBD", "Tbd", "tbd"]:
                continue
            if pitcher_name in seen_pitchers:
                continue
            seen_pitchers.add(pitcher_name)
            try:
                search_url = f"{self.api_url}/people/search?names={pitcher_name}&sportId=1"
                resp = requests.get(search_url, timeout=10)
                people = resp.json().get('people', [])
                if not people: continue
                player_id = people[0]['id']
                norm_name = normalize_player_name(pitcher_name)

                params_pitcher = {"stats": "statSplits", "group": "pitching", "sitCodes": "vl,vr", "season": season}
                resp2 = requests.get(f"{self.api_url}/people/{player_id}/stats", params=params_pitcher, timeout=10)
                stats = resp2.json().get('stats', [])
                splits = stats[0].get('splits', []) if stats else []
                
                pitcher_cache = {"vl": {}, "vr": {}}
                for s in splits:
                    code = s.get('split', {}).get('code')
                    stat = s.get('stat', {})
                    if code in ['vl', 'vr']:
                        pitcher_cache[code] = {
                            "ops": float(stat.get('ops', '0.000')),
                            "avg": float(stat.get('avg', '0.000')),
                            "slg": float(stat.get('slg', '0.000')),
                            "wOBA_proxy": (float(stat.get('obp', '0.000')) * 0.4) + (float(stat.get('slg', '0.000')) * 0.6),
                            "pa": int(stat.get('battersFaced', 0))
                        }
                cache['pitchers'][norm_name] = pitcher_cache
                time.sleep(random.uniform(0.1, 0.3))
            except Exception as e:
                pass

        # Save Cache
        os.makedirs(self.data_dir, exist_ok=True)
        with open(self.cache_path, 'w') as f:
            json.dump(cache, f, indent=4)
        
        print(f"  - [SUCCESS]: Saved Platoon Cache ({len(cache['teams'])} teams, {len(cache['pitchers'])} pitchers).")
        return self.cache_path

if __name__ == "__main__":
    fetcher = PlatoonFetcher()
    fetcher.fetch_platoon_data()
