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

    def get_cache_data(self):
        """Public accessor for the unified momentum cache."""
        return self._load_cache_to_memory()

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
        
    def refresh_momentum_data(self, season=2026):
        """
        OMEGA v6.6: Unified Dual-Stream Alignment (Hitting + Pitching).
        Pulls seasonal and rolling metrics to eliminate 'Detmers-style' blind spots.
        """
        print(f"[STATCAST]: Refreshing unified momentum alpha for {season}...")
        
        # 1. Fetch Hitting Data
        h_seasonal = self._fetch_api_stats(group='hitting', stats='season', season=season)
        h_rolling = self._fetch_api_stats(
            group='hitting', 
            stats='byDateRange', 
            season=season,
            extra_params={'startDate': (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"), 'endDate': datetime.now().strftime("%Y-%m-%d")}
        )
        
        # 2. Fetch Pitching Data
        p_seasonal = self._fetch_api_stats(group='pitching', stats='season', season=season)
        p_rolling = self._fetch_api_stats(
            group='pitching', 
            stats='byDateRange', 
            season=season,
            extra_params={'startDate': (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d"), 'endDate': datetime.now().strftime("%Y-%m-%d")}
        )
        
        # 3. Unified Merge
        cache = {}
        # Merge Hitters
        for name in set(list(h_seasonal.keys()) + list(h_rolling.keys())):
            s = h_seasonal.get(name, {})
            r = h_rolling.get(name, {})
            cache[name] = {
                "type": "hitter",
                "team": s.get('team') or r.get('team') or "UNK",
                "ops": s.get('ops', 0.0),
                "rolling_ops": r.get('ops', 0.0),
                "pa": s.get('pa', 0),
                "rolling_pa": r.get('pa', 0),
                "k": s.get('k', 0),
                "rolling_k": r.get('k', 0),
                "timestamp": datetime.now().isoformat()
            }
            
        # Merge Pitchers
        for name in set(list(p_seasonal.keys()) + list(p_rolling.keys())):
            s = p_seasonal.get(name, {})
            r = p_rolling.get(name, {})
            cache[name] = {
                "type": "pitcher",
                "team": s.get('team') or r.get('team') or "UNK",
                "era": s.get('era', 0.0),
                "rolling_era": r.get('era', 0.0),
                "k": s.get('k', 0),
                "rolling_k": r.get('k', 0),
                "ip": s.get('ip', 0.0),
                "timestamp": datetime.now().isoformat()
            }
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        
        with open(self.cache_path, 'w') as f:
            json.dump(cache, f, indent=4)
            
        print(f"  - SUCCESS: Unified cache synchronized ({len(cache)} profiles).")
        return cache

    def get_team_roster(self, team_name, player_type='hitter'):
        """
        Retrieves all cached players of a specific type for a given team.
        Used for Hybrid Hitter Discovery when market props are thin.
        """
        cache = self._load_cache_to_memory()
        if not cache: return []
        
        roster = []
        for name, data in cache.items():
            if data.get('type') == player_type and data.get('team') == team_name:
                p_data = data.copy()
                p_data['name'] = name # Include original name
                roster.append(p_data)
        
        # Sort by OPS (Hitters) or Rolling K (Pitchers) for discovery quality
        if player_type == 'hitter':
            roster.sort(key=lambda x: x.get('ops', 0), reverse=True)
        else:
            roster.sort(key=lambda x: x.get('rolling_k', 0), reverse=True)
            
        return roster

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
                    "era": safe_float(stat.get('era', '0.0')),
                    "k": int(stat.get('strikeOuts', 0)),
                    "ip": safe_float(stat.get('inningsPitched', '0.0')),
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
    bridge.refresh_momentum_data()
