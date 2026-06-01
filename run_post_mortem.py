import json
import os
from datetime import datetime
from utils.audit_engine import AuditEngine
from config import config

def run_post_mortem(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    print(f"\n" + "="*60)
    print(f"       OMEGA v6.1: POST-MORTEM AUDIT ({date_str})")
    print("="*60)
    
    # 1. Load Latest Results (The Projections)
    results_path = os.path.join(config.REPORTS_DIR, "latest_results.json")
    if not os.path.exists(results_path):
        print(f"ERROR: No latest_results.json found at {results_path}")
        return
    
    with open(results_path, 'r', encoding='utf-8') as f:
        projections = json.load(f)
    
    # 2. Fetch Actuals via AuditEngine
    audit = AuditEngine()
    print(f"[FETCH]: Retrieving official MLB results for {date_str}...")
    actuals = audit.fetch_results(date=date_str)
    
    if not actuals:
        print("ERROR: Could not fetch actual results from MLB API.")
        return

    # 3. Score Pitchers
    print("\n--- PITCHER PERFORMANCE ---")
    p_audit = audit.score_performance(projections.get('pitchers', []), actuals)
    for p in p_audit[:8]: # Top 8 targets
        print(f"  {p['success_flag']} {p['pitcher']:20} ({p['team'][:12]}) | OMEGA: {p['alpha_score']:5.1f} | Actual: {p['actual_k']} K, {p['actual_er']} ER in {p['actual_ip']} IP")

    # 4. Score Teams (Stacks)
    print("\n--- TEAM STACK PERFORMANCE ---")
    t_audit = audit.score_performance(projections.get('teams', []), actuals)
    for t in t_audit[:8]: # Top 8 stacks
        print(f"  {t['success_flag']} {t['team']:21} | OMEGA: {t['stack_score']:5.1f} | Actual: {t['actual_runs']} Runs | Status: {t['game_status']}")

    # 5. Score Hitters
    print("\n--- TOP HITTER PROJECTIONS ---")
    h_audit = audit.score_performance(projections.get('hitters', []), actuals)
    for h in h_audit[:10]:
        print(f"  {h['success_flag']} {h['name']:20} ({h['team'][:12]}) | OMEGA: {h['player_score']:5.1f} | Actual: {h.get('hitter_stat_line', 'N/A')} | Status: {h['game_status']}")

    print("\n" + "="*60)
    print("AUDIT COMPLETE")
    print("="*60 + "\n")

if __name__ == "__main__":
    import sys
    # If no date provided, use today. 
    # If it's before 10 AM, user likely wants 'yesterday's' slate.
    if len(sys.argv) > 1:
        target_date = sys.argv[1]
    else:
        now = datetime.now()
        if now.hour < 10:
            from datetime import timedelta
            target_date = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            target_date = now.strftime("%Y-%m-%d")
            
    run_post_mortem(target_date)
