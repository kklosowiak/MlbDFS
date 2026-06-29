import os
import json
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
archive_dir = os.path.join(base_dir, "reports", "archive")
from utils.audit_engine import calculate_dk_score

def load_slates():
    slates = []
    files = os.listdir(archive_dir)
    results_files = sorted([f for f in files if f.startswith("results_") and f.endswith(".json")])
    for rf in results_files:
        date_match = re.search(r'results_(\d{4}-\d{2}-\d{2})', rf)
        if not date_match:
            continue
        date_str = date_match.group(1)
        actuals_path = os.path.join(archive_dir, f"actuals_cache_{date_str}.json")
        if os.path.exists(actuals_path):
            try:
                with open(os.path.join(archive_dir, rf), "r", encoding="utf-8") as f:
                    proj = json.load(f)
                with open(actuals_path, "r", encoding="utf-8") as f:
                    act = json.load(f)
                slates.append({
                    "date": date_str,
                    "projections": proj,
                    "actuals": act
                })
            except Exception as e:
                pass
    return slates

def get_runs(act, team_name):
    for k, v in act.items():
        if team_name.lower() in k.lower() or k.lower() in team_name.lower():
            return v.get("runs")
    return None

def get_hitter_actuals(act, team_name, hitter_name):
    team_data = act.get(team_name)
    if not team_data:
        for k, v in act.items():
            if team_name.lower() in k.lower() or k.lower() in team_name.lower():
                team_data = v
                break
    if not team_data:
        return None
        
    hitters = team_data.get("hitters", {})
    from utils.normalization import normalize_player_name
    norm_h = normalize_player_name(hitter_name)
    
    if norm_h in hitters:
        return hitters[norm_h]
    for k, v in hitters.items():
        if norm_h in k or k in norm_h:
            return v
    return None

def main():
    slates = load_slates()
    
    lock_instances = []
    lean_instances = []
    
    dates = []
    
    for slate in slates:
        date = slate["date"]
        proj = slate["projections"]
        act = slate["actuals"]
        
        teams = proj.get("teams", [])
        hitters = proj.get("hitters", [])
        if not teams or not hitters:
            continue
            
        # Dynamically calibrate platoon labels
        h_sorted = sorted(hitters, key=lambda x: float(x.get('NPAS_xwOBA', 0.0) or 0.0), reverse=True)
        n_hitters = len(h_sorted)
        calibrated_labels = {}
        for idx, hr in enumerate(h_sorted):
            percentile = idx / n_hitters if n_hitters > 0 else 0.5
            npas = float(hr.get('NPAS_xwOBA', 0.0) or 0.0)
            if percentile <= 0.05 and npas >= 0.025:
                label = "ELITE PLATOON"
            elif percentile <= 0.15 and npas >= 0.015:
                label = "STRONG EDGE"
            elif npas <= -0.015 or (percentile >= 0.90 and npas <= -0.010):
                label = "PLATOON TRAP"
            else:
                label = "NEUTRAL"
            calibrated_labels[hr['name']] = label
            
        # Must have MSMI keys to participate in comparison
        has_msmi = "is_hot_run_msmi" in hitters[0]
        if not has_msmi:
            continue
            
        dates.append(date)
        
        # 1. Resolve LOCK (Top team stack by blended_rating)
        # Handle cases where multiple teams are present
        scored_teams = []
        for t in teams:
            team_name = t["team"]
            runs = get_runs(act, team_name)
            if runs is not None:
                scored_teams.append((t, runs))
                
        if scored_teams:
            # Sort by blended_rating descending
            scored_teams_sorted = sorted(scored_teams, key=lambda x: float(x[0].get("blended_rating", 0.0) or 0.0), reverse=True)
            top_t, top_runs = scored_teams_sorted[0]
            
            lock_instances.append({
                "date": date,
                "team": top_t["team"],
                "blended_rating": float(top_t.get("blended_rating", 0.0) or 0.0),
                "attack_conf": float(top_t.get("attack_conf", 0.0) or 0.0),
                "itt": float(top_t.get("implied_total", 4.5) or 4.5),
                "runs": top_runs,
                "is_fade_risk": bool(top_t.get("is_fade_risk") or top_t.get("fade_risk")),
                "divergence": float(top_t.get("divergence", 0.0) or 0.0),
                "is_cold_streak": bool(top_t.get("is_cold_streak_msmi") or top_t.get("is_cold_streak")),
                # Check for weather warnings or paradox in reasons
                "reasons": top_t.get("attack_reasons", []) or []
            })
            
        # 2. Resolve LEANs (Hitters with 2+ positive signals: HOT_MSMI, STRONG_EDGE, ELITE_PLATOON, SMASH)
        for h in hitters:
            name = h["name"]
            team = h["team"]
            h_act = get_hitter_actuals(act, team, name)
            if not h_act:
                continue
                
            # Check signals
            is_hot = bool(h.get("is_hot_run_msmi"))
            plat_label = calibrated_labels.get(name, "NEUTRAL")
            is_strong = plat_label == "STRONG EDGE"
            is_elite = plat_label == "ELITE PLATOON"
            is_smash = bool(h.get("smash_factor") or h.get("is_smash"))
            
            sig_count = sum([is_hot, is_strong, is_elite, is_smash])
            if sig_count >= 2:
                # Calculate actual DK score using complete StatsAPI fields
                actual_dk = calculate_dk_score(h_act)
                
                player_score = float(h.get("player_score", 0.0) or 0.0)
                proj_dk = player_score / 10.0
                
                lean_instances.append({
                    "date": date,
                    "name": name,
                    "team": team,
                    "blended": float(h.get("blended_rating", 0.0) or 0.0),
                    "proj": proj_dk,
                    "actual": actual_dk,
                    "diff": actual_dk - proj_dk
                })
                
    earliest_date = min(dates) if dates else "N/A"
    latest_date = max(dates) if dates else "N/A"
    
    n_locks = len(lock_instances)
    n_leans = len(lean_instances)
    
    # LOCK analysis
    locks_5plus = sum(1 for x in lock_instances if x["runs"] >= 5)
    locks_4plus = sum(1 for x in lock_instances if x["runs"] >= 4)
    locks_5plus_rate = locks_5plus / n_locks if n_locks > 0 else 0.0
    locks_4plus_rate = locks_4plus / n_locks if n_locks > 0 else 0.0
    avg_lock_runs = sum(x["runs"] for x in lock_instances) / n_locks if n_locks > 0 else 0.0
    avg_lock_itt = sum(x["itt"] for x in lock_instances) / n_locks if n_locks > 0 else 0.0
    
    # LEAN analysis
    leans_3plus = sum(1 for x in lean_instances if x["diff"] >= 3.0)
    leans_3plus_rate = leans_3plus / n_leans if n_leans > 0 else 0.0
    avg_lean_actual = sum(x["actual"] for x in lean_instances) / n_leans if n_leans > 0 else 0.0
    avg_lean_proj = sum(x["proj"] for x in lean_instances) / n_leans if n_leans > 0 else 0.0
    avg_lean_diff = sum(x["diff"] for x in lean_instances) / n_leans if n_leans > 0 else 0.0
    
    # LOCK breakdowns
    locks_conf_90 = [x for x in lock_instances if x["attack_conf"] >= 90]
    locks_conf_75_89 = [x for x in lock_instances if 75 <= x["attack_conf"] < 90]
    locks_conf_95 = [x for x in lock_instances if x["attack_conf"] >= 95]
    locks_conf_80_89 = [x for x in lock_instances if 80 <= x["attack_conf"] < 90]
    
    rate_conf_90 = sum(1 for x in locks_conf_90 if x["runs"] >= 5) / len(locks_conf_90) if locks_conf_90 else 0.0
    rate_conf_75_89 = sum(1 for x in locks_conf_75_89 if x["runs"] >= 5) / len(locks_conf_75_89) if locks_conf_75_89 else 0.0
    rate_conf_95 = sum(1 for x in locks_conf_95 if x["runs"] >= 5) / len(locks_conf_95) if locks_conf_95 else 0.0
    rate_conf_80_89 = sum(1 for x in locks_conf_80_89 if x["runs"] >= 5) / len(locks_conf_80_89) if locks_conf_80_89 else 0.0
    
    locks_fade = [x for x in lock_instances if x["is_fade_risk"]]
    rate_locks_fade = sum(1 for x in locks_fade if x["runs"] >= 5) / len(locks_fade) if locks_fade else 0.0
    
    # Bust analysis (Failed to score 5+ runs)
    bust_locks = [x for x in lock_instances if x["runs"] < 5]
    print("BACKTEST 3 — LOCK vs LEAN ROI Comparison")
    print(f"Sample size: LOCKs = {n_locks} slates, LEANs = {n_leans} hitter games")
    print(f"Data range: {earliest_date} to {latest_date}")
    
    primary_finding = f"Top-rated LOCK stacks scored 5+ runs in {locks_5plus_rate*100:.1f}% of slates (averaging {avg_lock_runs:.2f} runs vs {avg_lock_itt:.2f} ITT), while top LEAN hitters outperformed projections by 3+ DFS points in {leans_3plus_rate*100:.1f}% of games."
    print(f"Primary finding: {primary_finding}")
    
    print("Hit rate / accuracy:")
    print(f"  - LOCK Stack (5+ runs): {locks_5plus} / {n_locks} ({locks_5plus_rate*100:.1f}%)")
    print(f"  - LOCK Stack (4+ runs): {locks_4plus} / {n_locks} ({locks_4plus_rate*100:.1f}%)")
    print(f"  - LEAN Hitter (Outperform by 3+ DFS pts): {leans_3plus} / {n_leans} ({leans_3plus_rate*100:.1f}%)")
    
    print("Secondary metrics:")
    print(f"  - LOCK stack average actual runs: {avg_lock_runs:.2f} (vs Avg ITT: {avg_lock_itt:.2f})")
    print(f"  - LEAN hitter average actual DFS score: {avg_lean_actual:.2f} (vs Avg Proj: {avg_lean_proj:.2f}) | Avg Delta: {avg_lean_diff:+.2f} pts")
    
    print("Breakdown by signal combination:")
    print(f"  - LOCK Stack (CONF >= 90) 5+ Runs Hit Rate: {sum(1 for x in locks_conf_90 if x['runs'] >= 5)} / {len(locks_conf_90)} ({rate_conf_90*100:.1f}%)")
    print(f"  - LOCK Stack (CONF 75-89) 5+ Runs Hit Rate: {sum(1 for x in locks_conf_75_89 if x['runs'] >= 5)} / {len(locks_conf_75_89)} ({rate_conf_75_89*100:.1f}%)")
    print(f"  - LOCK Stack (CONF >= 95) 5+ Runs Hit Rate: {sum(1 for x in locks_conf_95 if x['runs'] >= 5)} / {len(locks_conf_95)} ({rate_conf_95*100:.1f}%)")
    print(f"  - LOCK Stack (CONF 80-89) 5+ Runs Hit Rate: {sum(1 for x in locks_conf_80_89 if x['runs'] >= 5)} / {len(locks_conf_80_89)} ({rate_conf_80_89*100:.1f}%)")
    print(f"  - LOCK Stack + FADE_RISK 5+ Runs Hit Rate: {sum(1 for x in locks_fade if x['runs'] >= 5)} / {len(locks_fade)} ({rate_locks_fade*100:.1f}%)")
    
    print("Edge cases or anomalies:")
    print(f"Analysis of LOCK Busts (Failed to score 5+ runs): Total {len(bust_locks)} busts.")
    # Check what warning signals were present in these bust games
    fade_risk_cnt = 0
    neg_div_cnt = 0
    cold_streak_cnt = 0
    weather_cnt = 0
    paradox_cnt = 0
    for b in bust_locks:
        if b["is_fade_risk"]: fade_risk_cnt += 1
        if b["divergence"] < -15: neg_div_cnt += 1
        if b["is_cold_streak"]: cold_streak_cnt += 1
        
        # Check reasons text
        reasons_text = " ".join(b["reasons"]).lower()
        if "weather" in reasons_text or "precip" in reasons_text or "wind" in reasons_text:
            weather_cnt += 1
            
        # Paradox
        if "paradox" in reasons_text:
            paradox_cnt += 1
            
    print(f"  Warning signals present in LOCK bust games:")
    print(f"    - FADE_RISK present: {fade_risk_cnt} / {len(bust_locks)} ({fade_risk_cnt/len(bust_locks)*100:.1f}%)")
    print(f"    - Negative divergence (div < -15) present: {neg_div_cnt} / {len(bust_locks)} ({neg_div_cnt/len(bust_locks)*100:.1f}%)")
    print(f"    - Team Cold Streak present: {cold_streak_cnt} / {len(bust_locks)} ({cold_streak_cnt/len(bust_locks)*100:.1f}%)")
    print(f"    - Weather warning present: {weather_cnt} / {len(bust_locks)} ({weather_cnt/len(bust_locks)*100:.1f}%)")
    print(f"    - PARADOX pitcher present: {paradox_cnt} / {len(bust_locks)} ({paradox_cnt/len(bust_locks)*100:.1f}%)")
    
    confidence_level = "HIGH" if n_locks >= 20 else "MEDIUM"
    print(f"Confidence level: {confidence_level}")
    print("Recommendation: FLAG FOR JULY AUDIT")

if __name__ == "__main__":
    main()
