import json
import os

class MatchupRadar:
    def __init__(self, data_dir="data"):
        self.data_path = os.path.join(data_dir, "matchup_data.json")
        self.data = self._load_data()
        
    def _load_data(self):
        if not os.path.exists(self.data_path):
            return {"pitchers": {}, "hitters": {}, "league_avg": {}, "meta": {}}
        try:
            from utils.normalization import normalize_player_name
            with open(self.data_path, 'r') as f:
                raw = json.load(f)
            return {
                "pitchers": {normalize_player_name(k): v for k, v in raw.get("pitchers", {}).items()},
                "hitters": {normalize_player_name(k): v for k, v in raw.get("hitters", {}).items()},
                "league_avg": raw.get("league_avg", {}),
                "meta": raw.get("meta", {})
            }
        except Exception:
            return {"pitchers": {}, "hitters": {}, "league_avg": {}, "meta": {}}

    def refresh_data(self):
        from data.savant_fetcher import build_matchup_data
        import datetime
        today = datetime.date.today().isoformat()
        if self.data.get('meta', {}).get('last_refresh') == today:
            print("[MATCHUP DNA]: Already refreshed today, skipping.")
            return
        print("[MATCHUP DNA]: Refreshing pitch arsenal data from Baseball Savant...")
        try:
            new_data = build_matchup_data()
            with open(self.data_path, 'w') as f:
                json.dump(new_data, f, indent=2)
            self.data = self._load_data()
            print(f"[MATCHUP DNA]: Refreshed — {new_data['meta']['pitcher_count']} pitchers, {new_data['meta']['hitter_count']} hitters.")
        except Exception as e:
            print(f"[MATCHUP DNA]: Refresh failed: {e}. Using existing data.")

    def get_matchup_boost(self, hitter_name, pitcher_name):
        """
        Calculates a synergy multiplier based on Pitch Arsenal vs. xwOBA.
        Returns a float (e.g., 1.05 for a boost, 0.95 for a penalty).
        """
        from utils.normalization import normalize_player_name
        pitcher = self.data['pitchers'].get(normalize_player_name(pitcher_name))
        hitter = self.data['hitters'].get(normalize_player_name(hitter_name))
        league_avg = self.data['league_avg']
        
        if not pitcher or not hitter:
            return 1.0 # Neutral if data missing
            
        # 1. Identify Pitcher's Primary Weapons
        # We look at any pitch with > 25% usage
        weapons = {ptype: usage for ptype, usage in pitcher.items() if usage >= 25.0}
        
        if not weapons:
            return 1.0
            
        total_boost = 0.0
        weight_sum = 0.0
        
        for ptype, usage in weapons.items():
            h_stat = hitter.get(ptype)
            l_avg = league_avg.get(ptype, 0.300)
            
            if h_stat and l_avg:
                # Advantage ratio (How much better/worse hitter is vs this pitch compared to avg)
                ratio = h_stat / l_avg
                
                # Weight by usage percentage
                weight = usage / 100.0
                total_boost += (ratio - 1.0) * weight
                weight_sum += weight
        
        if weight_sum == 0:
            return 1.0
            
        # Scale the effect: We don't want it to dominate the model.
        # A 1.05 boost (5%) is a strong synergy signal.
        final_multiplier = 1.0 + (total_boost * 0.5) # Dampen the effect by 50% for stability
        
        # Hard Cap: 0.90 to 1.10
        return max(0.90, min(1.10, final_multiplier))

if __name__ == "__main__":
    radar = MatchupRadar()
    # Test Olson vs Nelson (Fastball Heavy)
    boost = radar.get_matchup_boost("Olson, Matt", "Nelson, Ryne")
    print(f"Olson vs Nelson Matchup Boost: {round(boost, 3)}x")
    
    # Test Judge vs Williams
    boost = radar.get_matchup_boost("Judge, Aaron", "Williams, Gavin")
    print(f"Judge vs Williams Matchup Boost: {round(boost, 3)}x")
