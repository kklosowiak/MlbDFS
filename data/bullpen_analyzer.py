import statsapi
from datetime import datetime, timedelta
import os
import json
import concurrent.futures

from config import config

BULLPEN_CACHE_TTL_SEC = 6 * 3600
BULLPEN_CALL_TIMEOUT_SEC = 20


class BullpenAnalyzer:
    def __init__(self):
        self.team_id_map = {}
        self.cache_path = os.path.join(config.DATA_DIR, "bullpen_fatigue_cache.json")
        self._cache = None

    def _load_cache_file(self):
        if self._cache is not None:
            return self._cache
        self._cache = {}
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception:
                self._cache = {}
        return self._cache

    def _save_cache_file(self):
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self._cache, f, indent=2)

    def get_team_id(self, team_name):
        if team_name in self.team_id_map:
            return self.team_id_map[team_name]

        try:
            teams = statsapi.lookup_team(team_name)
            if teams:
                tid = teams[0]["id"]
                self.team_id_map[team_name] = tid
                return tid
        except Exception:
            pass
        return None

    def fetch_recent_usage(self, team_name, days=3):
        """
        Calculates total pitches thrown by a team's bullpen in the last X days.
        Returns: total_pitches, reliever_count
        """
        team_id = self.get_team_id(team_name)
        if not team_id:
            return 0, 0

        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

        total_pitches = 0
        reliever_seen = set()

        try:
            schedule = statsapi.schedule(team=team_id, start_date=start_date, end_date=end_date)
            for game in schedule[:5]:
                game_id = game["game_id"]
                box = statsapi.boxscore_data(game_id)

                for side in ["home", "away"]:
                    if box[side]["team"]["id"] == team_id:
                        pitchers = box[side]["pitchers"]
                        if len(pitchers) > 1:
                            for p_id in pitchers[1:]:
                                p_data = box[side]["players"][f"ID{p_id}"]
                                stats = p_data.get("stats", {}).get("pitching", {})
                                pitches = int(stats.get("numberOfPitches", 0))
                                total_pitches += pitches
                                reliever_seen.add(p_id)
        except Exception as e:
            print(f"  - [BULLPEN]: Usage fetch failed for {team_name}: {e}")

        return total_pitches, len(reliever_seen)

    def _compute_fatigue_score(self, team_name):
        pitches, count = self.fetch_recent_usage(team_name)
        score = min(100, (pitches / 220.0) * 100)
        return {
            "score": round(score, 1),
            "pitches": pitches,
            "relievers_used": count,
            "is_gassed": score >= 80,
            "is_fatigued": score >= 70,
        }

    def get_fatigue_score(self, team_name):
        """
        Returns a score from 0-100. Cached 6h per team; 20s timeout per live pull.
        """
        cache = self._load_cache_file()
        entry = cache.get(team_name)
        if entry:
            try:
                age = datetime.now().timestamp() - float(entry.get("cached_at", 0))
                if age < BULLPEN_CACHE_TTL_SEC:
                    return entry["data"]
            except Exception:
                pass

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(self._compute_fatigue_score, team_name)
            try:
                result = fut.result(timeout=BULLPEN_CALL_TIMEOUT_SEC)
            except concurrent.futures.TimeoutError:
                print(f"  - [BULLPEN]: Timeout for {team_name}; using neutral fatigue.")
                result = {
                    "score": 0.0,
                    "pitches": 0,
                    "relievers_used": 0,
                    "is_gassed": False,
                    "is_fatigued": False,
                }

        cache[team_name] = {"cached_at": datetime.now().timestamp(), "data": result}
        self._cache = cache
        self._save_cache_file()
        return result

    def refresh_bullpen_season_stats(self, season=2026):
        """
        Fetches team relief pitching stats in bulk from the MLB Stats API
        and caches them to data/bullpen_season_cache.json.
        """
        import requests
        cache_path = os.path.join(config.DATA_DIR, "bullpen_season_cache.json")
        print("[BULLPEN]: Refreshing reliever season stats from MLB API...")
        
        try:
            resp = requests.get(
                "https://statsapi.mlb.com/api/v1/teams/stats",
                params={"stats": "statSplits", "group": "pitching", "sportId": 1, "season": season, "sitCodes": "rp"},
                timeout=15
            )
            if resp.status_code == 200:
                splits = resp.json().get("stats", [{}])[0].get("splits", [])
                reliever_map = {}
                for s in splits:
                    team_name = s.get("team", {}).get("name")
                    stat = s.get("stat", {})
                    
                    k = int(stat.get("strikeOuts", 0))
                    bb = int(stat.get("baseOnBalls", 0))
                    bf = int(stat.get("battersFaced", 1))
                    k_bb = (k - bb) / bf if bf > 0 else 0.0
                    
                    reliever_map[team_name] = {
                        "era": float(stat.get("era", 4.00)),
                        "whip": float(stat.get("whip", 1.25)),
                        "k_bb_pct": k_bb,
                        "k": k,
                        "bb": bb,
                        "bf": bf
                    }
                
                with open(cache_path, 'w') as f:
                    json.dump(reliever_map, f, indent=2)
                print(f"  - SUCCESS: Bullpen season cache saved with {len(reliever_map)} teams.")
                return reliever_map
        except Exception as e:
            print(f"  - WARNING: Bullpen season fetch failed: {e}")
        return {}

    def get_dynamic_bullpen_grade(self, team_name):
        """
        Scores team bullpen based on reliever statistics.
        Returns (grade, multiplier, fatigue_mod, era, whip, k_bb)
        """
        cache_path = os.path.join(config.DATA_DIR, "bullpen_season_cache.json")
        reliever_stats = {}
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    reliever_stats = json.load(f)
            except:
                pass
                
        # Resolve team name aliases
        matched_key = None
        for k in reliever_stats.keys():
            if team_name.lower() in k.lower() or k.lower() in team_name.lower():
                matched_key = k
                break
                
        if not matched_key or matched_key not in reliever_stats:
            # Fallback to neutral Average
            return "Average", 1.00, 1.00, 4.00, 1.25, 0.12
            
        stats = reliever_stats[matched_key]
        k_bb = stats["k_bb_pct"]
        era = stats["era"]
        whip = stats["whip"]
        
        # Continuous talent score
        score = (k_bb * 100 * 2.5) + (5.0 - era) * 10 + (1.5 - whip) * 30
        
        if score >= 60.0:
            return "Elite", 0.90, 0.75, era, whip, k_bb
        elif score >= 48.0:
            return "Strong", 0.95, 0.85, era, whip, k_bb
        elif score >= 35.0:
            return "Average", 1.00, 1.00, era, whip, k_bb
        elif score >= 22.0:
            return "Below Average", 1.07, 1.12, era, whip, k_bb
        else:
            return "Weak", 1.15, 1.25, era, whip, k_bb

