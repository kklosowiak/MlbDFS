import os
import sys
from datetime import datetime, timedelta
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
        self._memory_cache = None

    def _load_cache_to_memory(self):
        """Loads cache into memory once."""
        if self._memory_cache is not None:
            return self._memory_cache
            
        if not os.path.exists(self.cache_path):
            self._memory_cache = {}
            return {}
            
        try:
            with open(self.cache_path, 'r') as f:
                self._memory_cache = json.load(f)
            return self._memory_cache
        except:
            self._memory_cache = {}
            return {}
        
    def refresh_hitter_data(self, season=2026):
        """
        OMEGA v6.5: Dual-Stream Alignment (Seasonal + Rolling 10-Day).
        Pulls both seasonal and recent momentum to identify 'Hot Hitter' signals.
        """
        print(f"[STATCAST]: Refreshing dual-stream alpha for {season}...")
        
        # 1. Fetch Seasonal Baselines
        seasonal_data = self._fetch_api_stats(group='hitting', stats='season', season=season)
        
        # 2. Fetch Rolling 10-Day Momentum
        today = datetime.now().strftime("%Y-%m-%d")
        ten_days_ago = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        rolling_data = self._fetch_api_stats(
            group='hitting', 
            stats='byDateRange', 
            season=season,
            extra_params={'startDate': ten_days_ago, 'endDate': today}
        )
        
        if not seasonal_data:
            print("  - WARNING: StatsAPI refresh returned no seasonal data.")
            return {}
            
        # 3. Merge and Cache
        cache = {}
        processed_names = set(list(seasonal_data.keys()) + list(rolling_data.keys()))
        
        for name in processed_names:
            s = seasonal_data.get(name, {})
            r = rolling_data.get(name, {})
            
            cache[name] = {
                "team": s.get('team') or r.get('team') or "UNK",
                "avg": s.get('avg', 0.0),
                "ops": s.get('ops', 0.0),
                "hr": s.get('hr', 0),
                "pa": s.get('pa', 0),
                "rolling_ops": r.get('ops', 0.0),
                "rolling_pa": r.get('pa', 0),
                "timestamp": datetime.now().isoformat()
            }
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        
        with open(self.cache_path, 'w') as f:
            json.dump(cache, f, indent=4)
            
        print(f"  - SUCCESS: Cached {len(cache)} hitters with dual-stream momentum.")
        return cache

    def _fetch_api_stats(self, group='hitting', stats='season', season=2026, extra_params=None):
        """Internal helper for MLB StatsAPI requests."""
        time.sleep(random.uniform(0.3, 0.7)) # Respect rate limits
        params = {
            'stats': stats,
            'group': group,
            'sportId': 1,
            'season': season,
            'limit': 1000
        }
        if extra_params:
            params.update(extra_params)
        
        try:
            response = requests.get(self.api_url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            if 'stats' not in data or not data['stats'][0].get('splits'):
                return {}
                
            splits = data['stats'][0]['splits']
            results = {}
            
            def safe_float(val):
                if val is None or val == "": return 0.0
                try: 
                    s_val = str(val)
                    if s_val.startswith('.'):
                        return float(s_val)
                    return float(s_val)
                except: return 0.0

            for split in splits:
                p_name = split.get('player', {}).get('fullName')
                if not p_name: continue
                
                name = normalize_player_name(str(p_name))
                stat = split.get('stat', {})
                
                results[name] = {
                    "team": split.get('team', {}).get('name', "UNK"),
                    "avg": safe_float(stat.get('avg', '0.000')),
                    "ops": safe_float(stat.get('ops', '0.000')),
                    "hr": int(stat.get('homeRuns', 0)),
                    "pa": int(stat.get('plateAppearances', 0))
                }
            return results
        except Exception as e:
            print(f"  - ERROR: Fetching {stats} failed: {e}")
            return {}

    def get_player_momentum(self, player_name):
        """OMEGA v6.1: Smarter momentum with cache aging."""
        cache = self._load_cache_to_memory()
        hit_data = cache.get(normalize_player_name(player_name))
        
        if not hit_data: return None
        
        # Simple metadata injection for audit/traceability
        hit_data['is_fresh'] = "timestamp" in hit_data
        return hit_data

if __name__ == "__main__":
    bridge = StatcastBridge()
    bridge.refresh_hitter_data()
