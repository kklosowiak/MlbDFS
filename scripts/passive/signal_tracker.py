import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import argparse
import csv
import json
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

from utils.normalization import normalize_player_name
from utils.audit_engine import AuditEngine

def get_yesterday_et_str():
    dt_utc = datetime.now(timezone.utc)
    if ZoneInfo:
        dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
    else:
        dt_et = dt_utc - timedelta(hours=4)
    yesterday_et = dt_et - timedelta(days=1)
    return yesterday_et.strftime("%Y-%m-%d")

def load_salary_map():
    salary_map = {}
    csv_path = os.path.join("data", "DKSalaries.csv")
    if os.path.exists(csv_path):
        try:
            with open(csv_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get('Name')
                    salary_str = row.get('Salary')
                    if name and salary_str:
                        norm = normalize_player_name(name)
                        salary_map[norm] = int(salary_str)
        except Exception as e:
            print(f"Warning: Failed to load salaries from {csv_path}: {e}")
    return salary_map

def get_pitcher_actuals(actuals, team_name, pitcher_name):
    norm_p = normalize_player_name(pitcher_name)
    for g in actuals:
        if g['home_team'] == team_name:
            sp = g['sp_home']
            if normalize_player_name(sp['name']) == norm_p or norm_p in normalize_player_name(sp['name']) or normalize_player_name(sp['name']) in norm_p:
                return sp, g['away_runs']
            return sp, g['away_runs']
        elif g['away_team'] == team_name:
            sp = g['sp_away']
            if normalize_player_name(sp['name']) == norm_p or norm_p in normalize_player_name(sp['name']) or normalize_player_name(sp['name']) in norm_p:
                return sp, g['home_runs']
            return sp, g['home_runs']
    return None, None

def get_team_implied_total(lock_data, team_name):
    if not team_name:
        return 0.0
    norm_t = normalize_player_name(team_name)
    for t in lock_data.get('teams', []):
        if normalize_player_name(t['team']) == norm_t:
            return float(t.get('implied_total', 0.0) or 0.0)
    return 0.0

def get_hitter_actuals(detailed_actuals, team_name, hitter_name):
    norm_h = normalize_player_name(hitter_name)
    for t_name, t_data in detailed_actuals.items():
        if normalize_player_name(t_name) == normalize_player_name(team_name):
            hitters = t_data.get('hitters', {})
            if norm_h in hitters:
                return hitters[norm_h]
            for h_name, h_val in hitters.items():
                if norm_h in h_name or h_name in norm_h:
                    return h_val
    return None

def calculate_hitter_dk_pts(ha):
    if not ha:
        return 0.0
    singles = ha.get('singles', 0)
    doubles = ha.get('doubles', 0)
    triples = ha.get('triples', 0)
    hr = ha.get('hr', 0)
    r = ha.get('runs_scored', 0)
    rbi = ha.get('rbi', 0)
    bb = ha.get('walks', 0)
    sb = ha.get('stolen_bases', 0)
    k = ha.get('strikeouts', 0)
    hbp = ha.get('hbp', 0)
    
    dk_pts = 3*singles + 5*doubles + 8*triples + 10*hr + 2*r + 2*rbi + 2*bb + 5*sb - 0.5*k + 2*hbp
    return float(round(dk_pts, 2))

def calculate_pitcher_dk_pts(sp):
    if not sp:
        return 0.0
    
    ip_str = str(sp.get('ip', "0.0"))
    if '.' in ip_str:
        parts = ip_str.split('.')
        outs = int(parts[0]) * 3 + int(parts[1])
    else:
        try:
            outs = int(float(ip_str)) * 3
        except ValueError:
            outs = 0
            
    ip_pts = outs * 0.75
    k = sp.get('k', 0) or 0
    er = sp.get('er', 0) or 0
    h = sp.get('h', 0) or 0
    bb = sp.get('bb', 0) or 0
    hb = sp.get('hitByPitch', 0) or 0
    win = sp.get('wins', 0) or 0
    cg = sp.get('completeGames', 0) or 0
    sho = sp.get('shutouts', 0) or 0
    
    dk_pts = ip_pts + (2.0 * k) - (2.0 * er) - (0.6 * h) - (0.6 * bb) - (0.6 * hb) + (4.0 * win)
    if cg:
        dk_pts += 2.5
        if sho:
            dk_pts += 2.5
    if cg and h == 0:
        dk_pts += 5.0
        
    return float(round(dk_pts, 2))

def get_hitter_baseline(hitter_dk_map, target_salary, target_batting_order, exclude_name_norm):
    matches = []
    for h_name_norm, h_info in hitter_dk_map.items():
        if h_name_norm == exclude_name_norm:
            continue
        if h_info['is_flagged']:
            continue
        sal = h_info['salary']
        bo = h_info['batting_order']
        if abs(sal - target_salary) <= 300 and abs(bo - target_batting_order) <= 1:
            matches.append(h_info['dk_pts'])
            
    if not matches:
        return 0.0
    return float(round(sum(matches) / len(matches), 2))

def append_to_csv(file_path, header, row_data, date_str):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    file_exists = os.path.exists(file_path)
    
    # Idempotency Check: if (date, entity) is already in the file, do not append
    if file_exists:
        try:
            with open(file_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.reader(f)
                rows = list(reader)
                if len(rows) > 1 and any(len(r) > 1 and len(row_data) > 1 and r[0] == row_data[0] and r[1] == row_data[1] for r in rows[1:]):
                    return
        except Exception:
            pass

    with open(file_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(header)
        writer.writerow(row_data)

def initialize_all_csvs(signals_dir):
    os.makedirs(signals_dir, exist_ok=True)
    csv_configs = {
        "trap_vulnerable_log.csv": ["date", "pitcher", "pitcher_team", "trap_type", "attack_conf", "ITT", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_ip"],
        "trap_short_leash_log.csv": ["date", "pitcher", "pitcher_team", "trap_type", "attack_conf", "ITT", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_ip"],
        "cold_high_br_log.csv": ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"],
        "fade_risk_log.csv": ["date", "team", "attack_conf", "ITT", "divergence", "ticket_pct", "money_pct", "actual_runs", "run_diff", "fade_correct"],
        "hot_msmi_log.csv": ["date", "player", "team", "salary", "batting_order", "blended_rating", "attack_conf", "actual_dk_pts"],
        "top_stack_log.csv": ["date", "team", "attack_conf", "ITT", "divergence", "actual_runs", "run_diff", "model_correct"],
        "right_game_wrong_team_log.csv": ["date", "game", "teamA", "teamA_conf", "teamA_actual_runs", "teamB", "teamB_conf", "teamB_actual_runs", "fade_risk_team", "both_scored_6plus", "higher_conf_team_won_scoring", "pattern_flagged"],
        "anti_chalk_smash_log.csv": ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"],
        "steam_log.csv": ["date", "team", "attack_conf", "ITT", "divergence", "ticket_pct", "money_pct", "actual_runs", "run_diff", "steam_correct"],
        "platoon_trap_log.csv": ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"],
        "strong_edge_log.csv": ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"],
        "elite_platoon_log.csv": ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"],
        "sharp_fade_pitcher_log.csv": ["date", "pitcher", "pitcher_team", "attack_conf", "ITT", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_ip"],
        "dqi_log.csv": ["date", "team", "attack_conf", "ITT", "dqi_tier", "actual_runs", "run_diff"],
        "pitcher_volatile_log.csv": ["date", "pitcher", "pitcher_team", "attack_conf", "conf_delta", "ITT", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_ip"],
        "pitcher_walks_hazard_log.csv": ["date", "pitcher", "pitcher_team", "attack_conf", "ITT", "walks_penalty", "is_hazard", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_bb"],
        "pen_fatigue_log.csv": ["date", "team", "attack_conf", "ITT", "is_gassed", "is_fatigued", "actual_runs", "run_diff"],
        "burst_log.csv": ["date", "team", "attack_conf", "ITT", "actual_runs", "run_diff", "burst_correct"]
    }
    for fn, header in csv_configs.items():
        fpath = os.path.join(signals_dir, fn)
        if not os.path.exists(fpath):
            with open(fpath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(header)

def main():
    parser = argparse.ArgumentParser(description="OMEGA Signal Tracker Script")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD), defaults to yesterday")
    args = parser.parse_args()

    date_str = args.date or get_yesterday_et_str()
    print(f"Tracking signals for date: {date_str}")

    # Load Predictions Lock JSON
    slates_dir = os.path.join("scratch", "passive_tracker", "slates")
    results_2220 = os.path.join(slates_dir, f"omega-results_{date_str}_2220UTC.json")
    results_1530 = os.path.join(slates_dir, f"omega-results_{date_str}_1530UTC.json")
    
    results_path = None
    if os.path.exists(results_2220):
        try:
            with open(results_2220, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("teams"):
                results_path = results_2220
        except Exception:
            pass

    if not results_path and os.path.exists(results_1530):
        try:
            with open(results_1530, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("teams"):
                results_path = results_1530
        except Exception:
            pass

    if not results_path:
        print(f"No valid lock results JSON found for date {date_str}. Skipping signal tracker.")
        sys.exit(0)

    # Load Actuals
    actuals_path = os.path.join("scratch", "passive_tracker", "actuals", f"actuals_{date_str}.json")
    if not os.path.exists(actuals_path):
        print(f"No game actuals JSON found at {actuals_path}. Skipping signal tracker.")
        sys.exit(0)

    try:
        with open(results_path, "r", encoding="utf-8") as f:
            lock_data = json.load(f)
        with open(actuals_path, "r", encoding="utf-8") as f:
            actuals_data = json.load(f)
    except Exception as e:
        print(f"Error loading JSON data: {e}")
        sys.exit(1)

    if not lock_data.get("teams") or not actuals_data:
        print("Empty predictions or actuals. Skipping signal tracker.")
        sys.exit(0)

    # Fetch detailed hitter boxscores from MLB StatsAPI
    print("Fetching detailed boxscores via AuditEngine...")
    audit = AuditEngine()
    detailed_actuals = audit.fetch_results(date=date_str)
    if not detailed_actuals:
        print("Warning: detailed actuals empty. Player actual scoring will default to 0.")

    # Mappings and lookups
    salary_map = load_salary_map()
    
    teams_dict = {normalize_player_name(t['team']): t for t in lock_data['teams']}
    pitchers_dict = {normalize_player_name(p['pitcher']): p for p in lock_data['pitchers']}
    
    # 1. Map all hitters actual DK points and properties for baseline lookup
    hitter_dk_map = {}
    for h in lock_data.get('hitters', []):
        h_name_norm = normalize_player_name(h['name'])
        team_name = h['team']
        ha = get_hitter_actuals(detailed_actuals, team_name, h['name'])
        dk_pts = calculate_hitter_dk_pts(ha)
        sal = salary_map.get(h_name_norm, int(h.get('salary', 3000)))
        
        hitter_dk_map[h_name_norm] = {
            'name': h['name'],
            'team': team_name,
            'salary': sal,
            'batting_order': int(h.get('batting_order', 1) or 1),
            'dk_pts': dk_pts,
            'is_flagged': bool(h.get('is_cold_high_br_warning'))
        }

    # Signal directory setup
    signals_dir = os.path.join("scratch", "passive_tracker", "signals")
    snapshots_dir = os.path.join("scratch", "passive_tracker", "snapshots")
    os.makedirs(signals_dir, exist_ok=True)
    os.makedirs(snapshots_dir, exist_ok=True)
    initialize_all_csvs(signals_dir)

    # ==================== PROCESS SIGNALS ====================

    # CSV 1: signals/trap_vulnerable_log.csv and signals/trap_short_leash_log.csv
    for p in lock_data.get('pitchers', []):
        if p.get('is_trap'):
            sp_actual, runs_against = get_pitcher_actuals(actuals_data, p['team'], p['pitcher'])
            if sp_actual and runs_against is not None:
                ip = sp_actual.get('ip', 0.0)
                er = sp_actual.get('er', 0)
                opp_team = p.get('opponent') or p.get('opposing_team')
                itt = get_team_implied_total(lock_data, opp_team)
                run_diff = float(round(runs_against - itt, 2))
                row = [date_str, p['pitcher'], p['team'], p.get('trap_type', 'Neutral'), float(p.get('attack_conf', 50)), itt, runs_against, run_diff, er, ip]
                
                t_type = p.get('trap_type', '').strip()
                if t_type == 'Vulnerable':
                    append_to_csv(os.path.join(signals_dir, "trap_vulnerable_log.csv"), ["date", "pitcher", "pitcher_team", "trap_type", "attack_conf", "ITT", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_ip"], row, date_str)
                elif t_type == 'Short Leash':
                    append_to_csv(os.path.join(signals_dir, "trap_short_leash_log.csv"), ["date", "pitcher", "pitcher_team", "trap_type", "attack_conf", "ITT", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_ip"], row, date_str)

    # CSV 2: signals/cold_high_br_log.csv
    # CSV 4: signals/hot_msmi_log.csv
    # CSV 7: signals/anti_chalk_smash_log.csv
    # CSV 9: signals/platoon_trap_log.csv
    # CSV 10: signals/strong_edge_log.csv
    # CSV 11: signals/elite_platoon_log.csv
    for h in lock_data.get('hitters', []):
        h_name_norm = normalize_player_name(h['name'])
        h_info = hitter_dk_map.get(h_name_norm)
        if not h_info: continue
        
        sal = h_info['salary']
        bo = h_info['batting_order']
        dk_pts = h_info['dk_pts']
        blended = float(h.get('blended_rating', 0.0) or 0.0)
        
        if h.get('is_cold_high_br_warning'):
            baseline = get_hitter_baseline(hitter_dk_map, sal, bo, h_name_norm)
            row = [date_str, h['name'], h['team'], sal, bo, blended, dk_pts, baseline, float(round(dk_pts - baseline, 2))]
            append_to_csv(os.path.join(signals_dir, "cold_high_br_log.csv"), ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"], row, date_str)

        if h.get('is_hot_run_msmi'):
            row = [date_str, h['name'], h['team'], sal, bo, blended, float(h.get('attack_conf', 50)), dk_pts]
            append_to_csv(os.path.join(signals_dir, "hot_msmi_log.csv"), ["date", "player", "team", "salary", "batting_order", "blended_rating", "attack_conf", "actual_dk_pts"], row, date_str)

        if h.get('is_anti_chalk_smash'):
            baseline = get_hitter_baseline(hitter_dk_map, sal, bo, h_name_norm)
            row = [date_str, h['name'], h['team'], sal, bo, blended, dk_pts, baseline, float(round(dk_pts - baseline, 2))]
            append_to_csv(os.path.join(signals_dir, "anti_chalk_smash_log.csv"), ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"], row, date_str)

        plat_label = h.get('platoon_label', 'Neutral')
        if plat_label == 'PLATOON TRAP':
            baseline = get_hitter_baseline(hitter_dk_map, sal, bo, h_name_norm)
            row = [date_str, h['name'], h['team'], sal, bo, blended, dk_pts, baseline, float(round(dk_pts - baseline, 2))]
            append_to_csv(os.path.join(signals_dir, "platoon_trap_log.csv"), ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"], row, date_str)

        if plat_label == 'STRONG EDGE':
            baseline = get_hitter_baseline(hitter_dk_map, sal, bo, h_name_norm)
            row = [date_str, h['name'], h['team'], sal, bo, blended, dk_pts, baseline, float(round(dk_pts - baseline, 2))]
            append_to_csv(os.path.join(signals_dir, "strong_edge_log.csv"), ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"], row, date_str)

        if plat_label == 'ELITE PLATOON':
            baseline = get_hitter_baseline(hitter_dk_map, sal, bo, h_name_norm)
            row = [date_str, h['name'], h['team'], sal, bo, blended, dk_pts, baseline, float(round(dk_pts - baseline, 2))]
            append_to_csv(os.path.join(signals_dir, "elite_platoon_log.csv"), ["date", "player", "team", "salary", "batting_order", "blended_rating", "actual_dk_pts", "baseline_dk_pts", "pts_diff"], row, date_str)

    # CSV 3: signals/fade_risk_log.csv
    # CSV 8: signals/steam_log.csv
    # CSV 13: signals/dqi_log.csv
    # CSV 16: signals/pen_fatigue_log.csv
    # CSV 17: signals/burst_log.csv
    # CSV 5: signals/top_stack_log.csv
    sorted_teams = sorted(lock_data['teams'], key=lambda x: float(x.get('attack_conf', 0.0) or 0.0), reverse=True)
    top_stack_team = sorted_teams[0]['team'] if sorted_teams else None
    
    for t in lock_data.get('teams', []):
        t_name_norm = normalize_player_name(t['team'])
        
        # Get actual runs scored
        actual_runs = 0
        for g in actuals_data:
            if g['home_team'] == t['team']:
                actual_runs = g['home_runs']
                break
            elif g['away_team'] == t['team']:
                actual_runs = g['away_runs']
                break

        itt = float(t.get('implied_total', 0.0) or 0.0)
        run_diff = float(round(actual_runs - itt, 2))
        conf = float(t.get('attack_conf', 50))
        div = float(t.get('divergence', 0) or 0)
        t_pct = float(t.get('ticket_pct', 0) or 0) if t.get('ticket_pct') is not None else 0.0
        m_pct = float(t.get('money_pct', 0) or 0) if t.get('money_pct') is not None else 0.0

        if t.get('is_fade_risk'):
            fade_correct = 'Y' if actual_runs < itt else 'N'
            row = [date_str, t['team'], conf, itt, div, t_pct, m_pct, actual_runs, run_diff, fade_correct]
            append_to_csv(os.path.join(signals_dir, "fade_risk_log.csv"), ["date", "team", "attack_conf", "ITT", "divergence", "ticket_pct", "money_pct", "actual_runs", "run_diff", "fade_correct"], row, date_str)

        if t.get('is_steam'):
            steam_correct = 'Y' if actual_runs >= itt else 'N'
            row = [date_str, t['team'], conf, itt, div, t_pct, m_pct, actual_runs, run_diff, steam_correct]
            append_to_csv(os.path.join(signals_dir, "steam_log.csv"), ["date", "team", "attack_conf", "ITT", "divergence", "ticket_pct", "money_pct", "actual_runs", "run_diff", "steam_correct"], row, date_str)

        dqi_status = t.get('dqi_status')
        if dqi_status in ['TRUST', 'CAUTION']:
            row = [date_str, t['team'], conf, itt, dqi_status, actual_runs, run_diff]
            append_to_csv(os.path.join(signals_dir, "dqi_log.csv"), ["date", "team", "attack_conf", "ITT", "dqi_tier", "actual_runs", "run_diff"], row, date_str)

        is_g = bool(t.get('is_gassed'))
        is_f = bool(t.get('is_fatigued'))
        if is_g or is_f:
            row = [date_str, t['team'], conf, itt, 'Y' if is_g else 'N', 'Y' if is_f else 'N', actual_runs, run_diff]
            append_to_csv(os.path.join(signals_dir, "pen_fatigue_log.csv"), ["date", "team", "attack_conf", "ITT", "is_gassed", "is_fatigued", "actual_runs", "run_diff"], row, date_str)

        if t.get('is_burst'):
            burst_correct = 'Y' if actual_runs >= itt else 'N'
            row = [date_str, t['team'], conf, itt, actual_runs, run_diff, burst_correct]
            append_to_csv(os.path.join(signals_dir, "burst_log.csv"), ["date", "team", "attack_conf", "ITT", "actual_runs", "run_diff", "burst_correct"], row, date_str)

        if t['team'] == top_stack_team:
            model_correct = 'Y' if actual_runs >= itt else 'N'
            row = [date_str, t['team'], conf, itt, div, actual_runs, run_diff, model_correct]
            append_to_csv(os.path.join(signals_dir, "top_stack_log.csv"), ["date", "team", "attack_conf", "ITT", "divergence", "actual_runs", "run_diff", "model_correct"], row, date_str)

    # CSV 6: signals/right_game_wrong_team_log.csv
    for g in actuals_data:
        home_team = g['home_team']
        away_team = g['away_team']
        home_runs = g['home_runs']
        away_runs = g['away_runs']
        
        home_proj = teams_dict.get(normalize_player_name(home_team))
        away_proj = teams_dict.get(normalize_player_name(away_team))
        
        if home_proj and away_proj:
            home_fade = bool(home_proj.get('is_fade_risk'))
            away_fade = bool(away_proj.get('is_fade_risk'))
            
            trigger = home_fade or away_fade or (home_runs >= 6 and away_runs >= 6)
            if trigger:
                fade_risk_team = 'both' if (home_fade and away_fade) else ('home' if home_fade else ('away' if away_fade else 'none'))
                both_scored_6 = 'Y' if (home_runs >= 6 and away_runs >= 6) else 'N'
                pattern_flagged = 'Y' if (home_fade or away_fade) else 'N'
                
                home_conf = float(home_proj.get('attack_conf', 50))
                away_conf = float(away_proj.get('attack_conf', 50))
                
                if home_conf > away_conf:
                    h_won = 'Y' if home_runs > away_runs else ('T' if home_runs == away_runs else 'N')
                elif away_conf > home_conf:
                    h_won = 'Y' if away_runs > home_runs else ('T' if home_runs == away_runs else 'N')
                else:
                    h_won = 'Y'
                    
                row = [date_str, f"{away_team} @ {home_team}", away_team, away_conf, away_runs, home_team, home_conf, home_runs, fade_risk_team, both_scored_6, h_won, pattern_flagged]
                append_to_csv(os.path.join(signals_dir, "right_game_wrong_team_log.csv"), ["date", "game", "teamA", "teamA_conf", "teamA_actual_runs", "teamB", "teamB_conf", "teamB_actual_runs", "fade_risk_team", "both_scored_6plus", "higher_conf_team_won_scoring", "pattern_flagged"], row, date_str)

    # CSV 12: signals/sharp_fade_pitcher_log.csv
    # CSV 14: signals/pitcher_volatile_log.csv
    # CSV 15: signals/pitcher_walks_hazard_log.csv
    for p in lock_data.get('pitchers', []):
        p_name_norm = normalize_player_name(p['pitcher'])
        sp_actual, runs_against = get_pitcher_actuals(actuals_data, p['team'], p['pitcher'])
        if sp_actual and runs_against is not None:
            ip = sp_actual.get('ip', 0.0)
            er = sp_actual.get('er', 0)
            bb = sp_actual.get('bb', 0)
            opp_team = p.get('opponent') or p.get('opposing_team')
            itt = get_team_implied_total(lock_data, opp_team)
            run_diff = float(round(runs_against - itt, 2))
            conf = float(p.get('attack_conf', 50))
            
            if p.get('sharp_fade'):
                row = [date_str, p['pitcher'], p['team'], conf, itt, runs_against, run_diff, er, ip]
                append_to_csv(os.path.join(signals_dir, "sharp_fade_pitcher_log.csv"), ["date", "pitcher", "pitcher_team", "attack_conf", "ITT", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_ip"], row, date_str)
                
            if p.get('is_volatile'):
                delta = float(p.get('conf_delta', 0.0) or 0.0)
                row = [date_str, p['pitcher'], p['team'], conf, delta, itt, runs_against, run_diff, er, ip]
                append_to_csv(os.path.join(signals_dir, "pitcher_volatile_log.csv"), ["date", "pitcher", "pitcher_team", "attack_conf", "conf_delta", "ITT", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_ip"], row, date_str)
                
            wp = bool(p.get('walks_penalty'))
            hz = bool(p.get('is_hazard'))
            if wp or hz:
                row = [date_str, p['pitcher'], p['team'], conf, itt, 'Y' if wp else 'N', 'Y' if hz else 'N', runs_against, run_diff, er, bb]
                append_to_csv(os.path.join(signals_dir, "pitcher_walks_hazard_log.csv"), ["date", "pitcher", "pitcher_team", "attack_conf", "ITT", "walks_penalty", "is_hazard", "actual_runs_against", "run_diff", "pitcher_actual_er", "pitcher_actual_bb"], row, date_str)

    # ==================== SAVE DAILY FULL SNAPSHOTS ====================

    # Snapshot A: all_teams_{YYYY-MM-DD}.csv
    # Sort actual runs and conf to calculate rank difference
    teams_actual_runs = {}
    for t in lock_data.get('teams', []):
        runs = 0
        for g in actuals_data:
            if g['home_team'] == t['team']: runs = g['home_runs']; break
            elif g['away_team'] == t['team']: runs = g['away_runs']; break
        teams_actual_runs[t['team']] = runs

    # conf rank
    conf_sorted_teams = sorted(lock_data['teams'], key=lambda x: float(x.get('attack_conf', 50.0) or 50.0), reverse=True)
    conf_ranks = {x['team']: idx + 1 for idx, x in enumerate(conf_sorted_teams)}
    
    # runs rank
    runs_sorted_teams = sorted(lock_data['teams'], key=lambda x: teams_actual_runs.get(x['team'], 0), reverse=True)
    runs_ranks = {x['team']: idx + 1 for idx, x in enumerate(runs_sorted_teams)}

    teams_snap_path = os.path.join(snapshots_dir, f"all_teams_{date_str}.csv")
    if not os.path.exists(teams_snap_path):
        with open(teams_snap_path, "w", newline="", encoding="utf-8") as sf:
            writer = csv.writer(sf)
            writer.writerow([
                "date", "team", "attack_conf", "blended_rating", "implied_total",
                "divergence", "ticket_pct", "money_pct", "signal_count",
                "is_fade_risk", "is_steam", "is_burst", "is_hot_run_msmi",
                "is_anti_chalk_smash", "is_cold_streak_msmi", "is_pitch_alignment", "is_true_talent_penalty",
                "is_gassed", "is_fatigued", "dqi_tier",
                "opp_pitcher", "opp_pitcher_conf", "opp_pitcher_trap_type",
                "actual_runs", "run_diff_vs_itt", "run_diff_vs_conf_rank"
            ])
            for t in lock_data['teams']:
                team_name = t['team']
                conf = float(t.get('attack_conf', 50.0) or 50.0)
                blended = float(t.get('blended_rating', 0.0) or 0.0)
                itt = float(t.get('implied_total', 0.0) or 0.0)
                div = float(t.get('divergence', 0) or 0)
                t_pct = t.get('ticket_pct')
                m_pct = t.get('money_pct')
                
                # count active signal pills
                sig_keys = ['is_fade_risk', 'is_steam', 'is_burst', 'is_hot_run_msmi', 'is_anti_chalk_smash', 'is_cold_streak_msmi', 'is_pitch_alignment', 'is_true_talent_penalty', 'is_gassed', 'is_fatigued']
                sig_count = sum(1 for k in sig_keys if t.get(k))
                
                opp_p_name = t.get('opp_pitcher', '')
                opp_p_norm = normalize_player_name(opp_p_name)
                opp_p = pitchers_dict.get(opp_p_norm, {})
                opp_p_conf = float(opp_p.get('attack_conf', 50.0) or 50.0)
                opp_p_trap = opp_p.get('trap_type', 'Neutral')
                
                runs = teams_actual_runs.get(team_name, 0)
                run_diff_itt = float(round(runs - itt, 2))
                
                conf_rank = conf_ranks.get(team_name, 8)
                runs_rank = runs_ranks.get(team_name, 8)
                rank_diff = conf_rank - runs_rank
                
                writer.writerow([
                    date_str, team_name, conf, blended, itt,
                    div, t_pct, m_pct, sig_count,
                    'Y' if t.get('is_fade_risk') else 'N',
                    'Y' if t.get('is_steam') else 'N',
                    'Y' if t.get('is_burst') else 'N',
                    'Y' if t.get('is_hot_run_msmi') else 'N',
                    'Y' if t.get('is_anti_chalk_smash') else 'N',
                    'Y' if t.get('is_cold_streak_msmi') else 'N',
                    'Y' if t.get('is_pitch_alignment') else 'N',
                    'Y' if t.get('is_true_talent_penalty') else 'N',
                    'Y' if t.get('is_gassed') else 'N',
                    'Y' if t.get('is_fatigued') else 'N',
                    t.get('dqi_status', 'None'),
                    opp_p_name, opp_p_conf, opp_p_trap,
                    runs, run_diff_itt, rank_diff
                ])

    # Snapshot B: all_pitchers_{YYYY-MM-DD}.csv
    pitchers_snap_path = os.path.join(snapshots_dir, f"all_pitchers_{date_str}.csv")
    if not os.path.exists(pitchers_snap_path):
        with open(pitchers_snap_path, "w", newline="", encoding="utf-8") as sf:
            writer = csv.writer(sf)
            writer.writerow([
                "date", "pitcher", "team", "attack_conf", "blended_rating",
                "conf_delta", "k_line", "er_line", "recent_era", "recent_era_5g", "siera",
                "is_trap", "trap_type", "sharp_fade", "is_volatile",
                "walks_penalty", "is_hazard", "form_status",
                "actual_ip", "actual_er", "actual_k", "actual_h", "actual_bb", "actual_dk_pts",
                "er_vs_line", "k_vs_line", "attacking_team_actual_runs"
            ])
            for p in lock_data['pitchers']:
                p_name = p['pitcher']
                team = p['team']
                conf = float(p.get('attack_conf', 50.0) or 50.0)
                blended = float(p.get('blended_rating', 0.0) or 0.0)
                delta = float(p.get('conf_delta', 0.0) or 0.0)
                k_line = float(p.get('k_line', 0.0) or 0.0)
                er_line = float(p.get('er_line', 0.0) or 0.0)
                recent_era = float(p.get('recent_era', 0.0) or 0.0)
                recent_era_5g = p.get('recent_era_5g')
                if recent_era_5g is not None and recent_era_5g != '':
                    recent_era_5g = float(recent_era_5g)
                else:
                    recent_era_5g = None
                siera = float(p.get('siera', 0.0) or 0.0)
                
                sp_actual, runs_against = get_pitcher_actuals(actuals_data, team, p_name)
                
                actual_ip = sp_actual.get('ip', 0.0) if sp_actual else 0.0
                actual_er = sp_actual.get('er', 0) if sp_actual else 0
                actual_k = sp_actual.get('k', 0) if sp_actual else 0
                actual_h = sp_actual.get('h', 0) if sp_actual else 0
                actual_bb = sp_actual.get('bb', 0) if sp_actual else 0
                actual_dk_pts = calculate_pitcher_dk_pts(sp_actual)
                
                er_vs = float(round(actual_er - er_line, 2))
                k_vs = float(round(actual_k - k_line, 2))
                
                writer.writerow([
                    date_str, p_name, team, conf, blended,
                    delta, k_line, er_line, recent_era, recent_era_5g, siera,
                    'Y' if p.get('is_trap') else 'N',
                    p.get('trap_type', 'Neutral'),
                    'Y' if p.get('sharp_fade') else 'N',
                    'Y' if p.get('is_volatile') else 'N',
                    'Y' if p.get('walks_penalty') else 'N',
                    'Y' if p.get('is_hazard') else 'N',
                    p.get('form_status', 'Neutral'),
                    actual_ip, actual_er, actual_k, actual_h, actual_bb, actual_dk_pts,
                    er_vs, k_vs, runs_against or 0
                ])

    # Snapshot C: all_hitters_{YYYY-MM-DD}.csv
    hitters_snap_path = os.path.join(snapshots_dir, f"all_hitters_{date_str}.csv")
    if not os.path.exists(hitters_snap_path):
        with open(hitters_snap_path, "w", newline="", encoding="utf-8") as sf:
            writer = csv.writer(sf)
            writer.writerow([
                "date", "player", "team", "salary", "batting_order",
                "blended_rating", "player_score", "attack_conf",
                "is_hot_run_msmi", "is_anti_chalk_smash",
                "is_cold_high_br_warning", "is_cold_streak_msmi",
                "platoon_label", "is_strong_edge",
                "actual_dk_pts", "dk_pts_per_1k_salary",
                "batting_order_tier", "team_actual_runs"
            ])
            for h in lock_data['hitters']:
                h_name = h['name']
                team = h['team']
                h_name_norm = normalize_player_name(h_name)
                h_info = hitter_dk_map.get(h_name_norm)
                if not h_info: continue
                
                sal = h_info['salary']
                bo = h_info['batting_order']
                dk_pts = h_info['dk_pts']
                
                blended = float(h.get('blended_rating', 0.0) or 0.0)
                score = float(h.get('player_score', 0.0) or 0.0)
                conf = float(h.get('attack_conf', 50.0) or 50.0)
                
                dk_per_1k = float(round(dk_pts / (sal / 1000.0), 2)) if sal > 0 else 0.0
                
                bo_tier = '1-4' if bo in [1,2,3,4] else ('5-6' if bo in [5,6] else '7+')
                t_runs = teams_actual_runs.get(team, 0)
                
                plat_label = h.get('platoon_label', 'Neutral')
                is_strong = 'Y' if plat_label == 'STRONG EDGE' else 'N'
                
                writer.writerow([
                    date_str, h_name, team, sal, bo,
                    blended, score, conf,
                    'Y' if h.get('is_hot_run_msmi') else 'N',
                    'Y' if h.get('is_anti_chalk_smash') else 'N',
                    'Y' if h.get('is_cold_high_br_warning') else 'N',
                    'Y' if h.get('is_cold_streak_msmi') else 'N',
                    plat_label, is_strong,
                    dk_pts, dk_per_1k,
                    bo_tier, t_runs
                ])

    # ==================== SAVE INTRADAY DELTAS ====================

    # Snapshot D: snapshots/intraday_deltas_{YYYY-MM-DD}.csv (if both files exist)
    if os.path.exists(results_1530) and os.path.exists(results_2220):
        try:
            with open(results_1530, "r", encoding="utf-8") as f1, open(results_2220, "r", encoding="utf-8") as f2:
                d_1530 = json.load(f1)
                d_2220 = json.load(f2)
                
            teams_1530 = {normalize_player_name(x['team']): x for x in d_1530.get('teams', [])}
            teams_2220 = {normalize_player_name(x['team']): x for x in d_2220.get('teams', [])}
            
            pitchers_1530 = {normalize_player_name(x['pitcher']): x for x in d_1530.get('pitchers', [])}
            pitchers_2220 = {normalize_player_name(x['pitcher']): x for x in d_2220.get('pitchers', [])}
            
            hitters_1530 = {normalize_player_name(x['name']): x for x in d_1530.get('hitters', [])}
            hitters_2220 = {normalize_player_name(x['name']): x for x in d_2220.get('hitters', [])}
            
            # Write Teams intraday
            teams_delta_path = os.path.join(snapshots_dir, f"intraday_deltas_teams_{date_str}.csv")
            if not os.path.exists(teams_delta_path):
                with open(teams_delta_path, "w", newline="", encoding="utf-8") as df:
                    writer = csv.writer(df)
                    writer.writerow([
                        "date", "team", "attack_conf_1130", "attack_conf_620", 
                        "conf_delta_intraday", "blended_1130", "blended_620",
                        "blended_delta_intraday", "divergence_1130", "divergence_620",
                        "actual_runs"
                    ])
                    for t_norm, t_620 in teams_2220.items():
                        t_1130 = teams_1530.get(t_norm)
                        if t_1130:
                            conf_620 = float(t_620.get('attack_conf', 50.0) or 50.0)
                            conf_1130 = float(t_1130.get('attack_conf', 50.0) or 50.0)
                            bl_620 = float(t_620.get('blended_rating', 0.0) or 0.0)
                            bl_1130 = float(t_1130.get('blended_rating', 0.0) or 0.0)
                            div_620 = float(t_620.get('divergence', 0) or 0)
                            div_1130 = float(t_1130.get('divergence', 0) or 0)
                            
                            runs = teams_actual_runs.get(t_620['team'], 0)
                            writer.writerow([
                                date_str, t_620['team'], conf_1130, conf_620,
                                float(round(conf_620 - conf_1130, 2)), bl_1130, bl_620,
                                float(round(bl_620 - bl_1130, 2)), div_1130, div_620,
                                runs
                            ])
                            
            # Write Pitchers intraday
            pitchers_delta_path = os.path.join(snapshots_dir, f"intraday_deltas_pitchers_{date_str}.csv")
            if not os.path.exists(pitchers_delta_path):
                with open(pitchers_delta_path, "w", newline="", encoding="utf-8") as df:
                    writer = csv.writer(df)
                    writer.writerow([
                        "date", "pitcher", "team", "attack_conf_1130", "attack_conf_620",
                        "conf_delta_intraday", "is_volatile_at_lock",
                        "actual_er", "actual_ip", "attacking_team_actual_runs"
                    ])
                    for p_norm, p_620 in pitchers_2220.items():
                        p_1130 = pitchers_1530.get(p_norm)
                        if p_1130:
                            conf_620 = float(p_620.get('attack_conf', 50.0) or 50.0)
                            conf_1130 = float(p_1130.get('attack_conf', 50.0) or 50.0)
                            
                            sp_actual, runs_against = get_pitcher_actuals(actuals_data, p_620['team'], p_620['pitcher'])
                            actual_ip = sp_actual.get('ip', 0.0) if sp_actual else 0.0
                            actual_er = sp_actual.get('er', 0) if sp_actual else 0
                            
                            writer.writerow([
                                date_str, p_620['pitcher'], p_620['team'], conf_1130, conf_620,
                                float(round(conf_620 - conf_1130, 2)), 'Y' if p_620.get('is_volatile') else 'N',
                                actual_er, actual_ip, runs_against or 0
                            ])
                            
            # Write Hitters intraday (only if blended rating changed)
            hitters_delta_path = os.path.join(snapshots_dir, f"intraday_deltas_hitters_{date_str}.csv")
            if not os.path.exists(hitters_delta_path):
                with open(hitters_delta_path, "w", newline="", encoding="utf-8") as df:
                    writer = csv.writer(df)
                    writer.writerow([
                        "date", "player", "team", "blended_1130", "blended_620",
                        "blended_delta_intraday", "actual_dk_pts"
                    ])
                    for h_norm, h_620 in hitters_2220.items():
                        h_1130 = hitters_1530.get(h_norm)
                        if h_1130:
                            bl_620 = float(h_620.get('blended_rating', 0.0) or 0.0)
                            bl_1130 = float(h_1130.get('blended_rating', 0.0) or 0.0)
                            
                            if abs(bl_620 - bl_1130) > 0.01:
                                h_info = hitter_dk_map.get(h_norm)
                                dk_pts = h_info['dk_pts'] if h_info else 0.0
                                
                                writer.writerow([
                                    date_str, h_620['name'], h_620['team'], bl_1130, bl_620,
                                    float(round(bl_620 - bl_1130, 2)), dk_pts
                                ])
        except Exception as e:
            print(f"Warning: Failed to calculate intraday deltas: {e}")

    # ==================== WEEKLY ROLLUPS ====================
    try:
        # Determine week number from date_str
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        week_num = dt.isocalendar()[1]
        
        # Combine all snapshots for this week
        rollup_path = os.path.join(snapshots_dir, f"rollup_week_{week_num}.csv")
        
        # Find all hitter snapshot files for the same week
        # (Since GHA runs nightly, we rebuild the rollup for the week by aggregating the hitter snapshots for dates within the same ISO week)
        # We target hitters snapshots as they represent player-level rollup, or we can compile teams/pitchers/hitters separately.
        # The prompt says: "combining all seven days into one file per week." 
        # We will compile hitters snapshots as they represent the most granular data (hitters rollups).
        hitter_snapshots = []
        for f in os.listdir(snapshots_dir):
            if f.startswith("all_hitters_") and f.endswith(".csv"):
                file_date_str = f.replace("all_hitters_", "").replace(".csv", "")
                try:
                    f_dt = datetime.strptime(file_date_str, "%Y-%m-%d")
                    if f_dt.isocalendar()[1] == week_num:
                        hitter_snapshots.append(os.path.join(snapshots_dir, f))
                except ValueError:
                    pass
                    
        if hitter_snapshots:
            # Sort by date
            hitter_snapshots.sort()
            
            # Combine them
            combined_rows = []
            header = None
            for fs in hitter_snapshots:
                with open(fs, "r", newline="", encoding="utf-8") as rfile:
                    reader = csv.reader(rfile)
                    r_rows = list(reader)
                    if len(r_rows) > 0:
                        if not header:
                            header = r_rows[0]
                        combined_rows.extend(r_rows[1:])
            
            if header and combined_rows:
                with open(rollup_path, "w", newline="", encoding="utf-8") as wfile:
                    writer = csv.writer(wfile)
                    writer.writerow(header)
                    writer.writerows(combined_rows)
                print(f"Updated weekly rollup at {rollup_path} with {len(combined_rows)} rows.")
    except Exception as e:
        print(f"Warning: Failed to compile weekly rollup: {e}")

    print("Signal tracker processing completed successfully.")

if __name__ == "__main__":
    main()
