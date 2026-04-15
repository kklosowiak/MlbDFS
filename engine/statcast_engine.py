import os
import pandas as pd
import json
from pybaseball import statcast_pitcher, playerid_lookup, statcast_batter
from datetime import datetime
from config import config
from utils.normalization import normalize_player_name

class StatcastEngine:
    def __init__(self):
        self.cache_dir = os.path.join(config.DATA_DIR, "statcast_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self.two_years_ago = "2024-03-20" # Static range for 2-year analysis
        self.today = datetime.now().strftime("%Y-%m-%d")

    def get_pitcher_arsenal(self, pitcher_name):
        """Fetches the % frequency of each pitch type for a pitcher over 2 seasons."""
        if not pitcher_name: return {}
        norm_name = normalize_player_name(pitcher_name)
        cache_path = os.path.join(self.cache_dir, f"arsenal_{norm_name.replace(' ', '_')}.json")
        
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                return json.load(f)
        
        try:
            print(f"  - Analyzing Statcast Arsenal for {pitcher_name} ({norm_name})...")
            # 1. Lookup ID
            names = norm_name.split(' ')
            p_info = playerid_lookup(names[-1], names[0])
            if p_info.empty: return {}
            
            p_id = p_info.at[0, 'key_mlbam']
            
            # 2. Get Statcast Data
            data = statcast_pitcher(self.two_years_ago, self.today, player_id=p_id)
            if data.empty: return {}
            
            # 3. Calculate Mix
            mix = data['pitch_type'].value_counts(normalize=True).to_dict()
            
            with open(cache_path, 'w') as f:
                json.dump(mix, f)
            return mix
        except Exception as e:
            print(f"ERROR: Failed Statcast for {pitcher_name}: {e}")
            return {}

    def get_hitter_stats_vs_mix(self, hitter_name, arsenal):
        """Calculates hitter xWOBA/ISO weighted by the pitcher's arsenal frequency."""
        if not hitter_name: return 0.320
        norm_name = normalize_player_name(hitter_name)
        h_cache = os.path.join(self.cache_dir, f"stats_{norm_name.replace(' ', '_')}.json")
        
        if os.path.exists(h_cache):
            with open(h_cache, 'r') as f:
                h_stats = json.load(f)
        else:
            h_stats = self._fetch_hitter_stats(hitter_name)

        if not h_stats or not arsenal: return 0.320 # Default xWOBA
        
        weighted_xwoba = 0
        total_weight = 0
        
        for p_type, freq in arsenal.items():
            if p_type in h_stats:
                weighted_xwoba += h_stats[p_type]['xwoba'] * freq
                total_weight += freq
        
        final_xwoba = weighted_xwoba / total_weight if total_weight > 0 else 0.315
        return round(final_xwoba, 3)

    def _fetch_hitter_stats(self, hitter_name):
        """Internal: Pull pitch-type stats for a hitter."""
        try:
            norm_name = normalize_player_name(hitter_name)
            names = norm_name.split(' ')
            h_info = playerid_lookup(names[-1], names[0])
            if h_info.empty: return {}
            h_id = h_info.at[0, 'key_mlbam']
            
            data = statcast_batter(self.two_years_ago, self.today, player_id=h_id)
            if data.empty: return {}
            
            # Group by pitch type for xWOBA
            # estimated_woba_using_speedangle is the xwOBA column
            stats = data.groupby('pitch_type').agg({
                'estimated_woba_using_speedangle': 'mean'
            }).to_dict()['estimated_woba_using_speedangle']
            
            # Map back to simple dict
            result = {k: {"xwoba": v} for k, v in stats.items()}
            return result
        except:
            return {}
