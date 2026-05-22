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
