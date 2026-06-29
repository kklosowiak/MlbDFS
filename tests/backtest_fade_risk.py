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

def get_runs(act, team_name):
    for k, v in act.items():
        if team_name.lower() in k.lower() or k.lower() in team_name.lower():
            return v.get("runs")
    return None

def main():
    slates = load_slates()
    
    fade_instances = []
    all_teams_count = 0
    all_teams_underperformed = 0
    
    dates = []
    
    for slate in slates:
        date = slate["date"]
        dates.append(date)
        proj = slate["projections"]
        act = slate["actuals"]
        
        teams = proj.get("teams", [])
        for t in teams:
            team_name = t["team"]
            runs = get_runs(act, team_name)
            if runs is None:
                continue
                
            itt = float(t.get("implied_total", 4.5) or 4.5)
            under = runs < itt
            
            all_teams_count += 1
            if under:
                all_teams_underperformed += 1
                
            is_fade = bool(t.get("is_fade_risk") or t.get("fade_risk"))
            if is_fade:
                div = float(t.get("divergence", 0) or 0)
                is_cold = bool(t.get("is_cold_streak_msmi") or t.get("is_cold_streak"))
                
                fade_instances.append({
                    "date": date,
                    "team": team_name,
                    "itt": itt,
                    "runs": runs,
                    "underperformed": under,
                    "magnitude": itt - runs,
                    "divergence": div,
                    "is_cold_streak": is_cold
                })
                
    earliest_date = min(dates) if dates else "N/A"
    latest_date = max(dates) if dates else "N/A"
    
    total_fade = len(fade_instances)
    underperformed_fade = sum(1 for x in fade_instances if x["underperformed"])
    under_rate = underperformed_fade / total_fade if total_fade > 0 else 0.0
    
    avg_itt = sum(x["itt"] for x in fade_instances) / total_fade if total_fade > 0 else 0.0
    avg_runs = sum(x["runs"] for x in fade_instances) / total_fade if total_fade > 0 else 0.0
    avg_mag = sum(x["magnitude"] for x in fade_instances) / total_fade if total_fade > 0 else 0.0
    
    # Secondary breakdowns
    fade_neg_div = [x for x in fade_instances if x["divergence"] < -15]
    fade_neg_div_under = sum(1 for x in fade_neg_div if x["underperformed"])
    neg_div_rate = fade_neg_div_under / len(fade_neg_div) if fade_neg_div else 0.0
    
    fade_cold = [x for x in fade_instances if x["is_cold_streak"]]
    fade_cold_under = sum(1 for x in fade_cold if x["underperformed"])
    cold_rate = fade_cold_under / len(fade_cold) if fade_cold else 0.0
    
    base_under_rate = all_teams_underperformed / all_teams_count if all_teams_count > 0 else 0.0
    
    print("BACKTEST 1 — FADE_RISK Hit Rate Validation")
    print(f"Sample size: {total_fade} instances")
    print(f"Data range: {earliest_date} to {latest_date}")
    
    primary_finding = f"FADE_RISK teams underperform their ITT {under_rate*100:.1f}% of the time, compared to a baseline of {base_under_rate*100:.1f}%."
    print(f"Primary finding: {primary_finding}")
    print(f"Hit rate / accuracy: {underperformed_fade} / {total_fade} ({under_rate*100:.1f}%) underperformed ITT")
    print(f"Secondary metrics:")
    print(f"  - Average ITT: {avg_itt:.2f} runs")
    print(f"  - Average Actual Runs: {avg_runs:.2f} runs")
    print(f"  - Average Underperformance Magnitude: {avg_mag:.2f} runs")
    print(f"  - Base Rate of ITT underperformance (all teams): {all_teams_underperformed} / {all_teams_count} ({base_under_rate*100:.1f}%)")
    print(f"Breakdown by signal combination:")
    print(f"  - FADE_RISK alone underperformance rate: {under_rate*100:.1f}%")
    print(f"  - FADE_RISK + negative divergence (div < -15): {fade_neg_div_under} / {len(fade_neg_div)} ({neg_div_rate*100:.1f}%)")
    print(f"  - FADE_RISK + Team Cold Streak (MSMI): {fade_cold_under} / {len(fade_cold)} ({cold_rate*100:.1f}%)")
    
    # Anomaly / Edge case checking
    outperformed_cases = [x for x in fade_instances if not x["underperformed"]]
    print(f"Edge cases or anomalies: Found {len(outperformed_cases)} instances where FADE_RISK team outperformed ITT.")
    if outperformed_cases:
        print("  Top Outperformers:")
        for x in sorted(outperformed_cases, key=lambda y: y["magnitude"])[:5]: # sorted by most negative magnitude (meaning most runs above ITT)
            print(f"    - {x['date']}: {x['team']} | ITT: {x['itt']} | Actual: {x['runs']} | Divergence: {x['divergence']}")
            
    confidence_level = "HIGH" if total_fade >= 100 else "MEDIUM" if total_fade >= 20 else "LOW"
    print(f"Confidence level: {confidence_level}")
    
    rec = "IMPLEMENT CHANGE" if under_rate >= 0.60 and total_fade >= 100 else "VALIDATE FURTHER"
    print(f"Recommendation: {rec}")

if __name__ == "__main__":
    main()
