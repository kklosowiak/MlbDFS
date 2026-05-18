import statsapi
from datetime import datetime, timedelta
import os
import json

class BullpenAnalyzer:
    def __init__(self):
        self.team_id_map = {} # Cache for team IDs
        
    def get_team_id(self, team_name):
        if team_name in self.team_id_map:
            return self.team_id_map[team_name]
        
        try:
            teams = statsapi.lookup_team(team_name)
            if teams:
                tid = teams[0]['id']
                self.team_id_map[team_name] = tid
                return tid
        except:
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
            
        end_date = datetime.now().strftime('%Y-%m-%d')
        start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
        
        total_pitches = 0
        reliever_seen = set()
        
        try:
            schedule = statsapi.schedule(team=team_id, start_date=start_date, end_date=end_date)
            for game in schedule:
                game_id = game['game_id']
                # boxscore_data is more robust for player-level stats
                box = statsapi.boxscore_data(game_id)
                
                # Check both home and away just in case
                for side in ['home', 'away']:
                    if box[side]['team']['id'] == team_id:
                        # Find pitchers who are NOT the starter
                        # The first pitcher in the list is usually the starter
                        pitchers = box[side]['pitchers']
                        if len(pitchers) > 1:
                            # Skip the first one as it's the starter
                            for p_id in pitchers[1:]:
                                p_data = box[side]['players'][f"ID{p_id}"]
                                stats = p_data.get('stats', {}).get('pitching', {})
                                pitches = int(stats.get('numberOfPitches', 0))
                                total_pitches += pitches
                                reliever_seen.add(p_id)
        except Exception as e:
            print(f"Error fetching bullpen usage for {team_name}: {e}")
            
        return total_pitches, len(reliever_seen)

    def get_fatigue_score(self, team_name):
        """
        Returns a score from 0-100.
        180 pitches = Fatigued (Signal Level)
        220 pitches = Gassed (Deep Fatigue)
        """
        pitches, count = self.fetch_recent_usage(team_name)
        # Baseline: 220 pitches is "Gassed"
        score = min(100, (pitches / 220.0) * 100)
        return {
            "score": round(score, 1),
            "pitches": pitches,
            "relievers_used": count,
            "is_gassed": score >= 80,
            "is_fatigued": score >= 70
        }

if __name__ == "__main__":
    analyzer = BullpenAnalyzer()
    print(f"Analyzing White Sox Bullpen...")
    res = analyzer.get_fatigue_score("Chicago White Sox")
    print(json.dumps(res, indent=4))
