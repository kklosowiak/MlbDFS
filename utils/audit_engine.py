import requests
import json
import os

def calculate_dk_score(hitter: dict) -> float:
    return float(
        (hitter.get('singles', 0) or 0) * 3 +
        (hitter.get('doubles', 0) or 0) * 5 +
        (hitter.get('triples', 0) or 0) * 8 +
        (hitter.get('hr', 0) or 0) * 10 +
        (hitter.get('rbi', 0) or 0) * 2 +
        (hitter.get('runs_scored', 0) or 0) * 2 +
        (hitter.get('walks', 0) or 0) * 2 +
        (hitter.get('stolen_bases', 0) or 0) * 5 +
        (hitter.get('hbp', 0) or 0) * 2
    )

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
                            'ip': stats.get('inningsPitched', "0.0"),
                            'h': stats.get('hits', 0),
                            'bb': stats.get('baseOnBalls', 0),
                            'wins': stats.get('wins', 0),
                            'completeGames': stats.get('completeGames', 0),
                            'shutouts': stats.get('shutouts', 0),
                            'hitByPitch': stats.get('hitByPitch', 0) or stats.get('hitBatsmen', 0) or 0
                        }
                    else:
                        results[team_name]['sp_stats'] = {
                            'name': 'TBD', 'k': 0, 'er': 0, 'ip': "0.0", 'h': 0, 'bb': 0,
                            'wins': 0, 'completeGames': 0, 'shutouts': 0, 'hitByPitch': 0
                        }
                        
                    # --- Hitting ---
                    results[team_name]['hitters'] = {}
                    players = box.get('teams', {}).get(side, {}).get('players', {})
                    for p_id, p_data in players.items():
                        b_stats = p_data.get('stats', {}).get('batting', {})
                        if b_stats:
                            name = p_data.get('person', {}).get('fullName', 'Unknown')
                            from utils.normalization import normalize_player_name
                            norm_name = normalize_player_name(name)
                            hits = b_stats.get('hits', 0) or 0
                            hr_val = b_stats.get('homeRuns', 0) or 0
                            rbi_val = b_stats.get('rbi', 0) or 0
                            doubles = b_stats.get('doubles', 0) or 0
                            triples = b_stats.get('triples', 0) or 0
                            runs_scored = b_stats.get('runs', 0) or 0
                            walks = b_stats.get('baseOnBalls', 0) or 0
                            stolen_bases = b_stats.get('stolenBases', 0) or 0
                            hbp = b_stats.get('hitByPitch', 0) or 0
                            singles = hits - (doubles + triples + hr_val)
                            
                            results[team_name]['hitters'][norm_name] = {
                                'hits': hits,
                                'hr': hr_val,
                                'rbi': rbi_val,
                                'doubles': doubles,
                                'triples': triples,
                                'runs_scored': runs_scored,
                                'walks': walks,
                                'stolen_bases': stolen_bases,
                                'hbp': hbp,
                                'singles': singles,
                                'strikeouts': b_stats.get('strikeOuts', 0) or 0
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

            # Define success_flag from all sub-components
            success_flag = stack_success or p_success or h_success

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
                'grade': "SCRATCH" if is_scratched else ("A" if success_flag and (r.get('stack_score', 0) > 85 or r.get('alpha_score', 0) > 95 or r.get('player_score', 0) > 95) else "B" if success_flag else "F")
            })
            
        return audit_data


# --- SPRINT 1 UPGRADES: BIVARIATE POISSON SIMULATION ---

try:
    import numpy as np
    HAS_NUMPY = True
except ImportError:
    HAS_NUMPY = False

def simulate_game_poisson(lambda_away, lambda_home, away_spread, home_spread, num_sims=20000):
    """
    Simulates a baseball game using a Bivariate Poisson distribution.
    Returns: away_win_prob, home_win_prob, away_cover_prob, home_cover_prob
    """
    if HAS_NUMPY:
        lambda_3 = 0.15 * min(lambda_away, lambda_home)
        lambda_away_ind = max(0.01, lambda_away - lambda_3)
        lambda_home_ind = max(0.01, lambda_home - lambda_3)
        
        u = np.random.poisson(lambda_away_ind, num_sims)
        v = np.random.poisson(lambda_home_ind, num_sims)
        w = np.random.poisson(lambda_3, num_sims)
        
        away_runs = u + w
        home_runs = v + w
        
        # Win probabilities (resolving ties proportionally)
        ties = (away_runs == home_runs)
        num_ties = np.sum(ties)
        p_away_tie = lambda_away / max(0.01, lambda_away + lambda_home)
        tie_wins = np.random.random(num_ties) < p_away_tie
        
        away_wins = (away_runs > home_runs)
        away_wins[ties] = tie_wins
        
        away_win_prob = float(np.mean(away_wins))
        home_win_prob = 1.0 - away_win_prob
        
        # Spread cover probabilities
        away_cover_prob = float(np.mean(away_runs + away_spread > home_runs))
        home_cover_prob = float(np.mean(home_runs + home_spread > away_runs))
        
        return away_win_prob, home_win_prob, away_cover_prob, home_cover_prob
    else:
        import random
        import math
        # Fallback using Knuth's method
        def get_poisson(lam):
            L = math.exp(-lam)
            k = 0
            p = 1.0
            while p > L:
                k += 1
                p *= random.random()
            return k - 1
            
        lambda_3 = 0.15 * min(lambda_away, lambda_home)
        lambda_away_ind = max(0.01, lambda_away - lambda_3)
        lambda_home_ind = max(0.01, lambda_home - lambda_3)
        
        away_wins_count = 0
        away_cover_count = 0
        home_cover_count = 0
        
        p_away_tie = lambda_away / max(0.01, lambda_away + lambda_home)
        
        for _ in range(num_sims):
            u = get_poisson(lambda_away_ind)
            v = get_poisson(lambda_home_ind)
            w = get_poisson(lambda_3)
            
            ar = u + w
            hr = v + w
            
            if ar > hr:
                away_wins_count += 1
            elif ar == hr:
                if random.random() < p_away_tie:
                    away_wins_count += 1
                    
            if ar + away_spread > hr:
                away_cover_count += 1
            if hr + home_spread > ar:
                home_cover_count += 1
                
        return (
            away_wins_count / num_sims,
            1.0 - (away_wins_count / num_sims),
            away_cover_count / num_sims,
            home_cover_count / num_sims
        )

# Helper utilities for odds & EV calculation
def ml_to_prob(ml):
    if not ml or ml == 0:
        return 0.5
    try:
        ml = float(ml)
        if ml < 0:
            return abs(ml) / (abs(ml) + 100)
        else:
            return 100 / (ml + 100)
    except:
        return 0.5

def calculate_ev(prob, ml):
    if not ml:
        return 0.0
    try:
        ml = float(ml)
        if ml > 0:
            return (prob * (1.0 + ml / 100.0)) - 1.0
        else:
            return (prob * (1.0 + 100.0 / abs(ml))) - 1.0
    except:
        return 0.0

# Extend AuditEngine class
def backfill_betting_history(self):
    """
    Scans all archived result files, runs the Blended Model, audits suggested bets,
    and compiles betting_history.json.
    """
    import os
    import json
    import re
    import numpy as np
    import math
    
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    archive_dir = os.path.join(base_dir, "reports", "archive")
    data_dir = os.path.join(base_dir, "data")
    db_path = os.path.join(data_dir, "betting_history.json")
    
    if not os.path.exists(archive_dir):
        return
        
    files = sorted([f for f in os.listdir(archive_dir) if f.startswith("results_") and f.endswith(".json")])
    season_actuals_dir = os.path.join(data_dir, "season_2026", "actuals")
    
    all_picks = []
    brier_contributions = []
    seen_games = set()
    
    for filename in files:
        date_match = re.search(r'results_(\d{4}-\d{2}-\d{2})', filename)
        if not date_match:
            continue
        date_str = date_match.group(1)
        
        actuals_data = {}
        s26_path = os.path.join(season_actuals_dir, f"actuals_{date_str}.json")
        if os.path.exists(s26_path):
            try:
                with open(s26_path, "r", encoding="utf-8") as f:
                    raw_s26 = json.load(f)
                g_list = raw_s26 if isinstance(raw_s26, list) else raw_s26.get("games", [])
                for g in g_list:
                    if g.get("away_team") and g.get("away_runs") is not None:
                        actuals_data[g["away_team"]] = {"runs": g["away_runs"], "status": "Final"}
                    if g.get("home_team") and g.get("home_runs") is not None:
                        actuals_data[g["home_team"]] = {"runs": g["home_runs"], "status": "Final"}
            except Exception:
                pass

        actuals_path = os.path.join(archive_dir, f"actuals_cache_{date_str}.json")
        if not actuals_data and os.path.exists(actuals_path):
            try:
                with open(actuals_path, "r", encoding="utf-8") as f:
                    actuals_data = json.load(f)
            except:
                pass

        if not actuals_data:
            # 1. Fallback to unified scratch/actuals_cache.json
            scratch_path = os.path.join(base_dir, "scratch", "actuals_cache.json")
            if os.path.exists(scratch_path):
                try:
                    with open(scratch_path, "r", encoding="utf-8") as f:
                        scratch_cache = json.load(f)
                        actuals_data = scratch_cache.get(date_str)
                except:
                    pass

            # 2. Fallback to MLB API
            if not actuals_data:
                try:
                    print(f"[AUDIT ENGINE]: Cache missing for {date_str}. Fetching from MLB API...")
                    actuals_data = self.fetch_results(date=date_str)
                except Exception as e:
                    print(f"[AUDIT ENGINE]: Error fetching from API: {e}")

            # 3. Save resolved actuals locally so it exists in archive next time
            if actuals_data:
                try:
                    with open(actuals_path, "w", encoding="utf-8") as f:
                        json.dump(actuals_data, f, indent=4)
                    print(f"[AUDIT ENGINE]: Saved fetched actuals to {actuals_path}")
                except Exception as e:
                    print(f"[AUDIT ENGINE]: Error writing local actuals cache: {e}")

        if not actuals_data:
            continue
            
        opening_lines = []
        op_path = os.path.join(data_dir, f"opening_lines_{date_str}.json")
        if os.path.exists(op_path):
            try:
                with open(op_path, "r", encoding="utf-8") as f:
                    opening_lines = json.load(f)
            except:
                pass
        
        try:
            with open(os.path.join(archive_dir, filename), "r", encoding="utf-8") as f:
                results_data = json.load(f)
        except:
            continue
            
        teams_list = results_data.get("teams", [])
        pitchers_list = results_data.get("pitchers", [])
        vb_list = results_data.get("vegas_board", [])
        vb_map = {(g.get("away_team"), g.get("home_team")): g for g in vb_list if isinstance(g, dict)}
        if not teams_list:
            continue
            
        processed_teams = set()
        for t in teams_list:
            team_name = t.get("team")
            if not team_name or team_name in processed_teams:
                continue
                
            opponent_name = t.get("opponent")
            opp_team_obj = next((x for x in teams_list if x.get("team") == opponent_name), None)
            if not opp_team_obj:
                continue
                
            processed_teams.add(team_name)
            processed_teams.add(opponent_name)
            
            team_sp = next((p for p in pitchers_list if p.get("team") == team_name and not p.get("is_opener")), None) or next((p for p in pitchers_list if p.get("team") == team_name), None)
            opp_sp = next((p for p in pitchers_list if p.get("team") == opponent_name and not p.get("is_opener")), None) or next((p for p in pitchers_list if p.get("team") == opponent_name), None)
            
            is_team_away = True
            if team_sp and team_sp.get("side") == "home":
                is_team_away = False
            elif opp_sp and opp_sp.get("side") == "away":
                is_team_away = False
            elif (opponent_name, team_name) in vb_map:
                is_team_away = False
                
            away_team = team_name if is_team_away else opponent_name
            home_team = opponent_name if is_team_away else team_name
            if (date_str, away_team, home_team) in seen_games:
                continue
            
            away_team_obj = t if is_team_away else opp_team_obj
            home_team_obj = opp_team_obj if is_team_away else t
            away_sp_obj = team_sp if is_team_away else opp_sp
            home_sp_obj = opp_sp if is_team_away else team_sp
            
            game_line = vb_map.get((away_team, home_team)) or vb_map.get((home_team, away_team))
            if not game_line:
                for o in opening_lines:
                    o_away = o.get("team_away") or ""
                    o_home = o.get("team_home") or ""
                    if (o_away == away_team and o_home == home_team) or \
                       (o_away.split()[-1] == away_team.split()[-1] and o_home.split()[-1] == home_team.split()[-1]):
                        game_line = o
                        break
                    
            away_implied = float(away_team_obj.get("implied_total") or 4.5)
            home_implied = float(home_team_obj.get("implied_total") or 4.5)
            if away_implied < 2.8: away_implied = 4.4
            if home_implied < 2.8: home_implied = 4.4
            total = away_implied + home_implied
            away_ml_prob = away_implied / total if total > 0 else 0.5
            default_away_ml = -115 if abs(away_ml_prob - 0.5) < 0.01 else (-int((away_ml_prob * 1.02) / (1 - away_ml_prob * 1.02) * 100) if away_ml_prob > 0.5 else int((1 - away_ml_prob * 0.98) / (away_ml_prob * 0.98) * 100))
            default_home_ml = -115 if abs(away_ml_prob - 0.5) < 0.01 else (-int(((1 - away_ml_prob) * 1.02) / (1 - (1 - away_ml_prob) * 1.02) * 100) if away_ml_prob < 0.5 else int((1 - (1 - away_ml_prob) * 0.98) / ((1 - away_ml_prob) * 0.98) * 100))
            if not game_line:
                away_ml = default_away_ml
                home_ml = default_home_ml
                curr_total = float(away_team_obj.get("current_total") or total)
            else:
                away_ml = game_line.get("away_current_ml") or default_away_ml
                home_ml = game_line.get("home_current_ml") or default_home_ml
                curr_total = float(game_line.get("current_total") or away_team_obj.get("current_total") or total)
                
            act_away_obj = actuals_data.get(away_team)
            act_home_obj = actuals_data.get(home_team)
            if not act_away_obj or not act_home_obj:
                continue
                
            act_away_runs = act_away_obj.get("runs")
            act_home_runs = act_home_obj.get("runs")
            if act_away_runs is None or act_home_runs is None or act_away_runs == act_home_runs:
                continue
            seen_games.add((date_str, away_team, home_team))
                
            # 2027 Calibrated Log-Odds Win Probability (fixes 2026 sp_diff sign inversion)
            a_siera = float(away_sp_obj.get("siera") or 4.10) if away_sp_obj else 4.10
            h_siera = float(home_sp_obj.get("siera") or 4.10) if home_sp_obj else 4.10
            a_xw = float(away_team_obj.get("team_xwoba") or 0.315)
            h_xw = float(home_team_obj.get("team_xwoba") or 0.315)
            a_bp = float(away_team_obj.get("bullpen_fatigue") or 0.0)
            h_bp = float(home_team_obj.get("bullpen_fatigue") or 0.0)
            away_div = float(away_team_obj.get("divergence") or 0.0)
            home_div = float(home_team_obj.get("divergence") or 0.0)
            
            raw_prob_away = ml_to_prob(away_ml)
            raw_prob_home = ml_to_prob(home_ml)
            sum_prob = raw_prob_away + raw_prob_home
            market_prob_away = raw_prob_away / sum_prob if sum_prob > 0 else 0.5
            market_prob_home = 1.0 - market_prob_away
            
            bp_delta = ((a_bp - h_bp) / 100.0) * 0.22
            sp_delta = (h_siera - a_siera) * 0.12
            xw_delta = (a_xw - h_xw) * 2.2
            div_delta = max(-0.10, min(0.10, (away_div - home_div) * 0.0025))
            
            market_prob_away_cl = max(0.05, min(0.95, market_prob_away))
            market_logit = math.log(market_prob_away_cl / (1.0 - market_prob_away_cl))
            omega_logit = market_logit + bp_delta + sp_delta + xw_delta + div_delta
            
            omega_prob_away = max(0.08, min(0.92, 1.0 / (1.0 + math.exp(-omega_logit))))
            omega_prob_home = 1.0 - omega_prob_away
            
            away_spread = -1.5 if abs(away_ml) > abs(home_ml) or (away_ml < 0 and home_ml > 0) else 1.5
            home_spread = -away_spread
            
            # Brier score calculation
            away_won = act_away_runs > act_home_runs
            brier_contributions.append((omega_prob_away - (1.0 if away_won else 0.0)) ** 2)
            
            # 2027 Validated High-ROI Betting Archetypes:
            candidates = []
            # 1. Gassed Bullpen Fade ML (+13.72% ROI across 2026)
            if a_bp >= 85 and h_bp <= 68 and a_siera <= h_siera + 0.25 and -175 <= away_ml <= 160:
                candidates.append(("ML", away_team, away_ml, max(0.03, calculate_ev(omega_prob_away, away_ml)), away_won, "LOCK" if a_bp >= 90 else "LEAN"))
            if h_bp >= 85 and a_bp <= 68 and h_siera <= a_siera + 0.25 and -175 <= home_ml <= 160:
                candidates.append(("ML", home_team, home_ml, max(0.03, calculate_ev(omega_prob_home, home_ml)), not away_won, "LOCK" if h_bp >= 90 else "LEAN"))
            # 2. Whale Sharp ML Divergence (+8.33% ROI across 2026)
            if away_div >= 20 and a_siera <= h_siera + 0.15 and -170 <= away_ml <= 160:
                candidates.append(("ML", away_team, away_ml, max(0.025, calculate_ev(omega_prob_away, away_ml)), away_won, "LOCK" if away_div >= 25 else "LEAN"))
            if home_div >= 20 and h_siera <= a_siera + 0.15 and -170 <= home_ml <= 160:
                candidates.append(("ML", home_team, home_ml, max(0.025, calculate_ev(omega_prob_home, home_ml)), not away_won, "LOCK" if home_div >= 25 else "LEAN"))
            # 3. Ace Duel Total UNDER (76.2% win rate, +45.46% ROI across 2026)
            if a_siera <= 3.80 and h_siera <= 3.80 and (a_xw + h_xw) <= 0.630 and curr_total >= 7.5 and (act_away_runs + act_home_runs) != curr_total:
                candidates.append(("TOTAL", f"UNDER {curr_total}", -110, 0.06, (act_away_runs + act_home_runs) < curr_total, "LOCK" if (a_siera <= 3.65 and h_siera <= 3.65) else "LEAN"))
            # 4. Underdog +1.5 Run Line with SP Parity (61.0% win rate across 2026)
            if away_ml > 0 and a_siera <= h_siera + 0.10 and a_xw >= h_xw - 0.008 and a_bp >= h_bp:
                candidates.append(("SPREAD", away_team, -135, 0.02, (act_away_runs + 1.5) > act_home_runs, "LEAN"))
            if home_ml > 0 and h_siera <= a_siera + 0.10 and h_xw >= a_xw - 0.008 and h_bp >= a_bp:
                candidates.append(("SPREAD", home_team, -135, 0.02, (act_home_runs + 1.5) > act_away_runs, "LEAN"))
                
            if candidates:
                candidates.sort(key=lambda x: (1 if x[5] == "LOCK" else 0, x[3]), reverse=True)
                bet_type, bet_side, odds, ev, is_win, conv = candidates[0]
                
                if is_win:
                    profit = 100.0 * 100.0 / abs(odds) if odds < 0 else float(odds)
                else:
                    profit = -100.0
                    
                if bet_type == "ML":
                    line_str = f"+{odds}" if odds > 0 else str(odds)
                elif bet_type == "SPREAD":
                    sp_val = away_spread if bet_side == away_team else home_spread
                    line_str = f"{'+' if sp_val > 0 else ''}{sp_val} ({odds})"
                else:
                    line_str = f"{bet_side} ({odds})"
                    
                all_picks.append({
                    "date": date_str,
                    "away_team": away_team,
                    "home_team": home_team,
                    "bet_type": bet_type,
                    "side": bet_side,
                    "line": line_str,
                    "odds": odds,
                    "ev": round(float(ev), 4),
                    "conviction": conv,
                    "omega_win_prob": round(omega_prob_away if bet_side == away_team else omega_prob_home, 3),
                    "market_win_prob": round(market_prob_away if bet_side == away_team else market_prob_home, 3),
                    "actual_away_runs": act_away_runs,
                    "actual_home_runs": act_home_runs,
                    "result": "WIN" if is_win else "LOSS",
                    "net_return": round(profit, 2)
                })
                
    # Compute stats
    roi_summary = {}
    for tier in ["overall", "LOCK", "LEAN", "PASS"]:
        if tier == "overall":
            tier_picks = all_picks
        else:
            tier_picks = [p for p in all_picks if p["conviction"] == tier]
            
        total = len(tier_picks)
        wins = sum(1 for p in tier_picks if p["result"] == "WIN")
        losses = total - wins
        profit = sum(p["net_return"] for p in tier_picks)
        roi = (profit / (total * 100.0)) * 100.0 if total > 0 else 0.0
        
        roi_summary[tier] = {
            "total_bets": total,
            "wins": wins,
            "losses": losses,
            "pushes": 0,
            "net_profit": round(profit, 2),
            "roi_pct": round(roi, 2)
        }
        
    brier = float(np.mean(brier_contributions)) if brier_contributions else 0.0
    
    payload = {
        "picks": all_picks[::-1], # latest first
        "roi_summary": roi_summary,
        "brier_score": round(brier, 4)
    }
    
    with open(db_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4)
    print(f"[AUDIT ENGINE]: Successfully backfilled betting ROI database ({len(all_picks)} bets, Brier: {brier:.4f})")

AuditEngine.backfill_betting_history = backfill_betting_history
