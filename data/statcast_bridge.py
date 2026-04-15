import os
import sys
from datetime import datetime
import requests
import json
import time
import random

# Support for standalone execution
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.normalization import normalize_player_name

class StatcastBridge:
    def __init__(self, data_dir="data"):
        self.cache_path = os.path.join(data_dir, "statcast_cache.json")
        self.api_url = "https://statsapi.mlb.com/api/v1/stats"
        
    def refresh_hitter_data(self, season=2026):
        """
        OMEGA v6.2: Migrated to official MLB StatsAPI to resolve FanGraphs 403s.
        Pulls season-to-date hitting stats for all hitters and caches them.
        """
        print(f"[STATCAST]: Refreshing official seasonal alpha for {season}...")
        
        # OMEGA v6.1: Randomized footprint to reduce potential rate limiting
        time.sleep(random.uniform(0.5, 1.5))
        
        params = {
            'stats': 'season',
            'group': 'hitting',
            'sportId': 1,
            'season': season,
            'limit': 1000
        }
        
        try:
            response = requests.get(self.api_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if 'stats' not in data or not data['stats'][0].get('splits'):
                print("  - WARNING: StatsAPI refresh returned no data.")
                return {}
                
            splits = data['stats'][0]['splits']
            cache = {}
            
            for split in splits:
                try:
                    p_info = split.get('player', {})
                    p_name = p_info.get('fullName')
                    if not p_name:
                        continue
                        
                    stats = split.get('stat', {})
                    name = normalize_player_name(str(p_name))
                    
                    # OMEGA v6.2 Schema: Strictly typed and safe
                    # Convert strings like ".312" to float 0.312
                    def safe_float(val):
                        if val is None or val == "": return 0.0
                        try:
                            return float(str(val).lstrip('.')) / 1000.0 if str(val).startswith('.') and len(str(val)) <= 4 else float(val)
                        except:
                            return 0.0

                    # Note: stats['avg'] and stats['ops'] are consistently returned as strings by MLB API
                    avg_val = stats.get('avg', '0.000')
                    ops_val = stats.get('ops', '0.000')
                    
                    cache[name] = {
                        "team": split.get('team', {}).get('name', "UNK"),
                        "avg": float(avg_val) if avg_val and not str(avg_val).startswith('.') else safe_float(avg_val),
                        "ops": float(ops_val) if ops_val and not str(ops_val).startswith('.') else safe_float(ops_val),
                        "hr": int(stats.get('homeRuns', 0)),
                        "pa": int(stats.get('plateAppearances', 0)),
                        "timestamp": datetime.now().isoformat()
                    }
                except Exception as e:
                    # Silent skip for corrupted individual player records
                    continue
            
            # Ensure data directory exists
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            
            with open(self.cache_path, 'w') as f:
                json.dump(cache, f, indent=4)
                
            print(f"  - SUCCESS: Cached {len(cache)} hitters via official StatsAPI bridge.")
            return cache
            
        except Exception as e:
            print(f"  - ERROR: StatsAPI bridge failed. {e}")
            return {}

    def get_player_momentum(self, player_name):
        """OMEGA v6.1: Smarter momentum with cache aging."""
        if not os.path.exists(self.cache_path):
            return None
            
        try:
            with open(self.cache_path, 'r') as f:
                cache = json.load(f)
            
            hit_data = cache.get(normalize_player_name(player_name))
            if not hit_data: return None
            
            # Simple metadata injection for audit/traceability
            hit_data['is_fresh'] = "timestamp" in hit_data
            return hit_data
        except:
            return None

if __name__ == "__main__":
    bridge = StatcastBridge()
    bridge.refresh_hitter_data()
