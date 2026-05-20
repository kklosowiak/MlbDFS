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
from utils.audit_engine import AuditEngine
from config import config

def calculate_dqi_for_audit(t, pitchers):
    """
    OMEGA v9.7: Continuous Multi-Layer Divergence Quality Index (DQI) Slider Model for historical audit and performance tracking.
    """
    divergence = t.get('divergence', 0) or 0
    if divergence < 10:
        return None, None

    opp_phys           = t.get('opp_pitcher_physics', 50.0) or 50.0
    bullpen            = t.get('bullpen_fatigue', 0) or 0
    tt_move            = t.get('tt_move', 0.0) or 0.0
    ml_move            = t.get('ml_move', 0.0) or 0.0
    is_storm           = t.get('is_storm', False)
    implied_total      = t.get('implied_total', 0.0) or 0.0
    team_xwoba         = t.get('team_xwoba', 0.0) or 0.0
    power_conc         = t.get('power_concentration', 0.0) or 0.0
    total_signal       = t.get('total_signal', '') or ''
    trend              = t.get('trend', 'STABLE') or 'STABLE'
    is_opp_debut       = t.get('is_opp_debut', False)

    # Cross-reference opposing pitcher is_trap
    opp_p_name = t.get('opp_pitcher', '').lower().strip()
    opp_p_obj = next((p for p in pitchers if p.get('pitcher', '').lower().strip() == opp_p_name), None)
    is_trap = opp_p_obj.get('is_trap', False) if opp_p_obj else False

    pos_pts    = 0.0
    warn_pts   = 0.0

    # Layer 1: Divergence Slider
    div_factor = min(1.0, max(0.0, (float(divergence) - 10.0) / 15.0))
    pos_pts += 5.0 + 15.0 * div_factor

    # Layer 2: Pitcher Environment Slider
    phys_factor = min(1.0, max(0.0, (40.0 - float(opp_phys)) / 21.0))
    pos_pts += 20.0 * phys_factor

    pen_factor = min(1.0, max(0.0, (float(bullpen) - 50.0) / 50.0))
    pos_pts += 15.0 * pen_factor

    # Layer 3: Market Confirmation
    if tt_move >= 0.3 or ml_move <= -10.0:
        pos_pts += 12.0
    elif (tt_move <= -0.3 and ml_move >= 10.0) or (ml_move >= 15.0) or (tt_move <= -0.5):
        warn_pts += 15.0

    if 'O-DIV' in total_signal:
        pos_pts += 10.0
    elif 'U-DIV' in total_signal:
        warn_pts += 12.0

    # Layer 4: Offense Quality Slider
    xwoba_factor = min(1.0, max(0.0, (float(team_xwoba) - 0.300) / 0.050))
    pos_pts += 12.0 * xwoba_factor
        
    if power_conc > 0.355:
        pos_pts += 8.0

    if trend == 'SURGING':
        pos_pts += 10.0
    elif trend == 'FADING':
        warn_pts += 15.0

    # Layer 5: Run Environment Slider
    run_factor = min(1.0, max(0.0, (float(implied_total) - 4.0) / 1.5))
    pos_pts += 15.0 * run_factor

    # Layer 6: Situational Bonuses / Traps
    if is_storm:
        pos_pts += 8.0
    if is_opp_debut:
        pos_pts += 10.0
    if is_trap:
        warn_pts += 20.0

    dqi_score = 30.0 + pos_pts - warn_pts
    dqi_score = max(0.0, min(100.0, dqi_score))
    dqi_score_int = int(round(dqi_score))
    status = "TRUST" if dqi_score_int >= 75 else ("CAUTION" if dqi_score_int >= 50 else "FADE")
    return dqi_score_int, status

def run_feedback_loop(days=7):
    print("\n" + "="*60)
    print(f"    OMEGA v9.5: FEEDBACK & SYSTEMATIC LEARNING LOOP")
    print(f"    Auditing Past {days} Slates...")
    print("="*60 + "\n")

    audit = AuditEngine()
    archive_dir = os.path.join(config.REPORTS_DIR, "archive")
    
    # Core performance metrics
    signal_stats = {
        'PITCHER_WHALE': {'fired': 0, 'hit': 0},
        'PITCHER_SHARK': {'fired': 0, 'hit': 0},
        'PITCHER_TRAP_FADE': {'fired': 0, 'hit': 0},  # Success = Trap pitcher gave up >= 4 ER or failed QS
        'TEAM_WHALE': {'fired': 0, 'hit': 0},
        'TEAM_STORM': {'fired': 0, 'hit': 0},
        'TEAM_SURGING': {'fired': 0, 'hit': 0},       # Success = Surging team scored 5+ runs
        'GASSED_BULLPEN_ATTACK': {'fired': 0, 'hit': 0},  # Success = Attacked team scored 5+ runs
        'DQI_TRUST': {'fired': 0, 'hit': 0},             # Success = Team scored 5+ runs
        'DQI_FADE': {'fired': 0, 'hit': 0},              # Success = Team scored < 4 runs (trap worked)
        'STEAM_SUPPORT': {'fired': 0, 'hit': 0},         # Success = Team scored 5+ runs
    }
    
    projection_stats = {
        'top3_pitchers': {'total': 0, 'hit': 0},  # Top 3 OMEGA score quality starts
        'top3_stacks': {'total': 0, 'hit': 0},    # Top 3 OMEGA stack score scoring 5+ runs
        'top5_hitters': {'total': 0, 'hit': 0},   # Top 5 hitters getting 2+ hits or 1+ HR
    }

    what_we_missed = []
    analyzed_dates = []

    # Iterate over the past N days (excluding today)
    today = datetime.date.today()
    for i in range(days, 0, -1):
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
            
        # Fetch actuals
        actuals = audit.fetch_results(date=date_str)
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
        
        # Top 3 Stacks Accuracy (5+ runs scored)
        for t in t_audit[:3]:
            projection_stats['top3_stacks']['total'] += 1
            if t.get('actual_runs', 0) >= 5:
                projection_stats['top3_stacks']['hit'] += 1
                
        # Signal Metrics
        for t in t_audit:
            runs = t.get('actual_runs', 0)
            is_hit_5 = runs >= 5
            div = float(t.get('divergence', 0) or 0)
            
            if t.get('is_whale'):
                signal_stats['TEAM_WHALE']['fired'] += 1
                if is_hit_5:
                    signal_stats['TEAM_WHALE']['hit'] += 1
                    
            if t.get('is_storm'):
                signal_stats['TEAM_STORM']['fired'] += 1
                if is_hit_5:
                    signal_stats['TEAM_STORM']['hit'] += 1
                    
            if t.get('trend') == 'SURGING':
                signal_stats['TEAM_SURGING']['fired'] += 1
                if is_hit_5:
                    signal_stats['TEAM_SURGING']['hit'] += 1
                    
            if t.get('is_gassed'):
                signal_stats['GASSED_BULLPEN_ATTACK']['fired'] += 1
                if runs >= 5:
                    signal_stats['GASSED_BULLPEN_ATTACK']['hit'] += 1
                    
            # 🟢 DQI TRUST, 🔴 DQI FADE calculation (v9.5 6-Layer alignment)
            dqi_score, dqi_status = calculate_dqi_for_audit(t, pitchers)
            if dqi_score is not None:
                if dqi_status == 'TRUST':
                    signal_stats['DQI_TRUST']['fired'] += 1
                    if is_hit_5:
                        signal_stats['DQI_TRUST']['hit'] += 1
                elif dqi_status == 'FADE':
                    signal_stats['DQI_FADE']['fired'] += 1
                    if runs < 4:
                        signal_stats['DQI_FADE']['hit'] += 1
            
            # 💸 STEAM Support Metric
            ml_move = float(t.get('ml_move', 0) or 0)
            tt_move = float(t.get('tt_move', 0) or 0)
            if abs(ml_move) >= 10 or abs(tt_move) >= 0.1:
                if ml_move < 0 or tt_move > 0:
                    signal_stats['STEAM_SUPPORT']['fired'] += 1
                    if is_hit_5:
                        signal_stats['STEAM_SUPPORT']['hit'] += 1

            # Divergence Misses: Positive divergence >= 15% but underperformed (< 3 runs)
            if div >= 15 and runs < 3:
                what_we_missed.append({
                    'date': date_str,
                    'type': 'Team Divergence Fail',
                    'name': t['team'],
                    'detail': f"OMEGA showed +{div}% divergence vs market, but they scored only {runs} runs vs {t.get('opp_pitcher')}."
                })

        # 2. Audit Pitcher Signals & Projections
        p_audit = audit.score_performance(pitchers, actuals)
        
        # Top 3 Pitchers Accuracy (QS is WIN in AuditEngine)
        for p in p_audit[:3]:
            projection_stats['top3_pitchers']['total'] += 1
            if p.get('success_flag') == '[WIN]':
                projection_stats['top3_pitchers']['hit'] += 1
                
        for p in p_audit:
            is_qs = p.get('success_flag') == '[WIN]'
            
            if p.get('is_whale'):
                signal_stats['PITCHER_WHALE']['fired'] += 1
                if is_qs:
                    signal_stats['PITCHER_WHALE']['hit'] += 1
                    
            if p.get('is_shark'):
                signal_stats['PITCHER_SHARK']['fired'] += 1
                if is_qs:
                    signal_stats['PITCHER_SHARK']['hit'] += 1
                    
            if p.get('is_trap'):
                signal_stats['PITCHER_TRAP_FADE']['fired'] += 1
                # Trap success = Pitcher failed to get QS
                if not is_qs:
                    signal_stats['PITCHER_TRAP_FADE']['hit'] += 1
                    
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
            if h.get('success_flag') == '[WIN]':
                projection_stats['top5_hitters']['hit'] += 1

    # Output learning loops and parameter suggestions
    recommendations = []
    
    # Auto-adjust advice logic
    for signal, data in signal_stats.items():
        # Exclude DQI & STEAM from basic card recommendations to keep advice focused on actionable multipliers
        if signal in ['DQI_TRUST', 'DQI_FADE', 'STEAM_SUPPORT']:
            continue
            
        if data['fired'] >= 3:
            rate = (data['hit'] / data['fired']) * 100
            if rate >= 65:
                recommendations.append(f"✅ **{signal}** is highly profitable at **{rate:.0f}%** hit rate. Increase projection weight and trust indicators.")
            elif rate < 40:
                recommendations.append(f"⚠️ **{signal}** has been cold at **{rate:.0f}%** hit rate. Downweight exposure and recommend faded caution.")

    # Explicit DQI Tuning Logic
    if signal_stats['DQI_TRUST']['fired'] >= 3:
        dqi_rate = (signal_stats['DQI_TRUST']['hit'] / signal_stats['DQI_TRUST']['fired']) * 100
        if dqi_rate >= 70:
            recommendations.append(f"🟢 **DQI TRUST Grade** is executing perfectly at **{dqi_rate:.0f}%** success rate. Highly recommend boosting PHY/MKT weights.")
        elif dqi_rate < 50:
            recommendations.append(f"⚠️ **DQI TRUST Grade** is showing convergence volatility at **{dqi_rate:.0f}%** success rate. Recommend widening margins.")

    if not recommendations:
        recommendations.append("🔍 Signal sample size too small for adjustment thresholds. Keep baseline parameters active.")

    # Write files
    feedback_payload = {
        'generated_at': datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p ET"),
        'dates_analyzed': analyzed_dates,
        'signal_stats': signal_stats,
        'projection_stats': projection_stats,
        'what_we_missed': what_we_missed[:5],  # Limit to top 5 misses
        'recommendations': recommendations
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
        "",
        "| Signal Type | Fired | Hit | Hit Rate | Performance |",
        "| :--- | :---: | :---: | :---: | :--- |"
    ]

    for sig, d in signal_stats.items():
        fired = d['fired']
        hit = d['hit']
        if fired == 0:
            rate_str = "0%"
            grade = "⚪ No Data"
        else:
            rate = (hit / fired) * 100
            rate_str = f"{rate:.0f}%"
            grade = "🟢 Hot" if rate >= 65 else ("🟡 Neutral" if rate >= 40 else "🔴 Cold")
            
        md_lines.append(f"| **{sig.replace('_', ' ')}** | {fired} | {hit} | {rate_str} | {grade} |")

    md_lines.extend([
        "",
        "## 📈 Core Projection Accuracy",
        "Grades the raw projections of top targeted options.",
        "",
        "| Target Category | Total Fired | Hits | Accuracy Rate |",
        "| :--- | :---: | :---: | :---: |"
    ])

    for cat, d in projection_stats.items():
        total = d['total']
        hit = d['hit']
        rate_str = f"{(hit/total)*100:.0f}%" if total > 0 else "0%"
        label = "Top 3 Pitchers (QS)" if cat == 'top3_pitchers' else ("Top 3 Stacks (5+ Runs)" if cat == 'top3_stacks' else "Top 5 Hitters (2+ H / HR)")
        md_lines.append(f"| {label} | {total} | {hit} | {rate_str} |")

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
