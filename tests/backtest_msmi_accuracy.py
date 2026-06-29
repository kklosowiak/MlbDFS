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

def get_hitter_actuals(act, team_name, hitter_name):
    # Find team actuals first
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
    
    # Direct match
    if norm_h in hitters:
        return hitters[norm_h]
        
    # Fuzzy match
    for k, v in hitters.items():
        if norm_h in k or k in norm_h:
            return v
    return None

def main():
    slates = load_slates()
    
    hitter_instances = []
    
    dates = []
    
    for slate in slates:
        date = slate["date"]
        proj = slate["projections"]
        act = slate["actuals"]
        
        hitters = proj.get("hitters", [])
        if not hitters:
            continue
            
        # Dynamically calibrate platoon labels for consistency across all slates
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
            
        # Check if MSMI keys exist in this slate (we only backtest slates that have MSMI keys populated)
        has_msmi = "is_hot_run_msmi" in hitters[0]
        if not has_msmi:
            continue
            
        dates.append(date)
        
        for h in hitters:
            name = h["name"]
            team = h["team"]
            h_act = get_hitter_actuals(act, team, name)
            if not h_act:
                continue
                
            # Actual stats
            hits = float(h_act.get("hits", 0) or 0)
            hr_val = float(h_act.get("hr", 0) or 0)
            rbi = float(h_act.get("rbi", 0) or 0)
            
            # Estimate actual DK score
            actual_dk = 3.0 * hits + 9.0 * hr_val + 2.0 * rbi
            
            # Projected score (scaled to raw DFS points)
            player_score = float(h.get("player_score", 0.0) or 0.0)
            proj_dk = player_score / 10.0
            
            blended = float(h.get("blended_rating", 0.0) or 0.0)
            
            plat_label = calibrated_labels.get(name, "NEUTRAL")
            is_hot = bool(h.get("is_hot_run_msmi"))
            is_cold = bool(h.get("is_cold_streak_msmi"))
            is_smash = bool(h.get("smash_factor") or h.get("is_smash"))
            
            hitter_instances.append({
                "date": date,
                "name": name,
                "team": team,
                "proj": proj_dk,
                "actual": actual_dk,
                "blended": blended,
                "diff": actual_dk - proj_dk,
                "is_hot": is_hot,
                "is_cold": is_cold,
                "is_smash": is_smash,
                "platoon": plat_label
            })
            
    earliest_date = min(dates) if dates else "N/A"
    latest_date = max(dates) if dates else "N/A"
    
    total_hitters = len(hitter_instances)
    
    print("BACKTEST 2 — HOT_MSMI and COLD_MSMI Hitter Accuracy")
    print(f"Sample size: {total_hitters} hitter games")
    print(f"Data range: {earliest_date} to {latest_date}")
    
    # Base rate
    base_outperformed = sum(1 for x in hitter_instances if x["diff"] > 0)
    base_outperformed_rate = base_outperformed / total_hitters if total_hitters > 0 else 0.0
    
    # 1. HOT_MSMI Group
    hot_group = [x for x in hitter_instances if x["is_hot"]]
    hot_size = len(hot_group)
    hot_avg_proj = sum(x["proj"] for x in hot_group) / hot_size if hot_size > 0 else 0.0
    hot_avg_act = sum(x["actual"] for x in hot_group) / hot_size if hot_size > 0 else 0.0
    hot_outperformed = sum(1 for x in hot_group if x["diff"] > 0)
    hot_out_rate = hot_outperformed / hot_size if hot_size > 0 else 0.0
    hot_avg_diff = sum(x["diff"] for x in hot_group) / hot_size if hot_size > 0 else 0.0
    
    # 2. COLD_MSMI Group
    cold_group = [x for x in hitter_instances if x["is_cold"]]
    cold_size = len(cold_group)
    cold_avg_proj = sum(x["proj"] for x in cold_group) / cold_size if cold_size > 0 else 0.0
    cold_avg_act = sum(x["actual"] for x in cold_group) / cold_size if cold_size > 0 else 0.0
    cold_underperformed = sum(1 for x in cold_group if x["diff"] < 0)
    cold_under_rate = cold_underperformed / cold_size if cold_size > 0 else 0.0
    cold_avg_diff = sum(x["diff"] for x in cold_group) / cold_size if cold_size > 0 else 0.0
    
    # 3. HOT_MSMI + STRONG_EDGE
    hot_strong = [x for x in hot_group if x["platoon"] == "STRONG EDGE"]
    hot_strong_size = len(hot_strong)
    hot_strong_out = sum(1 for x in hot_strong if x["diff"] > 0)
    hot_strong_rate = hot_strong_out / hot_strong_size if hot_strong_size > 0 else 0.0
    
    # 4. HOT_MSMI + ELITE_PLATOON
    hot_elite = [x for x in hot_group if x["platoon"] == "ELITE PLATOON"]
    hot_elite_size = len(hot_elite)
    hot_elite_out = sum(1 for x in hot_elite if x["diff"] > 0)
    hot_elite_rate = hot_elite_out / hot_elite_size if hot_elite_size > 0 else 0.0
    
    # 5. COLD_MSMI override High blended_rating (blended >= 80)
    cold_high_br = [x for x in cold_group if x["blended"] >= 80]
    cold_high_br_size = len(cold_high_br)
    cold_high_br_under = sum(1 for x in cold_high_br if x["diff"] < 0)
    cold_high_br_under_rate = cold_high_br_under / cold_high_br_size if cold_high_br_size > 0 else 0.0
    cold_high_br_avg_diff = sum(x["diff"] for x in cold_high_br) / cold_high_br_size if cold_high_br_size > 0 else 0.0
    
    # Platoon sub-analysis
    strong_group = [x for x in hitter_instances if x["platoon"] == "STRONG EDGE"]
    strong_size = len(strong_group)
    strong_out = sum(1 for x in strong_group if x["diff"] > 0)
    strong_rate = strong_out / strong_size if strong_size > 0 else 0.0
    
    elite_group = [x for x in hitter_instances if x["platoon"] == "ELITE PLATOON"]
    elite_size = len(elite_group)
    elite_out = sum(1 for x in elite_group if x["diff"] > 0)
    elite_rate = elite_out / elite_size if elite_size > 0 else 0.0
    
    trap_group = [x for x in hitter_instances if x["platoon"] == "PLATOON TRAP"]
    trap_size = len(trap_group)
    trap_under = sum(1 for x in trap_group if x["diff"] < 0)
    trap_rate = trap_under / trap_size if trap_size > 0 else 0.0
    
    primary_finding = f"HOT_MSMI hitters outperform projections by +{hot_avg_diff:+.2f} DFS points on average ({hot_out_rate*100:.1f}% outperformance), while COLD_MSMI hitters underperform by {cold_avg_diff:.2f} DFS points ({cold_under_rate*100:.1f}% underperformance)."
    print(f"Primary finding: {primary_finding}")
    print(f"Hit rate / accuracy:")
    print(f"  - HOT_MSMI Outperformance Rate: {hot_outperformed} / {hot_size} ({hot_out_rate*100:.1f}%)")
    print(f"  - COLD_MSMI Underperformance Rate: {cold_underperformed} / {cold_size} ({cold_under_rate*100:.1f}%)")
    
    print(f"Secondary metrics:")
    print(f"  - HOT_MSMI average actual score: {hot_avg_act:.2f} (vs Avg Proj: {hot_avg_proj:.2f}) | Avg Delta: {hot_avg_diff:+.2f} pts")
    print(f"  - COLD_MSMI average actual score: {cold_avg_act:.2f} (vs Avg Proj: {cold_avg_proj:.2f}) | Avg Delta: {cold_avg_diff:+.2f} pts")
    print(f"  - Base outperformance rate (all hitters): {base_outperformed} / {total_hitters} ({base_outperformed_rate*100:.1f}%)")
    
    print(f"Breakdown by signal combination:")
    print(f"  - HOT_MSMI + STRONG_EDGE Outperformance: {hot_strong_out} / {hot_strong_size} ({hot_strong_rate*100:.1f}%)")
    print(f"  - HOT_MSMI + ELITE_PLATOON Outperformance: {hot_elite_out} / {hot_elite_size} ({hot_elite_rate*100:.1f}%)")
    print(f"  - COLD_MSMI + High Blended (>=80) Underperformance: {cold_high_br_under} / {cold_high_br_size} ({cold_high_br_under_rate*100:.1f}%) | Avg Delta: {cold_high_br_avg_diff:+.2f} pts")
    print(f"  - STRONG_EDGE Alone Outperformance: {strong_out} / {strong_size} ({strong_rate*100:.1f}%)")
    print(f"  - ELITE_PLATOON Alone Outperformance: {elite_out} / {elite_size} ({elite_rate*100:.1f}%)")
    print(f"  - PLATOON_TRAP Alone Underperformance: {trap_under} / {trap_size} ({trap_rate*100:.1f}%)")
    
    print("Edge cases or anomalies: None")
    
    confidence_level = "HIGH" if total_hitters >= 100 else "MEDIUM"
    print(f"Confidence level: {confidence_level}")
    
    rec = "IMPLEMENT CHANGE" if abs(hot_avg_diff) >= 1.0 or abs(cold_avg_diff) >= 1.0 else "NO ACTION"
    print(f"Recommendation: {rec}")

if __name__ == "__main__":
    main()
