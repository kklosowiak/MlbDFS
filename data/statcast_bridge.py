import os
import sys
from datetime import datetime, timedelta
import requests
import json
import time
import random
import concurrent.futures
import statistics

# Support for standalone execution
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.normalization import normalize_player_name
from utils.team_resolve import teams_match

class StatcastBridge:
    def __init__(self, data_dir="data"):
        self.cache_path = os.path.join(data_dir, "statcast_cache.json")
        self.xwoba_meta_path = os.path.join(data_dir, "statcast_xwoba_meta.json")
        self.api_url = "https://statsapi.mlb.com/api/v1/stats"
        self._memory_cache = None

    @staticmethod
    def _name_from_expected_stats_row(row, name_col):
        """Parse 'Last, First' leaderboard rows into display names."""
        raw = row.get(name_col, "")
        if raw is None or (hasattr(raw, "__float__") and str(raw) == "nan"):
            return None
        text = str(raw).strip()
        if ", " in text:
            last, first = text.split(", ", 1)
            return f"{first} {last}".strip()
        return text or None

    def get_cache_data(self):
        """Public accessor for the unified momentum cache."""
        return self._load_cache_to_memory()

    def get_pitcher_form(self, pitcher_name):
        """OMEGA v10.2: Returns recent form data for a pitcher."""
        form_path = os.path.join(os.path.dirname(self.cache_path), "pitcher_form_cache.json")
        if not os.path.exists(form_path):
            return None
        try:
            with open(form_path, 'r') as f:
                form_cache = json.load(f)
            return form_cache.get(normalize_player_name(pitcher_name))
        except Exception:
            return None

    def get_hitter_form(self, hitter_name):
        """OMEGA v11.0: Returns recent form data for a hitter."""
        form_path = os.path.join(os.path.dirname(self.cache_path), "hitter_form_cache.json")
        if not os.path.exists(form_path):
            return None
        try:
            with open(form_path, 'r') as f:
                form_cache = json.load(f)
            return form_cache.get(normalize_player_name(hitter_name))
        except Exception:
            return None

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
        p_seasonal_2025 = self._fetch_api_stats(group='pitching', stats='season', season=2025)
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
                            "pa": safe_int(stat.get("plateAppearances", 0)),
                            "bb": safe_int(stat.get("baseOnBalls", 0)),
                            "k": safe_int(stat.get("strikeOuts", 0))
                        }
                    print(f"  - Loaded splits for {len(splits_map)} players in {season_year}.")
            except Exception as e:
                print(f"  - WARNING: Failed to fetch bulk splits for {season_year}: {e}")
            return splits_map

        splits_2026 = _fetch_bulk_splits(2026)
        splits_2025 = _fetch_bulk_splits(2025)

        # 3. Unified Merge
        existing_cache = {}
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    existing_cache = json.load(f)
            except Exception:
                pass

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
            
            # Preserve existing xwoba from cache
            existing_profile = existing_cache.get(name, {})
            existing_xwoba = existing_profile.get("xwoba")
            
            cache[name] = {
                "type": "hitter",
                "team": s.get('team') or r.get('team') or "UNK",
                "ops": s.get('ops', 0.0),
                "woba": s.get('woba', 0.0),
                "rolling_ops": r.get('ops', 0.0),
                "pa": s.get('pa', 0),
                "rolling_pa": r.get('pa', 0),
                "k": s.get('k', 0),
                "rolling_k": r.get('k', 0),
                "bat_side": bat_side,
                "vs_left_ops": p_splits_2026.get("vl", {}).get("ops", 0.0),
                "vs_left_pa": p_splits_2026.get("vl", {}).get("pa", 0),
                "vs_left_bb": p_splits_2026.get("vl", {}).get("bb", 0),
                "vs_left_k": p_splits_2026.get("vl", {}).get("k", 0),
                "vs_right_ops": p_splits_2026.get("vr", {}).get("ops", 0.0),
                "vs_right_pa": p_splits_2026.get("vr", {}).get("pa", 0),
                "vs_right_bb": p_splits_2026.get("vr", {}).get("bb", 0),
                "vs_right_k": p_splits_2026.get("vr", {}).get("k", 0),
                "vs_left_ops_2025": p_splits_2025.get("vl", {}).get("ops", 0.0),
                "vs_left_pa_2025": p_splits_2025.get("vl", {}).get("pa", 0),
                "vs_left_bb_2025": p_splits_2025.get("vl", {}).get("bb", 0),
                "vs_left_k_2025": p_splits_2025.get("vl", {}).get("k", 0),
                "vs_right_ops_2025": p_splits_2025.get("vr", {}).get("ops", 0.0),
                "vs_right_pa_2025": p_splits_2025.get("vr", {}).get("pa", 0),
                "vs_right_bb_2025": p_splits_2025.get("vr", {}).get("bb", 0),
                "vs_right_k_2025": p_splits_2025.get("vr", {}).get("k", 0),
                "timestamp": datetime.now().isoformat()
            }
            if existing_xwoba is not None:
                cache[name]["xwoba"] = existing_xwoba

            
        # Merge Pitchers
        for name in set(list(p_seasonal.keys()) + list(p_rolling.keys()) + list(p_seasonal_2025.keys())):
            if name in ["willi castro", "jake bauers", "alec burleson", "anthony seigler"]:
                continue
            s = p_seasonal.get(name, {})
            r = p_rolling.get(name, {})
            s25 = p_seasonal_2025.get(name, {})
            
            # Match handedness
            p_hand = handedness_map.get(name, {})
            pitch_hand = p_hand.get("pitch_hand", "R")
            
            cache[name] = {
                "type": "pitcher",
                "team": s.get('team') or r.get('team') or s25.get('team') or "UNK",
                "era": s.get('era', 0.0),
                "rolling_era": r.get('era', 0.0),
                "k": s.get('k', 0),
                "rolling_k": r.get('rolling_k', 0),
                "ip": s.get('ip', 0.0),
                "pitch_hand": pitch_hand,
                "bb": s.get('bb', 0),
                "hr": s.get('hr', 0),
                "whip": s.get('whip', 1.20),
                
                # 2025 stats for multi-year blending
                "era_2025": s25.get('era', 0.0),
                "k_2025": s25.get('k', 0),
                "ip_2025": s25.get('ip', 0.0),
                "bb_2025": s25.get('bb', 0),
                "hr_2025": s25.get('hr', 0),
                "whip_2025": s25.get('whip', 1.20),
                
                "timestamp": datetime.now().isoformat()
            }
        
        # 4. OMEGA v7.2: Pre-fetch probable pitchers to guarantee cache coverage
        cache = self._prefetch_probable_pitchers(cache, season)
        
        # Ensure data directory exists
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        
        # OMEGA Override: Force Willi Castro, Jake Bauers, and Alec Burleson as hitters
        if "willi castro" in cache:
            cache["willi castro"]["type"] = "hitter"
            cache["willi castro"]["team"] = "Colorado Rockies"
        if "jake bauers" in cache:
            cache["jake bauers"]["type"] = "hitter"
            cache["jake bauers"]["team"] = "Milwaukee Brewers"
        if "alec burleson" in cache:
            cache["alec burleson"]["type"] = "hitter"
            cache["alec burleson"]["team"] = "St. Louis Cardinals"
            
        with open(self.cache_path, 'w') as f:
            json.dump(cache, f, indent=4)
            
        pitchers_count = sum(1 for v in cache.values() if v.get('type') == 'pitcher')
        hitters_count = sum(1 for v in cache.values() if v.get('type') == 'hitter')
        print(f"  - SUCCESS: Unified cache synchronized ({len(cache)} profiles: {pitchers_count} pitchers, {hitters_count} hitters).")
        self._memory_cache = cache
        return cache

    def refresh_statcast_xwoba(self, season=2026, min_pa=30, force=False):
        """
        Bulk-merge Baseball Savant season xwOBA (est_woba) into statcast_cache.json.
        Uses one pybaseball leaderboard pull per season (free). Runs at most once per slate day
        unless force=True, so hourly refreshes do not hammer Savant.
        """
        from utils.xwoba_estimates import cap_matchup_xwoba

        today = datetime.now().strftime("%Y-%m-%d")
        meta = {}
        if os.path.exists(self.xwoba_meta_path):
            try:
                with open(self.xwoba_meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception:
                meta = {}

        if not force and meta.get("last_refresh_date") == today:
            print(f"[STATCAST-XWOBA]: Already refreshed for {today}; skipping (use force=True to override).")
            return self._load_cache_to_memory()

        print(f"[STATCAST-XWOBA]: Pulling Savant expected-stats leaderboard (min PA {min_pa})...")
        try:
            from pybaseball import statcast_batter_expected_stats
        except ImportError:
            print("  - WARNING: pybaseball unavailable; xwOBA refresh skipped.")
            return self._load_cache_to_memory()

        import concurrent.futures

        cache = self._load_cache_to_memory()
        if not cache:
            print("  - WARNING: statcast_cache.json empty; run refresh_momentum_data first.")
            return {}

        xwoba_map = {}
        barrel_map = {}
        hardhit_map = {}
        for yr in (season, season - 1):
            try:
                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
                    fut = ex.submit(statcast_batter_expected_stats, yr, minPA=min_pa)
                    df = fut.result(timeout=90)
                if df is None or df.empty:
                    continue
                name_col = next((c for c in df.columns if "first_name" in str(c)), None)
                if not name_col or "est_woba" not in df.columns:
                    print(f"  - WARNING: Unexpected leaderboard shape for {yr}.")
                    continue
                for _, row in df.iterrows():
                    display_name = self._name_from_expected_stats_row(row, name_col)
                    if not display_name:
                        continue
                    norm = normalize_player_name(display_name)
                    try:
                        xw = float(row["est_woba"])
                    except (TypeError, ValueError):
                        continue
                    if xw < 0.200:
                        continue
                    if yr == season or norm not in xwoba_map:
                        xwoba_map[norm] = cap_matchup_xwoba(xw)
                    # Also pull barrel % and hard hit % from the same row
                    try:
                        brl = float(row.get("barrel_batted_rate", 0) or 0)
                        if brl > 0 and (yr == season or norm not in barrel_map):
                            barrel_map[norm] = round(brl * 100, 1)
                    except (TypeError, ValueError):
                        pass
                    try:
                        hh = float(row.get("hard_hit_percent", 0) or 0)
                        if hh > 0 and (yr == season or norm not in hardhit_map):
                            hardhit_map[norm] = round(hh, 1)
                    except (TypeError, ValueError):
                        pass
                print(f"  - Loaded {len(df)} Savant rows for {yr}.")
            except concurrent.futures.TimeoutError:
                print(f"  - WARNING: Savant xwOBA timed out for {yr}; skipping year.")
            except Exception as e:
                print(f"  - WARNING: Savant xwOBA ingest failed for {yr}: {e}")

        updated = 0
        for norm, profile in cache.items():
            if profile.get("type") != "hitter":
                continue
            xw = xwoba_map.get(norm)
            brl = barrel_map.get(norm)
            hh  = hardhit_map.get(norm)
            if xw:
                profile["xwoba"] = xw
                updated += 1
            if brl is not None:
                profile["barrel_pct"] = brl
            if hh is not None:
                profile["hard_hit_pct"] = hh

        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=4)
        self._memory_cache = cache

        meta["last_refresh_date"] = today
        meta["last_refresh_at"] = datetime.now().isoformat()
        meta["players_updated"] = updated
        meta["leaderboard_size"] = len(xwoba_map)
        with open(self.xwoba_meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)

        print(f"  - SUCCESS: Merged Statcast xwOBA for {updated} hitters ({len(xwoba_map)} leaderboard entries).")
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
        seen_pitchers = set()
        for team, pitcher_name in probables.items():
            if team.endswith("_time") or pitcher_name in ["TBD", "Tbd", "tbd"]:
                continue
            if pitcher_name in seen_pitchers:
                continue
            seen_pitchers.add(pitcher_name)
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

    def refresh_pitcher_form_cache(self, season=2026):
        """
        OMEGA v10.2: Pulls the last 3 game logs for all probable pitchers
        to calculate Recent K/9 and Recent ERA.
        """
        print("[STATCAST]: Refreshing pitcher recent form (L3 starts)...")
        probables_path = os.path.join(os.path.dirname(self.cache_path), "probable_pitchers.json")
        form_path = os.path.join(os.path.dirname(self.cache_path), "pitcher_form_cache.json")
        
        if not os.path.exists(probables_path):
            print("  - WARNING: No probable pitchers found. Skipping form cache.")
            return {}
            
        try:
            with open(probables_path, 'r') as f:
                probables = json.load(f)
        except Exception:
            return {}
            
        form_cache = {}
        def _parse_ip(ip_str):
            try:
                parts = str(ip_str).split('.')
                full_innings = int(parts[0])
                partial = int(parts[1]) if len(parts) > 1 else 0
                return (full_innings * 3) + partial
            except:
                return 0

        def _stats_from_games(games):
            t_outs = 0
            t_k = 0
            t_er = 0
            t_bb = 0
            for g in games:
                stat = g.get('stat', {})
                t_outs += _parse_ip(stat.get('inningsPitched', '0.0'))
                t_k += int(stat.get('strikeOuts', 0))
                t_er += int(stat.get('earnedRuns', 0))
                t_bb += int(stat.get('baseOnBalls', 0))
            t_ip = t_outs / 3.0
            era = (t_er / t_ip * 9.0) if t_ip > 0 else 0.0
            k9 = (t_k / t_ip * 9.0) if t_ip > 0 else 0.0
            bb9 = (t_bb / t_ip * 9.0) if t_ip > 0 else 0.0
            return t_ip, era, k9, bb9

        seen_pitchers = set()
        for team, pitcher_name in probables.items():
            if team.endswith("_time") or pitcher_name in ["TBD", "Tbd", "tbd"]:
                continue
            if pitcher_name in seen_pitchers:
                continue
            seen_pitchers.add(pitcher_name)
            norm = normalize_player_name(pitcher_name)
            try:
                search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={pitcher_name}&sportId=1"
                resp = requests.get(search_url, timeout=10)
                if resp.status_code != 200: continue
                people = resp.json().get('people', [])
                if not people: continue
                player_id = people[0]['id']
                
                log_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group=pitching&season={season}"
                log_resp = requests.get(log_url, timeout=10)
                if log_resp.status_code != 200: continue
                
                stats_data = log_resp.json().get('stats', [])
                if not stats_data: continue
                splits = stats_data[0].get('splits', [])
                if not splits: continue
                
                # Filter for starting pitching games
                starting_splits = [g for g in splits if g.get('stat', {}).get('gamesStarted', 0) == 1]
                target_splits = starting_splits if starting_splits else splits
                
                # Get last 3 games for recent form
                recent_games = target_splits[-3:]
                total_ip, recent_era, recent_k9, recent_bb9 = _stats_from_games(recent_games)
                
                total_k = sum(int(g.get('stat', {}).get('strikeOuts', 0)) for g in recent_games)
                total_er = sum(int(g.get('stat', {}).get('earnedRuns', 0)) for g in recent_games)
                total_bb = sum(int(g.get('stat', {}).get('baseOnBalls', 0)) for g in recent_games)

                # OMEGA v21.1: 5-game rolling window
                recent_games_5g = target_splits[-5:]
                _, recent_era_5g, recent_k9_5g, _ = _stats_from_games(recent_games_5g)
                
                # OMEGA v21.1: Outlier-driven form detection (ex best start)
                recent_era_ex_best = recent_era
                is_outlier_driven = False
                if len(recent_games) >= 2:
                    max_remaining_era = 0.0
                    for i in range(len(recent_games)):
                        sub_games = [g for j, g in enumerate(recent_games) if j != i]
                        _, sub_era, _, _ = _stats_from_games(sub_games)
                        if sub_era > max_remaining_era:
                            max_remaining_era = sub_era
                    recent_era_ex_best = max_remaining_era
                    if len(recent_games) >= 3:
                        if (recent_era_ex_best - recent_era) >= 1.50 and recent_era_ex_best >= 4.0:
                            is_outlier_driven = True
                
                # Trailing 15 starts for variance
                def calculate_pitcher_dk_score(game_stat):
                    ip_str = str(game_stat.get('inningsPitched', '0.0'))
                    try:
                        parts = ip_str.split('.')
                        full_innings = int(parts[0])
                        partial = int(parts[1]) if len(parts) > 1 else 0
                        outs = (full_innings * 3) + partial
                        ip_val = outs / 3.0
                    except:
                        ip_val = 0.0
                    so = int(game_stat.get('strikeOuts', 0))
                    wins = int(game_stat.get('wins', 0))
                    er = int(game_stat.get('earnedRuns', 0))
                    hits = int(game_stat.get('hits', 0))
                    bb = int(game_stat.get('baseOnBalls', 0))
                    hbp = int(game_stat.get('hitByPitch', 0))
                    cg = 1 if game_stat.get('completeGames', 0) else 0
                    sho = 1 if game_stat.get('shutouts', 0) else 0
                    score = (ip_val * 2.25) + (so * 2.0) + (wins * 4.0) - (er * 2.0) - (hits * 0.6) - (bb * 0.6) - (hbp * 0.6)
                    if cg: score += 2.5
                    if sho: score += 2.5
                    return score

                variance_games = target_splits[-15:]
                dk_points_list = [calculate_pitcher_dk_score(g.get('stat', {})) for g in variance_games]
                
                dk_points_mean = 0.0
                dk_points_std = 0.0
                starts_sampled = len(dk_points_list)
                if starts_sampled > 0:
                    dk_points_mean = round(sum(dk_points_list) / starts_sampled, 2)
                if starts_sampled >= 3:
                    dk_points_std = round(statistics.stdev(dk_points_list), 2)
                
                form_cache[norm] = {
                    "pitcher": pitcher_name,
                    "team": team,
                    "games_sampled": len(recent_games),
                    "recent_ip": round(total_ip, 1),
                    "recent_k": total_k,
                    "recent_er": total_er,
                    "recent_bb": total_bb,
                    "recent_k9": round(recent_k9, 2),
                    "recent_era": round(recent_era, 2),
                    "recent_bb9": round(recent_bb9, 2),
                    "recent_era_5g": round(recent_era_5g, 2),
                    "recent_k9_5g": round(recent_k9_5g, 2),
                    "recent_era_ex_best": round(recent_era_ex_best, 2),
                    "is_outlier_driven": is_outlier_driven,
                    "dk_points_mean": dk_points_mean,
                    "dk_points_std": dk_points_std,
                    "starts_sampled": starts_sampled,
                    "timestamp": datetime.now().isoformat()
                }
                print(f"    + {pitcher_name} Form: {len(recent_games)}G, {round(total_ip,1)} IP, {total_k} K (K/9: {round(recent_k9,2)}), {total_er} ER (ERA: {round(recent_era,2)}), L3 BB/9: {round(recent_bb9, 2)} | Trailing Starts: {starts_sampled}, Mean: {dk_points_mean}, Std: {dk_points_std}")
                time.sleep(random.uniform(0.2, 0.4))
            except Exception as e:
                print(f"    ! Failed to fetch form for {pitcher_name}: {e}")
                
        with open(form_path, 'w') as f:
            json.dump(form_cache, f, indent=4)
            
        print(f"  - SUCCESS: Pitcher form cache saved with {len(form_cache)} profiles.")
        return form_cache

    def _fetch_single_hitter_form(self, player_name, season):
        try:
            search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={requests.utils.quote(player_name)}&sportId=1"
            resp = requests.get(search_url, timeout=10)
            if resp.status_code != 200:
                return None
            people = resp.json().get('people', [])
            if not people:
                return None
            player_id = people[0]['id']
            full_name = people[0].get('fullName', player_name)

            log_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group=hitting&season={season}"
            log_resp = requests.get(log_url, timeout=10)
            if log_resp.status_code != 200:
                return None
            stats_data = log_resp.json().get('stats', [])
            if not stats_data:
                return None
            splits = stats_data[0].get('splits', [])
            if not splits:
                return None

            # Get last 7 games
            recent_games = splits[-7:]
            total_pa = 0
            total_ab = 0
            total_hits = 0
            total_bb = 0
            total_hbp = 0
            total_sf = 0
            total_k = 0
            total_2b = 0
            total_3b = 0
            total_hr = 0

            for g in recent_games:
                stat = g.get('stat', {})
                total_pa += int(stat.get('plateAppearances', 0))
                total_ab += int(stat.get('atBats', 0))
                total_hits += int(stat.get('hits', 0))
                total_bb += int(stat.get('baseOnBalls', 0))
                total_hbp += int(stat.get('hitByPitch', 0))
                total_sf += int(stat.get('sacFlies', 0))
                total_k += int(stat.get('strikeOuts', 0))
                total_2b += int(stat.get('doubles', 0))
                total_3b += int(stat.get('triples', 0))
                total_hr += int(stat.get('homeRuns', 0))

            if total_pa == 0:
                return None

            obp_denom = total_ab + total_bb + total_hbp + total_sf
            obp = (total_hits + total_bb + total_hbp) / obp_denom if obp_denom > 0 else 0.0

            singles = total_hits - total_2b - total_3b - total_hr
            tb = singles + 2 * total_2b + 3 * total_3b + 4 * total_hr
            slg = tb / total_ab if total_ab > 0 else 0.0

            ops = obp + slg
            k_rate = total_k / total_pa if total_pa > 0 else 0.0

            return {
                "player": full_name,
                "games_sampled": len(recent_games),
                "recent_pa": total_pa,
                "recent_k": total_k,
                "recent_k_pct": round(k_rate * 100.0, 1),
                "recent_ops": round(ops, 3),
                "timestamp": datetime.now().isoformat()
            }
        except Exception:
            return None

    def refresh_hitter_form_cache(self, active_lineups, season=2026):
        """
        OMEGA v11.0: Pulls the last 7 game logs for all starting hitters
        on the active slate to calculate recent OPS and K%.
        Uses concurrent thread pool and daily local caching.
        """
        print("[STATCAST]: Refreshing hitter recent form (L7 games)...")
        form_path = os.path.join(os.path.dirname(self.cache_path), "hitter_form_cache.json")
        
        hitters_to_fetch = set()
        if active_lineups:
            for team, info in active_lineups.items():
                if team == "_game_times":
                    continue
                if isinstance(info, dict) and 'lineup' in info:
                    for player in info['lineup']:
                        hitters_to_fetch.add(normalize_player_name(player))
                elif isinstance(info, list):
                    for player in info:
                        hitters_to_fetch.add(normalize_player_name(player))
                        
        if not hitters_to_fetch:
            print("  - WARNING: No active starting hitters found to cache form for.")
            return {}

        try:
            with open(form_path, 'r') as f:
                form_cache = json.load(f)
        except Exception:
            form_cache = {}

        def is_fresh(entry):
            if not entry or 'timestamp' not in entry:
                return False
            try:
                ts = datetime.fromisoformat(entry['timestamp'])
                return (datetime.now() - ts).total_seconds() < 12 * 3600
            except:
                return False

        stale_hitters = [h for h in hitters_to_fetch if not is_fresh(form_cache.get(h))]
        
        if stale_hitters:
            print(f"[STATCAST]: Querying MLB StatsAPI for {len(stale_hitters)}/{len(hitters_to_fetch)} hitters concurrently...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
                future_to_hitter = {
                    executor.submit(self._fetch_single_hitter_form, hitter, season): hitter
                    for hitter in stale_hitters
                }
                for future in concurrent.futures.as_completed(future_to_hitter):
                    hitter = future_to_hitter[future]
                    try:
                        res = future.result()
                        if res:
                            form_cache[hitter] = res
                    except Exception as e:
                        print(f"    ! Failed to fetch form for {hitter}: {e}")
            
            try:
                with open(form_path, 'w') as f:
                    json.dump(form_cache, f, indent=4)
                print(f"  - SUCCESS: Hitter form cache saved with {len(form_cache)} profiles.")
            except Exception as e:
                print(f"  - ERROR: Failed to save hitter form cache: {e}")
        else:
            print("[STATCAST]: Hitter form cache is fresh. 0 API calls required.")
            
        return form_cache

    def get_team_roster(self, team_name, player_type='hitter'):
        """
        Retrieves all cached players of a specific type for a given team.
        Used for Hybrid Hitter Discovery when market props are thin.
        """
        cache = self._load_cache_to_memory()
        if not cache: return []
        
        roster = []
        for name, data in cache.items():
            if data.get('type') == player_type and teams_match(data.get('team'), team_name):
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
                    "woba": safe_float(stat.get('woba', '0.000')),
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
