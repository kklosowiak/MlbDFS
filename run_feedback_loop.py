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
from utils.dqi import calculate_dqi
from config import config
from utils.team_signals import evaluate_sneaky_stack

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
        'PITCHER_LOW_CEILING': {'fired': 0, 'hit': 0}, # Success = Low ceiling pitcher failed QS
        'PITCHER_HAZARD': {'fired': 0, 'hit': 0},      # Success = Hazard pitcher failed QS
        'TEAM_WHALE': {'fired': 0, 'hit': 0},
        'TEAM_STORM': {'fired': 0, 'hit': 0},
        'TEAM_SURGING': {'fired': 0, 'hit': 0},       # Success = Surging team scored 5+ runs
        'GASSED_BULLPEN_ATTACK': {'fired': 0, 'hit': 0},  # Success = Attacked team scored 5+ runs
        'TEAM_SNEAKY_STACK': {'fired': 0, 'hit': 0},      # Success = Sneaky stack scored 5+ runs
        'TEAM_BURST': {'fired': 0, 'hit': 0},             # Success = Team scored 5+ runs
        'ANTI_CHALK_SMASH': {'fired': 0, 'hit': 0},        # Success = Team scored 5+ runs
        'PHYSICS_OVERRIDE': {'fired': 0, 'hit': 0},        # Success = Team scored 5+ runs
        'GPP_FADE_RISK': {'fired': 0, 'hit': 0},           # Success = Team scored < 4 runs
        'TEAM_COLD_STREAK_MSMI': {'fired': 0, 'hit': 0},  # Success = Cold streak team scored < 4 runs
        'DQI_TRUST': {'fired': 0, 'hit': 0},             # Success = Team scored 5+ runs
        'DQI_FADE': {'fired': 0, 'hit': 0},              # Success = Team scored < 4 runs (trap worked)
        'STEAM_SUPPORT': {'fired': 0, 'hit': 0},         # Success = Team scored 5+ runs
        'HITTER_SMASH': {'fired': 0, 'hit': 0},           # Success = Hitter got 2+ Hits or 1+ HR
    }
    
    projection_stats = {
        'top3_pitchers': {'total': 0, 'hit': 0},  # Top 3 OMEGA score quality starts
        'top3_stacks': {'total': 0, 'hit': 0},    # Top 3 OMEGA stack score scoring 5+ runs
        'top5_hitters': {'total': 0, 'hit': 0},   # Top 5 hitters getting 2+ hits or 1+ HR
    }

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
                
        if date_str in actuals_cache:
            actuals = actuals_cache[date_str]
        else:
            actuals = audit.fetch_results(date=date_str)
            if actuals:
                actuals_cache[date_str] = actuals
                os.makedirs("scratch", exist_ok=True)
                try:
                    with open(cache_path, "w", encoding="utf-8") as cf:
                        json.dump(actuals_cache, cf, indent=4)
                except Exception:
                    pass

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
            # Resolve opposing pitcher for dynamic calculations
            opp_pitcher_name = t.get('opp_pitcher')
            opp_p = None
            if opp_pitcher_name and pitchers:
                from utils.normalization import normalize_player_name
                opp_norm = normalize_player_name(opp_pitcher_name)
                opp_p = next((p for p in pitchers if normalize_player_name(p.get('pitcher', '')) == opp_norm), None)

            if True:
                is_sneaky = evaluate_sneaky_stack(
                    t.get('implied_total'),
                    t.get('team_xwoba'),
                    t.get('opp_pitcher_outs'),
                    t.get('is_opp_debut', False),
                    t.get('bullpen_fatigue', 0),
                    t.get('is_gassed', False),
                    t.get('is_fatigued', False)
                )
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

            if t.get('is_physics_override'):
                signal_stats['PHYSICS_OVERRIDE']['fired'] += 1
                if is_hit_5:
                    signal_stats['PHYSICS_OVERRIDE']['hit'] += 1

            if t.get('is_fade_risk'):
                signal_stats['GPP_FADE_RISK']['fired'] += 1
                if runs < 4:
                    signal_stats['GPP_FADE_RISK']['hit'] += 1

            if t.get('is_cold_streak_msmi'):
                signal_stats['TEAM_COLD_STREAK_MSMI']['fired'] += 1
                if runs < 4:
                    signal_stats['TEAM_COLD_STREAK_MSMI']['hit'] += 1

            # 🟢 DQI TRUST, 🔴 DQI FADE calculation (v9.5 6-Layer alignment)
            dqi_score, dqi_status, _, _ = calculate_dqi(t, pitchers)
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
            if p.get('success_flag') == '[WIN]':
                projection_stats['top3_pitchers']['hit'] += 1
                
        for p in p_audit:
            is_qs = p.get('success_flag') == '[WIN]'
            
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

        for h in h_audit:
            is_smash = h.get('smash_factor') or h.get('is_smash')
            if is_smash is None:
                # Dynamically calculate the optimized smash factor: Matchup xwOBA >= 0.365 and NPAS_xwOBA >= 0.0
                matchup_xwoba = float(h.get('matchup_xwoba', 0.0) or 0.0)
                npas = float(h.get('NPAS_xwOBA', 0.0) or 0.0)
                is_smash = (matchup_xwoba >= 0.365 and npas >= 0.0)
            
            if is_smash:
                signal_stats['HITTER_SMASH']['fired'] += 1
                if h.get('success_flag') == '[WIN]':
                    signal_stats['HITTER_SMASH']['hit'] += 1

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
