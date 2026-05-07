import sys
import os
import json
sys.path.append(os.getcwd())
from datetime import datetime
from utils.audit_engine import AuditEngine
from config import config

def generate_report(date_str=None):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")
    
    results_path = os.path.join(config.REPORTS_DIR, "latest_results.json")
    if not os.path.exists(results_path):
        print(f"ERROR: No latest_results.json found at {results_path}")
        return
    
    with open(results_path, 'r') as f:
        projections = json.load(f)
    
    audit = AuditEngine()
    print(f"Fetching results for {date_str}...")
    actuals = audit.fetch_results(date=date_str)
    
    if not actuals:
        print("ERROR: Could not fetch results.")
        return

    p_audit = audit.score_performance(projections.get('pitchers', []), actuals)
    t_audit = audit.score_performance(projections.get('teams', []), actuals)
    h_audit = audit.score_performance(projections.get('hitters', []), actuals)

    report_lines = []
    report_lines.append(f"# OMEGA Post-Mortem Report: {date_str}")
    report_lines.append(f"Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append("\n## Pitcher Performance")
    report_lines.append("| Pitcher | Team | Alpha | Actual (K/ER/IP) | Result |")
    report_lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for p in p_audit:
        report_lines.append(f"| {p['pitcher']} | {p['team']} | {p['alpha_score']:.1f} | {p['actual_k']} K, {p['actual_er']} ER, {p['actual_ip']} IP | {p['success_flag']} |")

    report_lines.append("\n## Team Stack Performance")
    report_lines.append("| Team | Stack Score | Actual Runs | Status | Result |")
    report_lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for t in t_audit:
        report_lines.append(f"| {t['team']} | {t['stack_score']:.1f} | {t['actual_runs']} | {t['game_status']} | {t['success_flag']} |")

    report_lines.append("\n## Hitter Performance (Top 25 Projections)")
    report_lines.append("| Player | Team | OMEGA Score | Stat Line | Result |")
    report_lines.append("| :--- | :--- | :--- | :--- | :--- |")
    for h in h_audit[:25]:
        report_lines.append(f"| {h['name']} | {h['team']} | {h['player_score']:.1f} | {h.get('hitter_stat_line', 'N/A')} | {h['success_flag']} |")

    report_path = os.path.join(config.REPORTS_DIR, f"post_mortem_{date_str.replace('-', '_')}.md")
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("\n".join(report_lines))
    
    print(f"Report generated: {report_path}")

if __name__ == "__main__":
    import sys
    target_date = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    generate_report(target_date)
