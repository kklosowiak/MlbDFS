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
                
                # Pitching and Hitting Results
                for side in ['away', 'home']:
                    team_name = game['teams'][side]['team']['name']
                    
                    # --- Pitching ---
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
                        
                    # --- Hitting ---
                    results[team_name]['hitters'] = {}
                    players = box.get('teams', {}).get(side, {}).get('players', {})
                    for p_id, p_data in players.items():
                        b_stats = p_data.get('stats', {}).get('batting', {})
                        if b_stats:
                            name = p_data.get('person', {}).get('fullName', 'Unknown')
                            from utils.normalization import normalize_player_name
                            norm_name = normalize_player_name(name)
                            results[team_name]['hitters'][norm_name] = {
                                'hits': b_stats.get('hits', 0),
                                'hr': b_stats.get('homeRuns', 0),
                                'rbi': b_stats.get('rbi', 0)
                            }
            
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
            ip_raw = sp_stats.get('ip', "0.0")
            try:
                ip = float(ip_raw)
            except ValueError:
                ip = 0.0
            
            k = sp_stats.get('k', 0)
            er = sp_stats.get('er', 0)
            
            # DFS Logic for Pitchers
            high_k = (k >= 6 and er <= 2)
            dominant_ip = (ip >= 6.0 and er <= 1)
            qs_base = (ip >= 6.0 and er <= 3 and k >= 5)
            p_success = high_k or dominant_ip or qs_base
            
            # 3. Hitter Success
            h_stat_line = ""
            h_success = False
            if 'player_score' in r:
                from utils.normalization import normalize_player_name
                norm_h_name = normalize_player_name(r.get('name', ''))
                hitters_dict = result.get('hitters', {})
                if norm_h_name in hitters_dict:
                    h_data = hitters_dict[norm_h_name]
                    hits = h_data.get('hits', 0)
                    hr = h_data.get('hr', 0)
                    rbi = h_data.get('rbi', 0)
                    h_stat_line = f"{hits}H, {hr}HR, {rbi}RBI"
                    h_success = (hits >= 2 or hr >= 1)
                else:
                    h_stat_line = "DNP/No Stats"

            # Check if pitcher matched or was scratched
            is_scratched = False
            if 'alpha_score' in r:
                from utils.normalization import normalize_player_name
                norm_proj = normalize_player_name(r.get('pitcher', ''))
                norm_act = normalize_player_name(sp_stats.get('name', ''))
                if norm_proj and norm_act and norm_proj != norm_act:
                    is_scratched = True

            # Calculate a summary outcome for the target type
            if 'stack_score' in r:
                success = stack_success
            elif 'alpha_score' in r: # Pitcher
                success = p_success if not is_scratched else False
            else: # Hitters
                success = h_success

            success_flag = "[WIN]" if success else "[LOSS]" if status == "Final" else "[BUSY]"
            if is_scratched:
                success_flag = "[SCRATCH]"

            audit_data.append({
                **r,
                'actual_runs': runs,
                'actual_sp': sp_stats.get('name'),
                'actual_k': k if not is_scratched else 0,
                'actual_er': er if not is_scratched else 0,
                'actual_ip': ip_raw if not is_scratched else "0.0",
                'hitter_stat_line': h_stat_line,
                'game_status': status if not is_scratched else "Scratched",
                'success_flag': success_flag,
                'grade': "SCRATCH" if is_scratched else ("A" if success and (r.get('stack_score', 0) > 85 or r.get('alpha_score', 0) > 95 or r.get('player_score', 0) > 95) else "B" if success else "F")
            })
            
        return audit_data
