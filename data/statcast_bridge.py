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
        OMEGA v7.2: Unified Dual-Stream Alignment (Hitting + Pitching).
        Pulls seasonal and rolling metrics to eliminate 'Detmers-style' blind spots.
        OMEGA v9.5 splits update: Ingests bulk handedness and splits vs LHP/RHP in parallel.
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
        
        # OMEGA v9.5 Ingestion addition: Bulk Player Directory for Handedness
        handedness_map = {}
        try:
            print("[STATCAST]: Querying bulk players directory for handedness...")
            p_resp = requests.get(f"https://statsapi.mlb.com/api/v1/sports/1/players?season={season}", timeout=15)
            if p_resp.status_code == 200:
                p_data = p_resp.json().get("people", [])
                for p in p_data:
                    p_name = normalize_player_name(p.get("fullName", ""))
                    handedness_map[p_name] = {
                        "bat_side": p.get("batSide", {}).get("code", "R"),
                        "pitch_hand": p.get("pitchHand", {}).get("code", "R")
                    }
                print(f"  - Loaded handedness for {len(handedness_map)} players.")
        except Exception as e:
            print(f"  - WARNING: Failed to fetch bulk handedness: {e}")

        # OMEGA v9.5 Ingestion addition: Helper to fetch bulk splits
        def _fetch_bulk_splits(season_year):
            splits_map = {}
            try:
                print(f"[STATCAST]: Querying bulk splits for season {season_year}...")
                params = {
                    "stats": "statSplits",
                    "group": "hitting",
                    "season": season_year,
                    "sitCodes": "vl,vr",
                    "sportId": 1,
                    "limit": 5000,
                    "playerPool": "all"
                }
                resp = requests.get("https://statsapi.mlb.com/api/v1/stats", params=params, timeout=15)
                if resp.status_code == 200:
                    split_records = resp.json().get("stats", [{}])[0].get("splits", [])
                    for s in split_records:
                        p_name = normalize_player_name(s.get("player", {}).get("fullName", ""))
                        code = s.get("split", {}).get("code")  # "vl" or "vr"
                        stat = s.get("stat", {})
                        
                        def safe_float(val):
                            try: return float(val)
                            except: return 0.0
                            
                        def safe_int(val):
                            try: return int(val)
                            except: return 0
                            
                        if p_name not in splits_map:
                            splits_map[p_name] = {}
                        splits_map[p_name][code] = {
                            "ops": safe_float(stat.get("ops", 0.0)),
                            "pa": safe_int(stat.get("plateAppearances", 0))
                        }
                    print(f"  - Loaded splits for {len(splits_map)} players in {season_year}.")
            except Exception as e:
                print(f"  - WARNING: Failed to fetch bulk splits for {season_year}: {e}")
            return splits_map

        splits_2026 = _fetch_bulk_splits(2026)
        splits_2025 = _fetch_bulk_splits(2025)

        # 3. Unified Merge
        cache = {}
        # Merge Hitters
        for name in set(list(h_seasonal.keys()) + list(h_rolling.keys())):
            s = h_seasonal.get(name, {})
            r = h_rolling.get(name, {})
            
            # Match splits and handedness
            p_hand = handedness_map.get(name, {})
            bat_side = p_hand.get("bat_side", "R")
            
            p_splits_2026 = splits_2026.get(name, {})
            p_splits_2025 = splits_2025.get(name, {})
            
            cache[name] = {
                "type": "hitter",
                "team": s.get('team') or r.get('team') or "UNK",
                "ops": s.get('ops', 0.0),
                "rolling_ops": r.get('ops', 0.0),
                "pa": s.get('pa', 0),
                "rolling_pa": r.get('pa', 0),
                "k": s.get('k', 0),
                "rolling_k": r.get('k', 0),
                "bat_side": bat_side,
                "vs_left_ops": p_splits_2026.get("vl", {}).get("ops", 0.0),
                "vs_left_pa": p_splits_2026.get("vl", {}).get("pa", 0),
                "vs_right_ops": p_splits_2026.get("vr", {}).get("ops", 0.0),
                "vs_right_pa": p_splits_2026.get("vr", {}).get("pa", 0),
                "vs_left_ops_2025": p_splits_2025.get("vl", {}).get("ops", 0.0),
                "vs_left_pa_2025": p_splits_2025.get("vl", {}).get("pa", 0),
                "vs_right_ops_2025": p_splits_2025.get("vr", {}).get("ops", 0.0),
                "vs_right_pa_2025": p_splits_2025.get("vr", {}).get("pa", 0),
                "timestamp": datetime.now().isoformat()
            }
            
        # Merge Pitchers
        for name in set(list(p_seasonal.keys()) + list(p_rolling.keys())):
            s = p_seasonal.get(name, {})
            r = p_rolling.get(name, {})
            
            # Match handedness
            p_hand = handedness_map.get(name, {})
            pitch_hand = p_hand.get("pitch_hand", "R")
            
            cache[name] = {
                "type": "pitcher",
                "team": s.get('team') or r.get('team') or "UNK",
                "era": s.get('era', 0.0),
                "rolling_era": r.get('era', 0.0),
                "k": s.get('k', 0),
                "rolling_k": r.get('rolling_k', 0),
                "ip": s.get('ip', 0.0),
                "pitch_hand": pitch_hand,
                "bb": s.get('bb', 0),
                "hr": s.get('hr', 0),
                "whip": s.get('whip', 1.20),
                "timestamp": datetime.now().isoformat()
            }
        
        # 4. OMEGA v7.2: Pre-fetch probable pitchers to guarantee cache coverage
        cache = self._prefetch_probable_pitchers(cache, season)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        
        with open(self.cache_path, 'w') as f:
            json.dump(cache, f, indent=4)
            
        pitchers_count = sum(1 for v in cache.values() if v.get('type') == 'pitcher')
        hitters_count = sum(1 for v in cache.values() if v.get('type') == 'hitter')
        print(f"  - SUCCESS: Unified cache synchronized ({len(cache)} profiles: {pitchers_count} pitchers, {hitters_count} hitters).")
        return cache

    def _prefetch_probable_pitchers(self, cache, season=2026):
        """
        OMEGA v7.2: Ensures today's probable pitchers are in the cache.
        Reads probable_pitchers.json and fetches stats for any missing pitcher
        directly from the MLB StatsAPI.
        """
        probables_path = os.path.join(os.path.dirname(self.cache_path), "probable_pitchers.json")
        if not os.path.exists(probables_path):
            return cache
        
        try:
            with open(probables_path, 'r') as f:
                probables = json.load(f)
        except Exception:
            return cache
        
        missing = []
        for team, pitcher_name in probables.items():
            norm = normalize_player_name(pitcher_name)
            existing = cache.get(norm)
            if not existing or existing.get('type') != 'pitcher':
                missing.append((team, pitcher_name, norm))
        
        if not missing:
            return cache
        
        print(f"  - PRE-FETCH: {len(missing)} probable pitchers missing from cache. Fetching...")
        for team, pitcher_name, norm in missing:
            try:
                search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={pitcher_name}&sportId=1"
                resp = requests.get(search_url, timeout=10)
                if resp.status_code != 200:
                    continue
                people = resp.json().get('people', [])
                if not people:
                    continue
                player_id = people[0]['id']
                pitch_hand = people[0].get("pitchHand", {}).get("code", "R")
                
                stats_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=season&season={season}&group=pitching"
                stats_resp = requests.get(stats_url, timeout=10)
                if stats_resp.status_code != 200:
                    continue
                stats_data = stats_resp.json().get('stats', [])
                if not stats_data:
                    continue
                splits = stats_data[0].get('splits', [])
                if splits:
                    stat = splits[0].get('stat', {})
                    cache[norm] = {
                        "type": "pitcher",
                        "team": team,
                        "era": float(stat.get('era', '0.0')),
                        "rolling_era": 0.0,
                        "k": int(stat.get('strikeOuts', 0)),
                        "rolling_k": 0,
                        "ip": float(stat.get('inningsPitched', '0.0')),
                        "pitch_hand": pitch_hand,
                        "bb": int(stat.get('baseOnBalls', 0)),
                        "hr": int(stat.get('homeRuns', 0)),
                        "whip": float(stat.get('whip', '1.20')),
                        "timestamp": datetime.now().isoformat()
                    }
                    print(f"    + {pitcher_name} ({team}): ERA={stat.get('era')}, K={stat.get('strikeOuts')}, IP={stat.get('inningsPitched')}, Pitch Hand={pitch_hand}")
                time.sleep(random.uniform(0.2, 0.4))  # Rate limiting
            except Exception as e:
                print(f"    ! Failed to pre-fetch {pitcher_name}: {e}")
        
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

    def get_verified_team(self, player_name):
        """OMEGA v7.3: Roster integrity restored. Trusts Live API data exclusively."""
        return None

    def _fetch_api_stats(self, group='hitting', stats='season', season=2026, extra_params=None):
        """Internal helper for MLB StatsAPI requests."""
        time.sleep(random.uniform(0.3, 0.7)) # Respect rate limits
        params = {
            'stats': stats,
            'group': group,
            'sportId': 1,
            'season': season,
            'limit': 5000,
            'playerPool': 'all'
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
                
                # OMEGA v6.8.2: Hardened Team Mapping
                api_team = split.get('team', {}).get('name', "UNK")
                final_team = api_team
                
                results[name] = {
                    "team": final_team,
                    "avg": safe_float(stat.get('avg', '0.000')),
                    "ops": safe_float(stat.get('ops', '0.000')),
                    "era": safe_float(stat.get('era', '0.0')),
                    "k": int(stat.get('strikeOuts', 0)),
                    "ip": safe_float(stat.get('inningsPitched', '0.0')),
                    "hr": int(stat.get('homeRuns', 0)),
                    "pa": int(stat.get('plateAppearances', 0)),
                    "bb": int(stat.get('baseOnBalls', 0)),
                    "whip": safe_float(stat.get('whip', '1.20'))
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
