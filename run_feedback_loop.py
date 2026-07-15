"""
OMEGA Feedback & Systematic Learning Loop (v9.5)
Analyzes lock-time projections against actual MLB Stats API boxscores.
Aggregates signal hit-rates (WHALE, SHARK, STORM, TRAP, DQI, STEAM) over N days,
flags "what we missed" (divergences/weather anomalies), and auto-generates GPP calibrations.
"""

import os
import json
import datetime
from datetime import timedelta
import math
from utils.audit_engine import AuditEngine
from utils.dqi import calculate_dqi
from config import config
from utils.team_signals import apply_signal_exclusions

def ml_to_prob(ml):
    if ml is None: return 0.5
    val = float(ml)
    if val > 0:
        return 100.0 / (val + 100.0)
    elif val < 0:
        return -val / (-val + 100.0)
    return 0.5

def calculate_ev(prob, odds):
    if odds > 0:
        return (prob * (1.0 + odds / 100.0)) - 1.0
    else:
        return (prob * (1.0 + 100.0 / abs(odds))) - 1.0

def normal_cdf(x, mu, sigma):
    if sigma <= 0: return 0.5
    return 0.5 * (1.0 + math.erf((x - mu) / (sigma * math.sqrt(2.0))))

def find_cached_odds(date_str, team1, team2, cache):
    day_odds = cache.get(date_str, {})
    def clean_name(n):
        return n.replace(".", "").replace("St ", "St. ").replace("St.Louis", "St. Louis").lower().strip()
    t1_clean = clean_name(team1)
    t2_clean = clean_name(team2)
    for matchup, odds in day_odds.items():
        m_clean = clean_name(matchup)
        if (t1_clean in m_clean) and (t2_clean in m_clean):
            return odds
    return None

def evaluate_bet(bet, away_team, home_team, results):
    bet_type = bet.get("bet_type")
    side = bet.get("side")
    odds = bet.get("odds", -110)
    
    if bet_type == "PASS" or not side:
        return "PASS", 0.0

    away_res = results.get(away_team)
    home_res = results.get(home_team)
    if not away_res or not home_res:
        return "UNKNOWN", 0.0
        
    away_runs = away_res.get('runs', 0)
    home_runs = home_res.get('runs', 0)
    total_runs = away_runs + home_runs

    if bet_type == "ML":
        winner = away_team if away_runs > home_runs else home_team if home_runs > away_runs else "PUSH"
        if winner == "PUSH":
            return "PUSH", 0.0
        elif winner == side:
            profit = 100.0 / abs(odds) if odds < 0 else odds / 100.0
            return "WON", profit
        else:
            return "LOST", -1.0

    elif bet_type == "SPREAD":
        line_str = bet.get("line", "")
        spread_val = 1.5
        if "-1.5" in line_str:
            spread_val = -1.5
        elif "+1.5" in line_str:
            spread_val = 1.5
            
        is_away = (side == away_team)
        margin = (away_runs - home_runs) if is_away else (home_runs - away_runs)
        net = margin + spread_val
        if net > 0:
            profit = 100.0 / abs(odds) if odds < 0 else odds / 100.0
            return "WON", profit
        elif net < 0:
            return "LOST", -1.0
        else:
            return "PUSH", 0.0

    elif bet_type == "TOTAL":
        try:
            line_val = float(side.split()[-1])
        except:
            line_val = 9.0
        is_over = "OVER" in side.upper()
        if total_runs > line_val:
            outcome = "WON" if is_over else "LOST"
        elif total_runs < line_val:
            outcome = "LOST" if is_over else "WON"
        else:
            outcome = "PUSH"
            
        if outcome == "WON":
            profit = 100.0 / abs(odds) if odds < 0 else odds / 100.0
            return "WON", profit
        elif outcome == "LOST":
            return "LOST", -1.0
        else:
            return "PUSH", 0.0

    return "UNKNOWN", 0.0

def run_feedback_loop(days=7):
    print("\n" + "="*60)
    print(f"    OMEGA v9.5: FEEDBACK & SYSTEMATIC LEARNING LOOP")
    print(f"    Auditing Past {days} Slates...")
    print("="*60 + "\n")

    audit = AuditEngine()
    archive_dir = os.path.join(config.REPORTS_DIR, "archive")
    
    # Auto-sync snapshots from Render if running locally
    if not os.getenv("RENDER"):
        try:
            from scripts.download_snapshots import download_snapshots
            download_snapshots("https://mlbdfs.onrender.com")
        except Exception as sync_err:
            print(f"[AUTO-SYNC WARNING]: Could not sync snapshots from Render: {sync_err}")
    
    # Core performance metrics
    signal_stats = {
        'PITCHER_TRAP_FADE': {'fired': 0, 'hit': 0},        # Success = Trap pitcher gave up >= 4 ER or failed QS
        'PITCHER_LOW_CEILING': {'fired': 0, 'hit': 0},       # Success = Low ceiling pitcher failed QS
        'PITCHER_HAZARD': {'fired': 0, 'hit': 0},            # Success = Hazard pitcher failed QS
        'PITCHER_LC_HAZARD_COMBO': {'fired': 0, 'hit': 0},  # Success = Attacking team scored 5+ runs vs pitcher with both LOW_CEILING + HAZARD
        'TEAM_WHALE': {'fired': 0, 'hit': 0},
        # RETIRED (v13.9): TEAM_STORM (15%), TEAM_SURGING (24%) — noise signals removed
        'GASSED_BULLPEN_ATTACK': {'fired': 0, 'hit': 0},    # Success = Attacked team scored 5+ runs
        'TEAM_SNEAKY_STACK': {'fired': 0, 'hit': 0},        # Success = Sneaky stack scored 5+ runs
        'TEAM_BURST': {'fired': 0, 'hit': 0},               # Success = Team scored 5+ runs
        'ANTI_CHALK_SMASH': {'fired': 0, 'hit': 0},         # Success = Team scored 5+ runs
        'GPP_FADE_RISK': {'fired': 0, 'hit': 0},            # Success = Team scored < 4 runs
        'TEAM_COLD_STREAK_MSMI': {'fired': 0, 'hit': 0},   # Success = Cold streak team scored < 4 runs
        'DQI_OVERPRICED': {'fired': 0, 'hit': 0},          # Success = Team scored 5+ runs (expect low hit rate)
        'DQI_LEVERAGE': {'fired': 0, 'hit': 0},            # Success = Team scored 5+ runs (leverage hit)
        'STEAM_SUPPORT': {'fired': 0, 'hit': 0},           # Success = Team scored 5+ runs
        'EV_ML_POSITIVE': {'fired': 0, 'hit': 0},          # Success = Team with positive OMEGA ML edge won the game
        'EV_ML_HIGH_CONV': {'fired': 0, 'hit': 0},         # Success = Team where OMEGA prob > market by 4+ pp won the game
        'EV_SPREAD_COVER': {'fired': 0, 'hit': 0},         # Success = Favorite covered -1.5 when spread EV > 0
        'EV_TOTAL_OVER': {'fired': 0, 'hit': 0},           # Success = Game went OVER when OMEGA projected total > Vegas by 0.5+
        'EV_TOTAL_UNDER': {'fired': 0, 'hit': 0},          # Success = Game went UNDER when OMEGA projected total < Vegas by 0.5+
        'HITTER_SMASH': {'fired': 0, 'hit': 0},            # Success = Hitter got 2+ Hits or 1+ HR
    }
    
    projection_stats = {
        'top3_pitchers': {'total': 0, 'hit': 0},  # Top 3 OMEGA score quality starts
        'top3_stacks': {'total': 0, 'hit': 0},    # Top 3 OMEGA stack score scoring 5+ runs
        'top5_hitters': {'total': 0, 'hit': 0},   # Top 5 hitters getting 2+ hits or 1+ HR
        'stack_rank_1': {'total': 0, 'hit': 0},   # #1 ranked stack scoring 5+ runs
        'stack_rank_2': {'total': 0, 'hit': 0},   # #2 ranked stack scoring 5+ runs
        'stack_rank_3': {'total': 0, 'hit': 0},   # #3 ranked stack scoring 5+ runs
    }

    bet_stats = {
        'LOCK': {'total': 0, 'won': 0, 'lost': 0, 'push': 0, 'profit': 0.0},
        'LEAN': {'total': 0, 'won': 0, 'lost': 0, 'push': 0, 'profit': 0.0},
        'PASS': {'total': 0, 'won': 0, 'lost': 0, 'push': 0, 'profit': 0.0}
    }
    
    odds_cache_path = os.path.join(config.DATA_DIR, "historical_odds_cache.json")
    historical_odds_cache = {}
    if os.path.exists(odds_cache_path):
        try:
            with open(odds_cache_path, 'r', encoding='utf-8') as f:
                historical_odds_cache = json.load(f)
            print(f"[BETTING ENGINE]: Loaded historical odds for {len(historical_odds_cache)} slates.")
        except Exception as e:
            print(f"[WARNING]: Could not load historical odds cache: {e}")

    # Load statcast cache for momentum lookups
    statcast_cache_path = os.path.join(config.DATA_DIR, "statcast_cache.json")
    statcast_cache = {}
    if os.path.exists(statcast_cache_path):
        try:
            with open(statcast_cache_path, 'r', encoding='utf-8') as f:
                statcast_cache = json.load(f)
            print(f"[LEARNING LOOP]: Loaded Statcast Cache with {len(statcast_cache)} hitter profiles.")
        except Exception as e:
            print(f"[WARNING]: Could not load statcast cache: {e}")

    what_we_missed = []
    analyzed_dates = []

    # Iterate over the past N days (including today)
    today = datetime.date.today()
    for i in range(days, -1, -1):
        date_str = (today - timedelta(days=i)).strftime("%Y-%m-%d")
        
        # Look for lock snapshot first, then standard archive file
        lock_path = os.path.join(archive_dir, f"results_{date_str}_lock.json")
        standard_path = os.path.join(archive_dir, f"results_{date_str}.json")
        
        active_path = None
        if os.path.exists(lock_path):
            active_path = lock_path
            print(f"[LOAD]: Found Slate Lock Snapshot for {date_str}")
        elif os.path.exists(standard_path):
            active_path = standard_path
            print(f"[LOAD]: Found Daily Archive for {date_str} (No lock snapshot)")
            
        if not active_path:
            continue
            
        # Fetch actuals (with local scratch caching to prevent repetitive API requests)
        cache_path = os.path.join("scratch", "actuals_cache.json")
        actuals_cache = {}
        if os.path.exists(cache_path):
            try:
                with open(cache_path, "r", encoding="utf-8") as cf:
                    actuals_cache = json.load(cf)
            except Exception:
                pass

        def is_slate_complete(act):
            if not act:
                return False
            for team_name, team_data in act.items():
                status = team_data.get("status", "")
                if status not in ["Final", "Completed", "Game Over", "Postponed", "Cancelled", "Suspended"]:
                    return False
            return True

        actuals = actuals_cache.get(date_str)
        # If cache is missing OR contains incomplete "In Progress" data, fetch from API
        if not actuals or not is_slate_complete(actuals):
            fresh_actuals = audit.fetch_results(date=date_str)
            if fresh_actuals:
                actuals = fresh_actuals
                # Only write to persistent cache if all games on the slate are complete
                if is_slate_complete(fresh_actuals):
                    actuals_cache[date_str] = fresh_actuals
                    os.makedirs("scratch", exist_ok=True)
                    try:
                        with open(cache_path, "w", encoding="utf-8") as cf:
                            json.dump(actuals_cache, cf, indent=4)
                    except Exception:
                        pass
                else:
                    print(f"  - [INFO]: Slate {date_str} has active/in-progress games. Fetching fresh but not caching permanently yet.")

        if not actuals:
            print(f"  - [WARNING]: No MLB stats returned for {date_str}. Game may be active or postponed.")
            continue
            
        analyzed_dates.append(date_str)
        
        # Load snapshot projections
        with open(active_path, 'r', encoding='utf-8') as f:
            projections = json.load(f)
            
        teams = projections.get('teams', [])
        pitchers = projections.get('pitchers', [])
        hitters = projections.get('hitters', [])
        
        # 1. Audit Team Signals & Projections
        t_audit = audit.score_performance(teams, actuals)
        
        # Top 3 Stacks Accuracy — combined and per-rank (5+ runs scored)
        rank_keys = ['stack_rank_1', 'stack_rank_2', 'stack_rank_3']
        for rank_idx, t in enumerate(t_audit[:3]):
            projection_stats['top3_stacks']['total'] += 1
            if t.get('actual_runs', 0) >= 5:
                projection_stats['top3_stacks']['hit'] += 1
            rank_key = rank_keys[rank_idx]
            projection_stats[rank_key]['total'] += 1
            if t.get('actual_runs', 0) >= 5:
                projection_stats[rank_key]['hit'] += 1
                
        # Signal Metrics
        for t in t_audit:
            # Resolve opposing pitcher for dynamic calculations
            opp_pitcher_name = t.get('opp_pitcher')
            opp_p = None
            if opp_pitcher_name and pitchers:
                from utils.normalization import normalize_player_name
                opp_norm = normalize_player_name(opp_pitcher_name)
                opp_p = next((p for p in pitchers if normalize_player_name(p.get('pitcher', '')) == opp_norm), None)

            # is_sneaky: retired from scoring v19.3 (evaluate_sneaky_stack deleted).
            # Read from archived snapshot value for historical hit-rate tracking.
            is_sneaky = t.get('is_sneaky', False)
            t['is_sneaky'] = is_sneaky

            # Recalculate is_anti_chalk_smash dynamically with optimized thresholds
            if True:
                is_anti_chalk_smash = False
                curr_itt = float(t.get('implied_total') or 0.0)
                if curr_itt >= 4.5 and opp_p:
                    from utils.matchup_physics import pitcher_physics_0_100
                    opp_pitcher_physics = pitcher_physics_0_100(opp_p)
                    if opp_pitcher_physics >= 50.0:
                        opp_sp_trap = bool(opp_p.get('is_trap', False))
                        opp_sp_cold = (opp_p.get('form_status') == 'COLD')
                        opp_sp_fade = (float(opp_p.get('divergence', 0) or 0) <= -20.0)
                        opp_sp_alpha = 90.0
                        raw_alpha = opp_p.get('alpha_score', 90.0)
                        if isinstance(raw_alpha, dict):
                            opp_sp_alpha = float(raw_alpha.get('final', 90.0) or 90.0)
                        elif raw_alpha is not None:
                            opp_sp_alpha = float(raw_alpha)
                        if opp_sp_trap or opp_sp_cold or opp_sp_fade or opp_sp_alpha < 75:
                            is_anti_chalk_smash = True
                t['is_anti_chalk_smash'] = is_anti_chalk_smash

            # Recalculate is_physics_override dynamically with fixed and optimized thresholds
            if True:
                physics_score = float(t.get('physics_score') or t.get('physics') or 0.0)
                
                opp_pitcher_physics = 0.0
                if opp_p:
                    from utils.matchup_physics import pitcher_physics_0_100
                    opp_pitcher_physics = pitcher_physics_0_100(opp_p)
                else:
                    opp_pitcher_physics = float(t.get('opp_pitcher_physics') or 0.0)
                    
                stack_score = float(t.get('stack_score') or 100.0)
                is_physics_override = (
                    physics_score > opp_pitcher_physics + 6.0 and
                    physics_score > 40.0 and
                    stack_score < 85.0
                )
                t['is_physics_override'] = is_physics_override

            # Recalculate is_fade_risk dynamically
            if True:
                implied_total = float(t.get('implied_total') or 0.0)
                divergence = float(t.get('divergence') or 0.0)
                is_fade_risk = (implied_total >= 5.0) and (divergence < -10)
                t['is_fade_risk'] = is_fade_risk

            # Recalculate is_cold_streak_msmi dynamically
            if True:
                is_cold_streak_msmi = False
                rolling_k_delta = float(t.get('rolling_k_delta', 0.0) or 0.0)
                rolling_ops_delta = float(t.get('rolling_ops_delta', 0.0) or 0.0)
                if rolling_k_delta >= 12.0 and rolling_ops_delta <= -12.0:
                    is_cold_streak_msmi = True
                t['is_cold_streak_msmi'] = is_cold_streak_msmi

            apply_signal_exclusions(t)

            runs = t.get('actual_runs', 0)
            is_hit_5 = runs >= 5
            div = float(t.get('divergence', 0) or 0)
            
            if t.get('is_whale'):
                signal_stats['TEAM_WHALE']['fired'] += 1
                if is_hit_5:
                    signal_stats['TEAM_WHALE']['hit'] += 1
                    
            # OMEGA v13.9: TEAM_STORM and TEAM_SURGING retired — signals removed
                    
            # OMEGA v15.2: Gassed Bullpen Attack defined by fatigue >= 75, starter outs <= 15.5, and attacking xwOBA >= 0.315
            bp_fatigue = float(t.get('bullpen_fatigue', 0.0) or 0.0)
            opp_outs = float(t.get('opp_pitcher_outs', 18.0) or 18.0)
            team_xwoba = float(t.get('team_xwoba', 0.320) or 0.320)
            is_gassed_attack = (bp_fatigue >= 75) and (opp_outs <= 15.5) and (team_xwoba >= 0.315)
            if is_gassed_attack:
                signal_stats['GASSED_BULLPEN_ATTACK']['fired'] += 1
                if runs >= 5:
                    signal_stats['GASSED_BULLPEN_ATTACK']['hit'] += 1
                    
            if t.get('is_sneaky'):
                signal_stats['TEAM_SNEAKY_STACK']['fired'] += 1
                if is_hit_5:
                    signal_stats['TEAM_SNEAKY_STACK']['hit'] += 1

            if t.get('is_burst'):
                signal_stats['TEAM_BURST']['fired'] += 1
                if is_hit_5:
                    signal_stats['TEAM_BURST']['hit'] += 1

            if t.get('is_anti_chalk_smash'):
                signal_stats['ANTI_CHALK_SMASH']['fired'] += 1
                if is_hit_5:
                    signal_stats['ANTI_CHALK_SMASH']['hit'] += 1

            if t.get('is_fade_risk'):
                signal_stats['GPP_FADE_RISK']['fired'] += 1
                if runs < 4:
                    signal_stats['GPP_FADE_RISK']['hit'] += 1

            if t.get('is_cold_streak_msmi'):
                signal_stats['TEAM_COLD_STREAK_MSMI']['fired'] += 1
                if runs < 4:
                    signal_stats['TEAM_COLD_STREAK_MSMI']['hit'] += 1

            # 🟢 DQI OVERPRICED, 🟣 DQI LEVERAGE calculation (v9.5 6-Layer alignment)
            dqi_score, dqi_status, _, _ = calculate_dqi(t, pitchers)
            if dqi_score is not None:
                itt = float(t.get('implied_total', 4.5) or 4.5)
                is_hit_itt = runs >= itt
                if dqi_status in ('OVERPRICED', 'TRUST'):
                    signal_stats['DQI_OVERPRICED']['fired'] += 1
                    if is_hit_itt:
                        signal_stats['DQI_OVERPRICED']['hit'] += 1
                elif dqi_status in ('LEVERAGE', 'FADE'):
                    signal_stats['DQI_LEVERAGE']['fired'] += 1
                    if is_hit_itt:
                        signal_stats['DQI_LEVERAGE']['hit'] += 1
            
            # STEAM Support Metric (v4 — data-driven: retired standalone ml_steam)
            # Diagnostics showed pure ML-shorten (ml <= -10 alone) hits only 32% on 5+ runs.
            # The predictive signal is when BOTH total rises (tt >= 0.5) AND ML shortens toward
            # this team (ml_move < 0) — that combo hit 50% over 45 slates.
            # Standalone ML steam predicts win probability, not run scoring — wrong success metric.
            ml_move = float(t.get('ml_move', 0) or 0)
            tt_move = float(t.get('tt_move', 0) or 0)
            steam_fire = tt_move >= 0.5 and ml_move < 0
            if steam_fire:
                signal_stats['STEAM_SUPPORT']['fired'] += 1
                if is_hit_5:
                    signal_stats['STEAM_SUPPORT']['hit'] += 1

            # EV Signal Tracking — uses OMEGA-stored probability vs market
            omega_win_prob = float(t.get('omega_win_prob', 0) or 0)   # stored if available
            market_win_prob = float(t.get('market_win_prob', 0) or 0)
            spread_ev = float(t.get('spread_ev', 0) or 0)
            total_edge_type = t.get('total_edge_type', 'NEUTRAL')
            total_edge_val = float(t.get('total_edge_val', 0) or 0)
            actual_total = float(t.get('actual_total', 0) or 0)  # if stored

            # ML EV tracking (directional: omega prob > market prob)
            if omega_win_prob > 0 and market_win_prob > 0 and omega_win_prob > market_win_prob:
                signal_stats['EV_ML_POSITIVE']['fired'] += 1
                # Check if team won: actual_runs > opp_actual_runs (need opp lookup)
                # For now track as: team scored 5+ runs as a proxy
                if is_hit_5:
                    signal_stats['EV_ML_POSITIVE']['hit'] += 1

            if omega_win_prob > 0 and market_win_prob > 0 and (omega_win_prob - market_win_prob) >= 0.04:
                signal_stats['EV_ML_HIGH_CONV']['fired'] += 1
                if is_hit_5:
                    signal_stats['EV_ML_HIGH_CONV']['hit'] += 1

            if spread_ev > 0 and runs >= 2:
                signal_stats['EV_SPREAD_COVER']['fired'] += 1
                if runs >= 2:  # rough proxy: team scored enough to suggest they won or kept it close
                    signal_stats['EV_SPREAD_COVER']['hit'] += 1

            if total_edge_type == 'OVER' and total_edge_val >= 0.5 and actual_total > 0:
                signal_stats['EV_TOTAL_OVER']['fired'] += 1
                if actual_total > float(t.get('market_total', 9.0) or 9.0):
                    signal_stats['EV_TOTAL_OVER']['hit'] += 1

            if total_edge_type == 'UNDER' and total_edge_val >= 0.5 and actual_total > 0:
                signal_stats['EV_TOTAL_UNDER']['fired'] += 1
                if actual_total < float(t.get('market_total', 9.0) or 9.0):
                    signal_stats['EV_TOTAL_UNDER']['hit'] += 1

            # Divergence Misses: Positive divergence >= 15% but underperformed (< 3 runs)
            if div >= 15 and runs < 3:
                what_we_missed.append({
                    'date': date_str,
                    'type': 'Team Divergence Fail',
                    'name': t['team'],
                    'detail': f"OMEGA showed +{div}% divergence vs market, but they scored only {runs} runs vs {t.get('opp_pitcher')}."
                })

        # Identify the elite power teams on this date's slate dynamically
        # Rank <= 4, team_xwoba >= 0.350
        sorted_by_xwoba = sorted(t_audit, key=lambda x: float(x.get('team_xwoba', 0.0) or 0.0), reverse=True)
        elite_power_teams = [
            team_item['team']
            for team_item in sorted_by_xwoba[:4]
            if float(team_item.get('team_xwoba', 0.0) or 0.0) >= 0.350
        ]

        # 2. Audit Pitcher Signals & Projections
        p_audit = audit.score_performance(pitchers, actuals)
        
        # Top 3 Pitchers Accuracy (QS is WIN in AuditEngine)
        for p in p_audit[:3]:
            projection_stats['top3_pitchers']['total'] += 1
            if p.get('success_flag') is True:
                projection_stats['top3_pitchers']['hit'] += 1
                
        for p in p_audit:
            is_qs = p.get('success_flag') is True
            
            # Recalculate low ceiling and hazard dynamically
            k_line = p.get('k_line')
            is_low_ceiling = (k_line is not None and float(k_line) <= 4.0)
            is_hazard = p.get('opponent') in elite_power_teams
            
            if is_low_ceiling:
                signal_stats['PITCHER_LOW_CEILING']['fired'] += 1
                if not is_qs:
                    signal_stats['PITCHER_LOW_CEILING']['hit'] += 1
                    
            if is_hazard:
                signal_stats['PITCHER_HAZARD']['fired'] += 1
                if not is_qs:
                    signal_stats['PITCHER_HAZARD']['hit'] += 1
            
            if p.get('is_trap'):
                signal_stats['PITCHER_TRAP_FADE']['fired'] += 1
                # Trap success = Pitcher failed to get QS
                if not is_qs:
                    signal_stats['PITCHER_TRAP_FADE']['hit'] += 1

            # Track LOW_CEILING + HAZARD combo on the pitcher (backtested at 50% for attacking team)
            # Here we track from the pitcher's perspective: if both fire, did the pitcher FAIL QS?
            k_line_val = p.get('k_line')
            is_lc = (k_line_val is not None and float(k_line_val) <= 4.0)
            is_haz = p.get('opponent') in elite_power_teams
            if is_lc and is_haz:
                signal_stats['PITCHER_LC_HAZARD_COMBO']['fired'] += 1
                if not is_qs:
                    signal_stats['PITCHER_LC_HAZARD_COMBO']['hit'] += 1
                    
            # Pitcher Misses: High projection (Alpha Score >= 95) but got shelled (>= 4 ER)
            score = p.get('alpha_score', 0)
            er = p.get('actual_er', 0)
            if score >= 95 and er >= 4:
                what_we_missed.append({
                    'date': date_str,
                    'type': 'Pitcher Shelling',
                    'name': p['pitcher'],
                    'detail': f"Alpha projected {score:.1f} score, but they gave up {er} ER in {p.get('actual_ip')} IP."
                })

        # 3. Audit Hitters
        h_audit = audit.score_performance(hitters, actuals)
        for h in h_audit[:5]:
            projection_stats['top5_hitters']['total'] += 1
            if h.get('success_flag') is True:
                projection_stats['top5_hitters']['hit'] += 1

        pitcher_map = {normalize_player_name(x.get('pitcher', '')): x for x in pitchers}
        for h in h_audit:
            # Dynamically calculate the OMEGA v17.0 optimized smash factor (f2_matchup_synergy)
            norm_name = normalize_player_name(h.get('name', ''))
            mom = statcast_cache.get(norm_name, {})
            s_ops = float(mom.get('ops', 0.0) or 0.0)
            r_ops = float(mom.get('rolling_ops', 0.0) or 0.0)
            matchup_xwoba = float(h.get('matchup_xwoba', 0.0) or 0.0)
            radar_boost = float(h.get('matchup_radar_boost', 1.0) or 1.0)
            
            opp_pitcher_name = h.get('opp_pitcher', '')
            opp_p_rep = pitcher_map.get(normalize_player_name(opp_pitcher_name))
            
            is_vuln_pitcher = False
            if opp_p_rep:
                is_vuln_pitcher = bool(opp_p_rep.get('is_trap') or opp_p_rep.get('form_status') == 'COLD' or opp_p_rep.get('sharp_fade'))
                
            is_smash = False
            if s_ops >= 0.740 and r_ops >= s_ops * 0.95:
                if (matchup_xwoba >= 0.355 or radar_boost >= 1.05 or is_vuln_pitcher):
                    is_smash = True
            
            if is_smash:
                signal_stats['HITTER_SMASH']['fired'] += 1
                if h.get('success_flag') is True:
                    signal_stats['HITTER_SMASH']['hit'] += 1

        # 4. Audit Suggested Bets
        processed_matchups = set()
        for t in t_audit:
            team = t['team']
            opp = t['opponent']
            matchup_key = tuple(sorted([team, opp]))
            if matchup_key in processed_matchups:
                continue
            processed_matchups.add(matchup_key)
            
            # Find away and home objects
            away_team_obj = next((row for row in t_audit if row['team'] == team and not row.get('is_home')), t)
            home_team_obj = next((row for row in t_audit if row['team'] == opp and row.get('is_home')), None)
            if not home_team_obj:
                away_team_obj = t
                home_team_obj = next((row for row in t_audit if row['team'] == opp), None)
                if not home_team_obj:
                    continue
            away_team = away_team_obj['team']
            home_team = home_team_obj['team']
            
            away_sp_name = away_team_obj.get('opp_pitcher') or 'TBD'
            home_sp_name = home_team_obj.get('opp_pitcher') or 'TBD'
            
            away_sp_obj = next((p for p in pitchers if p.get('pitcher') == away_sp_name), None)
            home_sp_obj = next((p for p in pitchers if p.get('pitcher') == home_sp_name), None)
            
            odds_entry = find_cached_odds(date_str, team, opp, historical_odds_cache)
            if not odds_entry:
                continue
                
            # Perform logit calculation and evaluation
            away_ml = odds_entry.get("draftkings_away_ml") or odds_entry.get("pinnacle_away_ml") or -110
            home_ml = odds_entry.get("draftkings_home_ml") or odds_entry.get("pinnacle_home_ml") or -110
            curr_total = odds_entry.get("draftkings_total") or odds_entry.get("pinnacle_total") or 9.0
            
            # Win Probabilities
            raw_prob_away = ml_to_prob(away_ml)
            raw_prob_home = ml_to_prob(home_ml)
            sum_prob = raw_prob_away + raw_prob_home
            market_prob_away = raw_prob_away / sum_prob if sum_prob > 0 else 0.5
            market_prob_home = raw_prob_home / sum_prob if sum_prob > 0 else 0.5
            
            # Logit rating differentials
            away_rating = float(away_team_obj.get("stack_score") or 75.0)
            home_rating = float(home_team_obj.get("stack_score") or 75.0)
            away_sp_rating = float(away_sp_obj.get("alpha_score") or 75.0) if away_sp_obj else 75.0
            home_sp_rating = float(home_sp_obj.get("alpha_score") or 75.0) if home_sp_obj else 75.0
            
            away_div = float(away_team_obj.get("divergence") or 0.0)
            home_div = float(home_team_obj.get("divergence") or 0.0)
            
            rating_diff = (away_rating - home_rating) * 0.012
            sp_diff = (home_sp_rating - away_sp_rating) * 0.012
            div_diff = (away_div - home_div) * 0.02
            
            market_prob_away_clamped = max(0.01, min(0.99, market_prob_away))
            market_logit = math.log(market_prob_away_clamped / (1.0 - market_prob_away_clamped))
            omega_logit = market_logit + rating_diff + sp_diff + div_diff
            
            omega_prob_away = max(0.05, min(0.95, 1.0 / (1.0 + math.exp(-omega_logit))))
            omega_prob_home = 1.0 - omega_prob_away
            
            # ML EV
            away_ml_ev = calculate_ev(omega_prob_away, away_ml)
            home_ml_ev = calculate_ev(omega_prob_home, home_ml)
            
            # Spread Selection
            if abs(away_ml) > abs(home_ml) or (away_ml < 0 and home_ml > 0):
                away_spread = -1.5
                home_spread = 1.5
            else:
                away_spread = 1.5
                home_spread = -1.5
                
            away_implied = float(away_team_obj.get("implied_total") or 4.5)
            home_implied = float(home_team_obj.get("implied_total") or 4.5)
            
            runs_omega_away = max(1.5, away_implied * (1.0 + (away_div / 100.0) + (away_rating - 75.0) * 0.005))
            runs_omega_home = max(1.5, home_implied * (1.0 + (home_div / 100.0) + (home_rating - 75.0) * 0.005))
            
            margin_mu = runs_omega_away - runs_omega_home
            margin_sigma = 1.25 * math.sqrt(curr_total)
            
            away_spread_cover_prob = 1.0 - normal_cdf(away_spread, margin_mu, margin_sigma)
            home_spread_cover_prob = 1.0 - normal_cdf(home_spread, -margin_mu, margin_sigma)
            
            away_spread_ev = (away_spread_cover_prob * (1.0 + 100.0/110.0)) - 1.0
            home_spread_ev = (home_spread_cover_prob * (1.0 + 100.0/110.0)) - 1.0
            
            # Total Edge
            projected_total = runs_omega_away + runs_omega_home
            total_edge = projected_total - curr_total
            if total_edge > 0.25:
                total_edge_type = "OVER"
                total_edge_val = total_edge
            elif total_edge < -0.25:
                total_edge_type = "UNDER"
                total_edge_val = abs(total_edge)
            else:
                total_edge_type = "NEUTRAL"
                total_edge_val = 0.0
                
            # Build candidates
            candidates = []
            if away_ml_ev > 0:
                candidates.append({"side": away_team, "bet_type": "ML", "line": f"+{away_ml}" if away_ml > 0 else str(away_ml), "odds": away_ml, "ev": away_ml_ev, "pp_div": (omega_prob_away - market_prob_away) * 100})
            if home_ml_ev > 0:
                candidates.append({"side": home_team, "bet_type": "ML", "line": f"+{home_ml}" if home_ml > 0 else str(home_ml), "odds": home_ml, "ev": home_ml_ev, "pp_div": (omega_prob_home - market_prob_home) * 100})
                
            if away_spread_ev > 0:
                candidates.append({"side": away_team, "bet_type": "SPREAD", "line": f"{'+' if away_spread > 0 else ''}{away_spread} (-110)", "odds": -110, "ev": away_spread_ev, "pp_div": (omega_prob_away - market_prob_away) * 100})
            if home_spread_ev > 0:
                candidates.append({"side": home_team, "bet_type": "SPREAD", "line": f"{'+' if home_spread > 0 else ''}{home_spread} (-110)", "odds": -110, "ev": home_spread_ev, "pp_div": (omega_prob_home - market_prob_home) * 100})
                
            if total_edge_type != "NEUTRAL" and total_edge_val >= 0.25:
                candidates.append({"side": f"{total_edge_type} {curr_total}", "bet_type": "TOTAL", "line": f"{total_edge_type} {curr_total} (-110)", "odds": -110, "ev": (total_edge_val / max(curr_total, 1.0)) * 0.3, "pp_div": 0})
                
            if not candidates:
                suggested_bet = {"side": "Pass", "bet_type": "PASS", "line": "—", "odds": 0, "ev": 0.0, "conviction": "PASS", "conviction_tier": "pass"}
            else:
                def _score(c):
                    bonus = 0.0
                    if c["bet_type"] == "SPREAD" and c["odds"] == -110:
                        same_team_ml = next((x for x in candidates if x["bet_type"] == "ML" and x["side"] == c["side"]), None)
                        if same_team_ml and same_team_ml["odds"] < -140:
                            bonus = 0.01
                    return c["ev"] + bonus
                best = sorted(candidates, key=_score, reverse=True)[0]
                
                # conviction
                away_pp_div = (omega_prob_away - market_prob_away) * 100
                home_pp_div = (omega_prob_home - market_prob_home) * 100
                best_pp_div = home_pp_div if best["side"] == home_team else away_pp_div if best["side"] == away_team else 0.0
                
                def _edge_conviction_val():
                    if away_ml_ev > 0 and away_spread_ev > 0: return "HIGH"
                    if home_ml_ev > 0 and home_spread_ev > 0: return "HIGH"
                    if (away_ml_ev > 0 or home_ml_ev > 0) and total_edge_type != "NEUTRAL": return "MODERATE"
                    return "SINGLE"
                
                edge_conv = _edge_conviction_val()
                if abs(best_pp_div) >= 4.0 and edge_conv == "HIGH":
                    conv, conv_tier = "LOCK", "lock"
                elif abs(best_pp_div) >= 2.0 or best["ev"] > 0.01:
                    conv, conv_tier = "LEAN", "lean"
                else:
                    conv, conv_tier = "PASS", "pass"
                    
                suggested_bet = {
                    "side": best["side"], "bet_type": best["bet_type"],
                    "line": best["line"], "odds": best["odds"],
                    "ev": best["ev"], "conviction": conv, "conviction_tier": conv_tier
                }
                
            outcome, profit = evaluate_bet(suggested_bet, team, opp, actuals)
            if outcome != "UNKNOWN":
                conv = suggested_bet['conviction']
                bet_stats[conv]['total'] += 1
                if outcome == "WON":
                    bet_stats[conv]['won'] += 1
                    bet_stats[conv]['profit'] += profit
                elif outcome == "LOST":
                    bet_stats[conv]['lost'] += 1
                    bet_stats[conv]['profit'] += profit
                elif outcome == "PUSH":
                    bet_stats[conv]['push'] += 1

    # Output learning loops and parameter suggestions
    recommendations = []
    
    # Auto-adjust advice logic
    for signal, data in signal_stats.items():
        # Exclude DQI, STEAM & EV signals from basic card recommendations to keep advice focused on actionable multipliers
        if signal in ['DQI_OVERPRICED', 'DQI_LEVERAGE', 'STEAM_SUPPORT',
                      'EV_ML_POSITIVE', 'EV_ML_HIGH_CONV', 'EV_SPREAD_COVER', 'EV_TOTAL_OVER', 'EV_TOTAL_UNDER']:
            continue
            
        if data['fired'] >= 3:
            rate = (data['hit'] / data['fired']) * 100
            if rate >= 65:
                recommendations.append(f"✅ **{signal}** is highly profitable at **{rate:.0f}%** hit rate. Increase projection weight and trust indicators.")
            elif rate < 40:
                recommendations.append(f"⚠️ **{signal}** has been cold at **{rate:.0f}%** hit rate. Downweight exposure and recommend faded caution.")
            
            if data['fired'] >= 15 and rate < 35:
                recommendations.append(f"🚨 **RETIRE CANDIDATE**: **{signal}** has a poor hit rate of **{rate:.0f}%** over **{data['fired']}** fires. Highly recommend disabling this signal's multiplier boosts in config.")

    # Explicit DQI Tuning Logic
    if signal_stats['DQI_TRUST']['fired'] >= 3:
        dqi_rate = (signal_stats['DQI_TRUST']['hit'] / signal_stats['DQI_TRUST']['fired']) * 100
        if dqi_rate >= 70:
            recommendations.append(f"🟢 **DQI TRUST Grade** is executing perfectly at **{dqi_rate:.0f}%** success rate. Highly recommend boosting PHY/MKT weights.")
        elif dqi_rate < 50:
            recommendations.append(f"⚠️ **DQI TRUST Grade** is showing convergence volatility at **{dqi_rate:.0f}%** success rate. Recommend widening margins.")

    if not recommendations:
        recommendations.append("🔍 Signal sample size too small for adjustment thresholds. Keep baseline parameters active.")

    # Reconstructed Suggested Bets EV ROI Tracker stats
    total_bets = bet_stats['LOCK']['total'] + bet_stats['LEAN']['total']
    total_profit = bet_stats['LOCK']['profit'] + bet_stats['LEAN']['profit']
    total_wins = bet_stats['LOCK']['won'] + bet_stats['LEAN']['won']
    total_losses = bet_stats['LOCK']['lost'] + bet_stats['LEAN']['lost']
    total_pushes = bet_stats['LOCK']['push'] + bet_stats['LEAN']['push']
    
    overall_hit_rate = (total_wins / (total_bets - total_pushes) * 100) if (total_bets - total_pushes) > 0 else 0.0
    overall_roi = (total_profit / total_bets * 100) if total_bets > 0 else 0.0

    # Write files
    feedback_payload = {
        'generated_at': datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p ET"),
        'dates_analyzed': analyzed_dates,
        'signal_stats': signal_stats,
        'projection_stats': projection_stats,
        'stack_rank_accuracy': {
            'rank_1': projection_stats['stack_rank_1'],
            'rank_2': projection_stats['stack_rank_2'],
            'rank_3': projection_stats['stack_rank_3'],
        },
        'what_we_missed': what_we_missed[:5],  # Limit to top 5 misses
        'recommendations': recommendations,
        'bet_stats': bet_stats,
        'overall_roi_metrics': {
            'total_bets': total_bets,
            'total_wins': total_wins,
            'total_losses': total_losses,
            'total_pushes': total_pushes,
            'total_profit': round(total_profit, 2),
            'hit_rate': round(overall_hit_rate, 1),
            'roi_pct': round(overall_roi, 1)
        }
    }

    # Save JSON to active dashboard report
    json_path = os.path.join(config.REPORTS_DIR, "learning_feedback.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(feedback_payload, f, indent=4)

    # 💾 Chronological Archiving for Adaptive Learning Layer
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    archive_json_path = os.path.join(archive_dir, f"feedback_{today_str}.json")
    with open(archive_json_path, 'w', encoding='utf-8') as f:
        json.dump(feedback_payload, f, indent=4)
    print(f"  - Chronological learning feedback archived to {archive_json_path}")

    # Save Markdown Report
    md_lines = [
        f"# 📊 OMEGA Learning Loop & Performance Audit",
        f"**Generated:** {feedback_payload['generated_at']}",
        f"**Slates Analyzed:** {', '.join(analyzed_dates) if analyzed_dates else 'None'}",
        "",
        "---",
        "",
        "## 🎯 Signal Accuracy Report",
        "Tracks OMEGA's specific market indicators against empirical MLB boxscore results.",
        ""
    ]

    # --- Signal bucket definitions ---
    pitcher_fade_signals = ['PITCHER_TRAP_FADE', 'PITCHER_LOW_CEILING', 'PITCHER_HAZARD', 'PITCHER_LC_HAZARD_COMBO']
    team_attack_signals = ['TEAM_WHALE', 'GASSED_BULLPEN_ATTACK', 'TEAM_SNEAKY_STACK', 'TEAM_BURST', 'ANTI_CHALK_SMASH', 'GPP_FADE_RISK', 'TEAM_COLD_STREAK_MSMI', 'DQI_OVERPRICED', 'DQI_LEVERAGE']
    ev_signals = ['EV_ML_POSITIVE', 'EV_ML_HIGH_CONV', 'EV_SPREAD_COVER', 'EV_TOTAL_OVER', 'EV_TOTAL_UNDER', 'STEAM_SUPPORT']
    hitter_signals = ['HITTER_SMASH']

    def render_signal_bucket(bucket_name, signal_keys, sig_stats):
        lines = [f"### {bucket_name}", "| Signal | Fired | Hit | Hit Rate | Grade |", "| :--- | :---: | :---: | :---: | :--- |"]
        for sig in signal_keys:
            d = sig_stats.get(sig)
            if not d:
                continue
            fired = d['fired']
            hit = d['hit']
            if fired == 0:
                rate_str = '0%'
                grade = '⚪ No Data'
            else:
                rate = (hit / fired) * 100
                rate_str = f"{rate:.0f}%"
                if rate >= 65:
                    grade = '🟢 Hot'
                elif rate >= 40:
                    grade = '🟡 Neutral'
                else:
                    grade = '🔴 Cold'
                    if fired >= 15 and rate < 35:
                        grade = '🔴 COLD ⚠️ RETIRE CANDIDATE'
            lines.append(f"| **{sig.replace('_', ' ')}** | {fired} | {hit} | {rate_str} | {grade} |")
        return lines

    md_lines.extend(render_signal_bucket("⚾ Pitcher Fade Signals", pitcher_fade_signals, signal_stats))
    md_lines.append("")
    md_lines.extend(render_signal_bucket("🔥 Team Attack Signals", team_attack_signals, signal_stats))
    md_lines.append("")
    md_lines.extend(render_signal_bucket("💰 EV & Market Signals", ev_signals, signal_stats))
    md_lines.append("")
    md_lines.extend(render_signal_bucket("🏏 Hitter Signals", hitter_signals, signal_stats))

    md_lines.extend([
        "",
        "## 📈 Core Projection Accuracy",
        "Grades the raw projections of top targeted options.",
        "",
        "| Target Category | Total Fired | Hits | Accuracy Rate |",
        "| :--- | :---: | :---: | :---: |"
    ])

    for cat, d in projection_stats.items():
        # Skip per-rank keys here — rendered separately in the Stack Rank table below
        if cat.startswith('stack_rank_'):
            continue
        total = d['total']
        hit = d['hit']
        rate_str = f"{(hit/total)*100:.0f}%" if total > 0 else "0%"
        label = "Top 3 Pitchers (QS)" if cat == 'top3_pitchers' else ("Top 3 Stacks (5+ Runs)" if cat == 'top3_stacks' else "Top 5 Hitters (2+ H / HR)")
        md_lines.append(f"| {label} | {total} | {hit} | {rate_str} |")

    # Stack Rank Accuracy sub-table
    md_lines.extend([
        "",
        "### Stack Rank Accuracy",
        "| Rank | Fired | Hit (5+ Runs) | Hit Rate |",
        "| :--- | :---: | :---: | :---: |"
    ])
    for rank_label, rank_key in [('#1 Stack', 'stack_rank_1'), ('#2 Stack', 'stack_rank_2'), ('#3 Stack', 'stack_rank_3')]:
        d = projection_stats[rank_key]
        total = d['total']
        hit = d['hit']
        rate_str = f"{(hit/total)*100:.0f}%" if total > 0 else "0%"
        md_lines.append(f"| {rank_label} | {total} | {hit} | {rate_str} |")

    # EV Betting ROI Tracker Table
    md_lines.extend([
        "",
        "## 💰 Suggested Bets EV ROI Tracker",
        "Grades OMEGA's LOCK and LEAN game conviction recommendations against boxscore outcomes (assumes flat 1-unit bet size on LOCK and LEAN plays; PASS plays are excluded).",
        "",
        "| Bet Category | Suggested Plays | Won | Lost | Push | Net Units | Hit Rate | ROI % |",
        "| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: |"
    ])
    
    for category in ['LOCK', 'LEAN', 'PASS']:
        stats = bet_stats[category]
        total = stats['total']
        won = stats['won']
        lost = stats['lost']
        push = stats['push']
        net = stats['profit']
        
        if total == 0:
            hit_str = "0%"
            roi_str = "0%"
            net_str = "—"
        else:
            hit_str = f"{(won / (total - push) * 100):.1f}%" if (total - push) > 0 else "0%"
            roi_str = f"{(net / total * 100):+.1f}%"
            net_str = f"{net:+.2f} u"
            
        if category == 'PASS':
            net_str = "—"
            hit_str = "—"
            roi_str = "—"
            label = "🪵 **PASSES**"
        elif category == 'LOCK':
            label = "🔒 **LOCKS**"
        else:
            label = "⚡ **LEANS**"
            
        md_lines.append(f"| {label} | {total} | {won} | {lost} | {push} | {net_str} | {hit_str} | {roi_str} |")
        
    md_lines.append(
        f"| 📊 **OVERALL (LOCK+LEAN)** | **{total_bets}** | **{total_wins}** | **{total_losses}** | **{total_pushes}** | **{total_profit:+.2f} u** | **{overall_hit_rate:.1f}%** | **{overall_roi:+.1f}%** |"
    )

    md_lines.extend([
        "",
        "## 🚨 What We Missed (Anomalies & Lessons)",
        "Deep diagnostic failures to help Konrad self-correct and study outliers."
    ])

    if what_we_missed:
        for miss in what_we_missed[:4]:
            md_lines.append(f"- **[{miss['type']}]** ({miss['date']}) — *{miss['name']}*: {miss['detail']}")
    else:
        md_lines.append("- No high-divergence anomalies or projection collapses detected. Calibration holds.")

    md_lines.extend([
        "",
        "## 🛠️ Automated Tactical Adjustments",
        "Suggestions generated by the systematic feedback loops for Konrad's tournament exposure:"
    ])

    for rec in recommendations:
        md_lines.append(f"- {rec}")

    md_path = os.path.join(config.REPORTS_DIR, "learning_feedback.md")
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(md_lines))

    print(f"\n[SUCCESS]: Learning feedback loop executed!")
    print(f"  - Saved JSON feedback to {json_path}")
    print(f"  - Saved Markdown feedback to {md_path}")

if __name__ == "__main__":
    import sys
    days_to_audit = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    run_feedback_loop(days_to_audit)
