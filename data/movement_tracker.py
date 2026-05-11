import pandas as pd
import os
import json
from datetime import datetime
from config import config

class MovementTracker:
    def __init__(self):
        self.snapshots_dir = config.DATA_DIR
        
    def find_latest_snapshots(self, count=2):
        """Finds the last N snapshot files in the data directory."""
        files = [f for f in os.listdir(self.snapshots_dir) if f.startswith("snapshot_") and f.endswith(".json")]
        files.sort(reverse=True)
        return [os.path.join(self.snapshots_dir, f) for f in files[:count]]

    def calculate_movement(self):
        """
        OMEGA v7.8: Dual-Stream Movement Tracker (ITT + Props).
        Compares the two latest snapshots to find both Team and Player-level movement.
        """
        snapshots = self.find_latest_snapshots(2)
        if len(snapshots) < 2:
            return None
            
        with open(snapshots[0], 'r') as f:
            l_snap = json.load(f)
            latest = l_snap['odds']
            l_props = l_snap.get('props', {})
            
        with open(snapshots[1], 'r') as f:
            p_snap = json.load(f)
            previous = p_snap['odds']
            p_props = p_snap.get('props', {})
            
        movements = []
        prev_map = {game['id']: game for game in previous}
        
        # 1. Calculate Team ITT Movements
        for game in latest:
            gid = game['id']
            if gid not in prev_map: continue
            
            p_game = prev_map[gid]
            home_team = game['home_team']
            away_team = game['away_team']
            
            l_ml_home, l_ml_away = self._get_ml_both(game)
            p_ml_home, p_ml_away = self._get_ml_both(p_game)
            l_total = self._get_total(game)
            p_total = self._get_total(p_game)
            
            if all(v is not None for v in [l_ml_home, p_ml_home, l_total, p_total]):
                l_prob_home = self._ml_to_prob(l_ml_home)
                p_prob_home = self._ml_to_prob(p_ml_home)
                l_itt_home = l_total * l_prob_home
                p_itt_home = p_total * p_prob_home
                
                l_prob_away = self._ml_to_prob(l_ml_away)
                p_prob_away = self._ml_to_prob(p_ml_away)
                l_itt_away = l_total * l_prob_away
                p_itt_away = p_total * p_prob_away
                
                movements.append({
                    'team': home_team,
                    'ml_move': p_ml_home - l_ml_home,
                    'tt_move': round(l_itt_home - p_itt_home, 2),
                    'game_total': l_total,
                    'opponent': away_team,
                    'type': 'team'
                })
                movements.append({
                    'team': away_team,
                    'ml_move': p_ml_away - l_ml_away,
                    'tt_move': round(l_itt_away - p_itt_away, 2),
                    'game_total': l_total,
                    'opponent': home_team,
                    'type': 'team'
                })
        
        # 2. Calculate Pitcher Prop Movements (K-Lines)
        for p_name, l_data in l_props.items():
            if p_name in p_props:
                prev_data = p_props[p_name]
                k_move = (l_data.get('pitcher_strikeouts', {}).get('point', 0) or 0) - (prev_data.get('pitcher_strikeouts', {}).get('point', 0) or 0)
                outs_move = (l_data.get('pitcher_outs', {}).get('point', 0) or 0) - (prev_data.get('pitcher_outs', {}).get('point', 0) or 0)
                
                if k_move != 0 or outs_move != 0:
                    movements.append({
                        'player': p_name,
                        'k_move': round(k_move, 1),
                        'outs_move': round(outs_move, 1),
                        'type': 'prop'
                    })
                
        return movements

    def _ml_to_prob(self, ml):
        if ml < 0: return abs(ml) / (abs(ml) + 100)
        return 100 / (ml + 100)

    def _get_ml_both(self, game_data):
        try:
            outcomes = game_data['bookmakers'][0]['markets'][0]['outcomes']
            return outcomes[0]['price'], outcomes[1]['price']
        except: return None, None

    def _get_total(self, game_data):
        try:
            return game_data['bookmakers'][0]['markets'][1]['outcomes'][0]['point']
        except: return None

if __name__ == "__main__":
    tracker = MovementTracker()
    movement = tracker.calculate_movement()
    print(movement)
