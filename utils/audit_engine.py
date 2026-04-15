import requests
import json
import os

class AuditEngine:
    def __init__(self):
        self.api_base = "https://statsapi.mlb.com/api/v1"

    def fetch_results(self, date=None):
        """
        Fetches official scores and pitcher stats for the given date.
        Defaults to today's date if none provided.
        """
        if not date:
            from datetime import datetime
            date = datetime.now().strftime("%Y-%m-%d")
            
        url = f"{self.api_base}/schedule?sportId=1&date={date}&hydrate=boxscore"
        try:
            response = requests.get(url, timeout=15)
            data = response.json()
            games = data.get('dates', [{}])[0].get('games', [])
            
            results = {} # Team: {runs: X, sp_stats: {k: Y, er: Z, ip: W}, status: S}
            
            for game in games:
                teams = game['teams']
                game_pk = game['gamePk']
                status = game['status']['detailedState']
                
                # Fetch detailed boxscore for stats
                box_url = f"{self.api_base}/game/{game_pk}/boxscore"
                try:
                    box_resp = requests.get(box_url, timeout=10)
                    box = box_resp.json()
                except:
                    box = {}

                # Team Results
                results[game['teams']['away']['team']['name']] = {'runs': teams['away'].get('score', 0), 'status': status}
                results[game['teams']['home']['team']['name']] = {'runs': teams['home'].get('score', 0), 'status': status}
                
                # Pitching Results
                for side in ['away', 'home']:
                    team_name = game['teams'][side]['team']['name']
                    pitcher_ids = box.get('teams', {}).get(side, {}).get('pitchers', [])
                    if pitcher_ids:
                        # First pitcher in the list is the starter
                        sp_id = pitcher_ids[0]
                        sp_data = box.get('teams', {}).get(side, {}).get('players', {}).get(f"ID{sp_id}", {})
                        stats = sp_data.get('stats', {}).get('pitching', {})
                        results[team_name]['sp_stats'] = {
                            'name': sp_data.get('person', {}).get('fullName', 'Unknown'),
                            'k': stats.get('strikeOuts', 0),
                            'er': stats.get('earnedRuns', 0),
                            'ip': stats.get('inningsPitched', "0.0")
                        }
                    else:
                        results[team_name]['sp_stats'] = {'name': 'TBD', 'k': 0, 'er': 0, 'ip': "0.0"}
            
            return results
        except Exception as e:
            print(f"Audit Fetch Error: {e}")
            return {}

    def score_performance(self, alpha_reports, final_results):
        """
        Compares Alpha Scores vs. Reality.
        """
        audit_data = []
        for r in alpha_reports:
            # We match on team name (flexible normalization should be handled by caller)
            team_name = r.get('team')
            result = final_results.get(team_name, {})
            
            if not result:
                # Try normalization fallback
                from utils.normalization import normalize_player_name # Not exactly for teams but placeholder for logic
                # For now, we assume team names match standard MLB names
                continue

            runs = result.get('runs', 0)
            sp_stats = result.get('sp_stats', {'k': 0, 'er': 0, 'ip': "0.0", 'name': 'Unknown'})
            status = result.get('status', 'Unknown')
            
            # Success Flags
            # 1. Team Stack Success: Score >= 5 runs OR Win with Score >= 4
            stack_success = runs >= 5
            
            # 2. Pitcher Success: >= 6 Ks AND <= 2 ER (Targeting Alpha-Tier)
            # Or > 5 innings and < 3 ER
            k_success = sp_stats.get('k', 0) >= 6
            er_success = sp_stats.get('er', 0) <= 2
            p_success = k_success and er_success
            
            # Calculate a summary outcome for the target type
            if 'stack_score' in r:
                success = stack_success
            elif 'alpha_score' in r: # Pitcher
                success = p_success
            else: # Hitters (if we add them)
                success = False

            audit_data.append({
                **r,
                'actual_runs': runs,
                'actual_sp': sp_stats.get('name'),
                'actual_k': sp_stats.get('k', 0),
                'actual_er': sp_stats.get('er', 0),
                'actual_ip': sp_stats.get('ip', "0.0"),
                'game_status': status,
                'success_flag': "[WIN]" if success else "[LOSS]" if status == "Final" else "[BUSY]",
                'grade': "A" if success and (r.get('stack_score', 0) > 85 or r.get('alpha_score', 0) > 95) else "B" if success else "F"
            })
            
        return audit_data
