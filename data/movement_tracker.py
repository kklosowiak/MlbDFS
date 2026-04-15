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
        Compares the two latest snapshots to find Implied Team Total (ITT) movement.
        """
        snapshots = self.find_latest_snapshots(2)
        if len(snapshots) < 2:
            return None
            
        with open(snapshots[0], 'r') as f:
            latest = json.load(f)['odds']
        with open(snapshots[1], 'r') as f:
            previous = json.load(f)['odds']
            
        movements = []
        prev_map = {game['id']: game for game in previous}
        
        for game in latest:
            gid = game['id']
            if gid not in prev_map: continue
            
            p_game = prev_map[gid]
            home_team = game['home_team']
            away_team = game['away_team']
            
            # Extract ML and Totals
            l_ml_home, l_ml_away = self._get_ml_both(game)
            p_ml_home, p_ml_away = self._get_ml_both(p_game)
            l_total = self._get_total(game)
            p_total = self._get_total(p_game)
            
            if all(v is not None for v in [l_ml_home, p_ml_home, l_total, p_total]):
                # Calculate ITT for Home and Away
                # ITT_Home = Total * (100 / (abs(ML) + 100))
                l_prob_home = self._ml_to_prob(l_ml_home)
                p_prob_home = self._ml_to_prob(p_ml_home)
                l_itt_home = l_total * l_prob_home
                p_itt_home = p_total * p_prob_home
                
                l_prob_away = self._ml_to_prob(l_ml_away)
                p_prob_away = self._ml_to_prob(p_ml_away)
                l_itt_away = l_total * l_prob_away
                p_itt_away = p_total * p_prob_away
                
                # Append both teams
                movements.append({
                    'team': home_team,
                    'ml_move': p_ml_home - l_ml_home,
                    'tt_move': round(l_itt_home - p_itt_home, 2),
                    'game_total': l_total,
                    'opponent': away_team
                })
                movements.append({
                    'team': away_team,
                    'ml_move': p_ml_away - l_ml_away,
                    'tt_move': round(l_itt_away - p_itt_away, 2),
                    'game_total': l_total,
                    'opponent': home_team
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
