import os
import sys
import csv
import glob
from datetime import datetime, timezone

def read_csv_rows(file_path):
    if not os.path.exists(file_path):
        return []
    rows = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception:
        pass
    return rows

def safe_float(val, default=0.0):
    try:
        return float(val)
    except (TypeError, ValueError):
        return default

def calculate_accuracy_row(signal_name, rows, hit_key, hit_val, diff_key):
    total = len(rows)
    if total == 0:
        return {"name": signal_name, "n": 0, "hit_pct": "0.0%", "avg_diff": "0.0", "trend": []}
    
    hits = sum(1 for r in rows if r.get(hit_key) == hit_val)
    hit_pct = (hits / total) * 100
    
    diffs = [safe_float(r.get(diff_key)) for r in rows]
    avg_diff = sum(diffs) / total
    
    # Trend: last 7 instances
    # We sort by date (newest last) and look at hit results
    sorted_rows = sorted(rows, key=lambda x: x.get('date', ''))
    last_7 = sorted_rows[-7:]
    trend = []
    for r in last_7:
        trend.append("HIT" if r.get(hit_key) == hit_val else "MISS")
        
    return {
        "name": signal_name,
        "n": total,
        "hit_pct": f"{hit_pct:.1f}%",
        "avg_diff": f"{avg_diff:+.2f}",
        "trend": trend
    }

def main():
    print("Generating OMEGA Audit Dashboard...")

    signals_dir = os.path.join("scratch", "passive_tracker", "signals")
    digests_dir = os.path.join("scratch", "passive_tracker", "digests")
    docs_dir = "docs"
    os.makedirs(docs_dir, exist_ok=True)
    dashboard_path = os.path.join(docs_dir, "audit_dashboard.html")

    # Load signals CSVs
    trap_rows = read_csv_rows(os.path.join(signals_dir, "trap_arm_log.csv"))
    fade_rows = read_csv_rows(os.path.join(signals_dir, "fade_risk_log.csv"))
    top_stack_rows = read_csv_rows(os.path.join(signals_dir, "top_stack_log.csv"))
    hot_msmi_rows = read_csv_rows(os.path.join(signals_dir, "hot_msmi_log.csv"))
    cold_br_rows = read_csv_rows(os.path.join(signals_dir, "cold_high_br_log.csv"))
    anti_chalk_rows = read_csv_rows(os.path.join(signals_dir, "anti_chalk_smash_log.csv"))
    steam_rows = read_csv_rows(os.path.join(signals_dir, "steam_log.csv"))
    plat_trap_rows = read_csv_rows(os.path.join(signals_dir, "platoon_trap_log.csv"))
    strong_edge_rows = read_csv_rows(os.path.join(signals_dir, "strong_edge_log.csv"))
    sharp_fade_rows = read_csv_rows(os.path.join(signals_dir, "sharp_fade_pitcher_log.csv"))
    volatile_rows = read_csv_rows(os.path.join(signals_dir, "pitcher_volatile_log.csv"))
    walks_hazard_rows = read_csv_rows(os.path.join(signals_dir, "pitcher_walks_hazard_log.csv"))
    pen_fatigue_rows = read_csv_rows(os.path.join(signals_dir, "pen_fatigue_log.csv"))
    burst_rows = read_csv_rows(os.path.join(signals_dir, "burst_log.csv"))
    rgwt_rows = read_csv_rows(os.path.join(signals_dir, "right_game_wrong_team_log.csv"))

    # Calculate signal stats
    vul_arms = [r for r in trap_rows if r.get('trap_type') == 'Vulnerable']
    sh_arms = [r for r in trap_rows if r.get('trap_type') == 'Short Leash']
    
    # Helper to calculate hit rate for vulnerable/short leash
    # Hits = opposing runs < ITT (run_diff < 0)
    vul_stats = calculate_accuracy_row("TRAP / Vulnerable", vul_arms, "", "", "run_diff")
    if len(vul_arms) > 0:
        vul_hits = sum(1 for r in vul_arms if safe_float(r.get('run_diff')) < 0)
        vul_stats["hit_pct"] = f"{(vul_hits / len(vul_arms)) * 100:.1f}%"
        vul_stats["trend"] = ["HIT" if safe_float(r.get('run_diff')) < 0 else "MISS" for r in sorted(vul_arms, key=lambda x: x.get('date', ''))[-7:]]
        
    sh_stats = calculate_accuracy_row("TRAP / Short Leash", sh_arms, "", "", "run_diff")
    if len(sh_arms) > 0:
        sh_hits = sum(1 for r in sh_arms if safe_float(r.get('run_diff')) < 0)
        sh_stats["hit_pct"] = f"{(sh_hits / len(sh_arms)) * 100:.1f}%"
        sh_stats["trend"] = ["HIT" if safe_float(r.get('run_diff')) < 0 else "MISS" for r in sorted(sh_arms, key=lambda x: x.get('date', ''))[-7:]]

    fade_stats = calculate_accuracy_row("FADE_RISK", fade_rows, "fade_correct", "Y", "run_diff")
    top_stack_stats = calculate_accuracy_row("Top Stack", top_stack_rows, "model_correct", "Y", "run_diff")
    
    # HOT_MSMI and COLD_HIGH_BR have actual points
    hot_stats = calculate_accuracy_row("HOT_MSMI", hot_msmi_rows, "", "", "actual_dk_pts")
    if len(hot_msmi_rows) > 0:
        hot_avg = sum(safe_float(r.get('actual_dk_pts')) for r in hot_msmi_rows) / len(hot_msmi_rows)
        hot_stats["hit_pct"] = "N/A"
        hot_stats["avg_diff"] = f"{hot_avg:.2f} DK"
        hot_stats["trend"] = [] # Not hit/miss
        
    cold_stats = calculate_accuracy_row("COLD_HIGH_BR_WARNING", cold_br_rows, "", "", "pts_diff")
    if len(cold_br_rows) > 0:
        cold_under = sum(1 for r in cold_br_rows if safe_float(r.get('pts_diff')) < 0)
        cold_stats["hit_pct"] = f"{(cold_under / len(cold_br_rows)) * 100:.1f}% under"
        cold_stats["trend"] = ["HIT" if safe_float(r.get('pts_diff')) < 0 else "MISS" for r in sorted(cold_br_rows, key=lambda x: x.get('date', ''))[-7:]]

    steam_stats = calculate_accuracy_row("STEAM Stacks", steam_rows, "steam_correct", "Y", "run_diff")
    anti_chalk_stats = calculate_accuracy_row("ANTI_CHALK_SMASH", anti_chalk_rows, "", "", "pts_diff")
    if len(anti_chalk_rows) > 0:
        ac_avg = sum(safe_float(r.get('pts_diff')) for r in anti_chalk_rows) / len(anti_chalk_rows)
        anti_chalk_stats["hit_pct"] = "N/A"
        anti_chalk_stats["avg_diff"] = f"{ac_avg:+.2f} vs BL"
        anti_chalk_stats["trend"] = []

    plat_trap_stats = calculate_accuracy_row("PLATOON_TRAP", plat_trap_rows, "", "", "pts_diff")
    if len(plat_trap_rows) > 0:
        pt_under = sum(1 for r in plat_trap_rows if safe_float(r.get('pts_diff')) < 0)
        plat_trap_stats["hit_pct"] = f"{(pt_under / len(plat_trap_rows)) * 100:.1f}% under"
        plat_trap_stats["trend"] = ["HIT" if safe_float(r.get('pts_diff')) < 0 else "MISS" for r in sorted(plat_trap_rows, key=lambda x: x.get('date', ''))[-7:]]

    strong_edge_stats = calculate_accuracy_row("STRONG_EDGE", strong_edge_rows, "", "", "pts_diff")
    if len(strong_edge_rows) > 0:
        se_avg = sum(safe_float(r.get('pts_diff')) for r in strong_edge_rows) / len(strong_edge_rows)
        strong_edge_stats["hit_pct"] = "N/A"
        strong_edge_stats["avg_diff"] = f"{se_avg:+.2f} vs BL"
        strong_edge_stats["trend"] = []

    sharp_fade_stats = calculate_accuracy_row("SHARP_FADE Pitchers", sharp_fade_rows, "", "", "run_diff")
    if len(sharp_fade_rows) > 0:
        sf_hits = sum(1 for r in sharp_fade_rows if safe_float(r.get('run_diff')) < 0)
        sharp_fade_stats["hit_pct"] = f"{(sf_hits / len(sharp_fade_rows)) * 100:.1f}%"
        sharp_fade_stats["trend"] = ["HIT" if safe_float(r.get('run_diff')) < 0 else "MISS" for r in sorted(sharp_fade_rows, key=lambda x: x.get('date', ''))[-7:]]

    volatile_stats = calculate_accuracy_row("VOLATILE Pitchers", volatile_rows, "", "", "run_diff")
    if len(volatile_rows) > 0:
        # Volatile hit = attacking team overscored ITT (run_diff > 0)
        vol_hits = sum(1 for r in volatile_rows if safe_float(r.get('run_diff')) > 0)
        volatile_stats["hit_pct"] = f"{(vol_hits / len(volatile_rows)) * 100:.1f}%"
        volatile_stats["trend"] = ["HIT" if safe_float(r.get('run_diff')) > 0 else "MISS" for r in sorted(volatile_rows, key=lambda x: x.get('date', ''))[-7:]]

    walks_hazard_stats = calculate_accuracy_row("WALKS/HAZARD Pitchers", walks_hazard_rows, "", "", "run_diff")
    if len(walks_hazard_rows) > 0:
        wh_hits = sum(1 for r in walks_hazard_rows if safe_float(r.get('run_diff')) > 0)
        walks_hazard_stats["hit_pct"] = f"{(wh_hits / len(walks_hazard_rows)) * 100:.1f}%"
        walks_hazard_stats["trend"] = ["HIT" if safe_float(r.get('run_diff')) > 0 else "MISS" for r in sorted(walks_hazard_rows, key=lambda x: x.get('date', ''))[-7:]]

    pen_stats = calculate_accuracy_row("GASSED Bullpen Teams", pen_fatigue_rows, "", "", "run_diff")
    if len(pen_fatigue_rows) > 0:
        pen_hits = sum(1 for r in pen_fatigue_rows if safe_float(r.get('run_diff')) >= 0)
        pen_stats["hit_pct"] = f"{(pen_hits / len(pen_fatigue_rows)) * 100:.1f}%"
        pen_stats["trend"] = ["HIT" if safe_float(r.get('run_diff')) >= 0 else "MISS" for r in sorted(pen_fatigue_rows, key=lambda x: x.get('date', ''))[-7:]]

    burst_stats = calculate_accuracy_row("BURST Stacks", burst_rows, "burst_correct", "Y", "run_diff")

    signal_accuracy_table = [
        vul_stats, sh_stats, fade_stats, top_stack_stats, hot_stats, cold_stats,
        steam_stats, anti_chalk_stats, plat_trap_stats, strong_edge_stats,
        sharp_fade_stats, volatile_stats, walks_hazard_stats, pen_stats, burst_stats
    ]

    # Build Recent Slates Table (last 14 days)
    # We find all dates in top_stack_log
    all_dates = sorted(list(set(r.get('date') for r in top_stack_rows)), reverse=True)
    recent_dates = all_dates[:14]
    
    recent_slates = []
    for dt_str in recent_dates:
        # Top Stack
        ts_row = next((r for r in top_stack_rows if r.get('date') == dt_str), {})
        ts_team = ts_row.get('team', 'N/A')
        ts_conf = ts_row.get('attack_conf', 'N/A')
        ts_itt = ts_row.get('ITT', 'N/A')
        ts_act = ts_row.get('actual_runs', 'N/A')
        
        # TRAP instances count
        trap_count = sum(1 for r in trap_rows if r.get('date') == dt_str)
        # FADE instances count
        fade_count = sum(1 for r in fade_rows if r.get('date') == dt_str)
        # Right Game Wrong Team flag
        rg_flag = "None"
        for rg in rgwt_rows:
            if rg.get('date') == dt_str:
                if rg.get('both_scored_6plus') == 'Y':
                    rg_flag = "Both 6+ Runs"
                    break
                elif rg.get('fade_risk_team') != 'none':
                    rg_flag = f"Fade {rg.get('fade_risk_team')}"
                    
        recent_slates.append({
            "date": dt_str,
            "top_stack": ts_team,
            "conf": ts_conf,
            "itt": ts_itt,
            "actual": ts_act,
            "traps": trap_count,
            "fades": fade_count,
            "rg_flag": rg_flag
        })

    # Build Audit Flags list (scan all files)
    audit_flags_history = []
    # 1. TRAP over-delivery (IP >= 5, ER <= 2)
    for tr in trap_rows:
        try:
            ip = float(tr.get('pitcher_actual_ip', 0.0))
            er = int(tr.get('pitcher_actual_er', 0))
            if ip >= 5.0 and er <= 2:
                audit_flags_history.append({
                    "date": tr.get('date'),
                    "type": "TRAP Over-delivered",
                    "desc": f"{tr.get('pitcher')} ({tr.get('pitcher_team')}) pitched {ip} IP and allowed {er} ER."
                })
        except: pass
    # 2. FADE_RISK failure (Runs >= ITT)
    for fd in fade_rows:
        if fd.get('fade_correct') == 'N':
            audit_flags_history.append({
                "date": fd.get('date'),
                "type": "FADE_RISK Failed",
                "desc": f"{fd.get('team')} scored {fd.get('actual_runs')} runs vs ITT={fd.get('ITT')}."
            })
    # 3. RGWT match
    for rg in rgwt_rows:
        if rg.get('both_scored_6plus') == 'Y':
            audit_flags_history.append({
                "date": rg.get('date'),
                "type": "Right-Game-Wrong-Team Match",
                "desc": f"In {rg.get('game')}, both teams scored 6+ runs (Away: {rg.get('teamA_actual_runs')}, Home: {rg.get('teamB_actual_runs')})."
            })
    # 4. COLD Hitter Smash
    for cb in cold_br_rows:
        try:
            diff = float(cb.get('pts_diff', 0.0))
            if diff >= 5.0:
                audit_flags_history.append({
                    "date": cb.get('date'),
                    "type": "COLD_HIGH_BR Hitter Smash",
                    "desc": f"{cb.get('player')} ({cb.get('team')}) scored {cb.get('actual_dk_pts')} DK points (+{diff:.1f} vs baseline)."
                })
        except: pass

    # Sort flags by date descending
    audit_flags_history.sort(key=lambda x: x['date'], reverse=True)

    # Load last 7 digests
    digest_files = sorted(glob.glob(os.path.join(digests_dir, "digest_*.txt")), reverse=True)
    recent_digests = []
    for fpath in digest_files[:7]:
        fname = os.path.basename(fpath)
        fdate = fname.replace("digest_", "").replace(".txt", "")
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
            recent_digests.append({"date": fdate, "content": content})
        except Exception:
            pass

    # HTML Template
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>OMEGA Passive Audit Dashboard</title>
    <style>
        :root {{
            --bg-color: #0b0f19;
            --card-bg: rgba(17, 24, 39, 0.7);
            --border-color: rgba(255, 255, 255, 0.08);
            --text-color: #f3f4f6;
            --text-muted: #9ca3af;
            --primary: #3b82f6;
            --primary-glow: rgba(59, 130, 246, 0.15);
            --success: #10b981;
            --danger: #ef4444;
            --warning: #f59e0b;
        }}
        
        body {{
            margin: 0;
            padding: 0;
            background-color: var(--bg-color);
            color: var(--text-color);
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.5;
            -webkit-font-smoothing: antialiased;
        }}

        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 24px 16px;
        }}

        header {{
            margin-bottom: 32px;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 16px;
        }}

        h1 {{
            font-size: 28px;
            font-weight: 700;
            margin: 0 0 8px 0;
            background: linear-gradient(90deg, #60a5fa, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }}

        .timestamp {{
            font-size: 14px;
            color: var(--text-muted);
        }}

        .section {{
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            backdrop-filter: blur(10px);
        }}

        h2 {{
            font-size: 20px;
            margin-top: 0;
            margin-bottom: 16px;
            border-left: 4px solid var(--primary);
            padding-left: 10px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            text-align: left;
        }}

        th, td {{
            padding: 12px 16px;
            border-bottom: 1px solid var(--border-color);
        }}

        th {{
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            color: var(--text-muted);
            font-weight: 600;
        }}

        td {{
            font-size: 15px;
        }}

        tr:last-child td {{
            border-bottom: none;
        }}

        /* Badge/Trend Pill styles */
        .trend-container {{
            display: flex;
            gap: 4px;
        }}

        .trend-pill {{
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
        }}

        .trend-pill.hit {{
            background-color: var(--success);
            box-shadow: 0 0 6px var(--success);
        }}

        .trend-pill.miss {{
            background-color: var(--danger);
            box-shadow: 0 0 6px var(--danger);
        }}

        .status-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            font-weight: 600;
        }}

        .status-badge.warning {{
            background-color: rgba(245, 158, 11, 0.15);
            color: var(--warning);
        }}

        .status-badge.danger {{
            background-color: rgba(239, 68, 68, 0.15);
            color: var(--danger);
        }}

        .status-badge.none {{
            background-color: rgba(156, 163, 175, 0.1);
            color: var(--text-muted);
        }}

        .flag-item {{
            padding: 12px;
            border-bottom: 1px solid var(--border-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        .flag-item:last-child {{
            border-bottom: none;
        }}

        .flag-meta {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}

        .flag-title {{
            font-weight: 600;
            font-size: 14px;
        }}

        .flag-desc {{
            font-size: 13px;
            color: var(--text-muted);
        }}

        .flag-date {{
            font-size: 12px;
            color: var(--text-muted);
            background: rgba(255, 255, 255, 0.04);
            padding: 2px 6px;
            border-radius: 4px;
        }}

        details {{
            margin-bottom: 12px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            background: rgba(255, 255, 255, 0.01);
        }}

        details[open] {{
            background: rgba(255, 255, 255, 0.02);
        }}

        summary {{
            padding: 14px 16px;
            font-weight: 600;
            cursor: pointer;
            outline: none;
            user-select: none;
        }}

        pre {{
            margin: 0;
            padding: 16px;
            border-top: 1px solid var(--border-color);
            background: rgba(0, 0, 0, 0.3);
            font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace;
            font-size: 13px;
            overflow-x: auto;
            white-space: pre-wrap;
            color: #38bdf8;
        }}

        .links-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 12px;
        }}

        .link-card {{
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--border-color);
            padding: 16px;
            border-radius: 8px;
            text-decoration: none;
            color: var(--text-color);
            display: flex;
            justify-content: space-between;
            align-items: center;
            transition: all 0.2s ease;
        }}

        .link-card:hover {{
            background: var(--primary-glow);
            border-color: var(--primary);
            transform: translateY(-2px);
        }}

        .link-name {{
            font-weight: 600;
            font-size: 14px;
        }}

        .link-arrow {{
            color: var(--primary);
            font-weight: bold;
        }}

        /* Responsive */
        @media (max-width: 768px) {{
            .section {{
                padding: 16px;
            }}
            th, td {{
                padding: 10px 12px;
                font-size: 13px;
            }}
            h1 {{
                font-size: 24px;
            }}
            h2 {{
                font-size: 18px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>⚾ OMEGA Audit Dashboard</h1>
            <div class="timestamp">Last updated: {timestamp} (Eastern Time rollover tracking)</div>
        </header>

        <!-- Signal Accuracy Section -->
        <div class="section">
            <h2>Running Signal Accuracy</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Signal Type</th>
                            <th>Instances (N)</th>
                            <th>Hit Rate</th>
                            <th>Avg Run Diff</th>
                            <th>Trend (Last 7)</th>
                        </tr>
                    </thead>
                    <tbody>"""
    
    for row in signal_accuracy_table:
        trend_html = ""
        for t in row["trend"]:
            c_class = "hit" if t == "HIT" else "miss"
            trend_html += f'<span class="trend-pill {c_class}" title="{t}"></span>'
            
        html += f"""
                        <tr>
                            <td><strong>{row["name"]}</strong></td>
                            <td>{row["n"]}</td>
                            <td>{row["hit_pct"]}</td>
                            <td>{row["avg_diff"]}</td>
                            <td>
                                <div class="trend-container">
                                    {trend_html if trend_html else '<span style="color:var(--text-muted); font-size:12px;">N/A</span>'}
                                </div>
                            </td>
                        </tr>"""
                        
    html += """
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Recent Slates Section -->
        <div class="section">
            <h2>Recent Slates</h2>
            <div style="overflow-x: auto;">
                <table>
                    <thead>
                        <tr>
                            <th>Date</th>
                            <th>Top Stack</th>
                            <th>Conf</th>
                            <th>ITT</th>
                            <th>Actual Runs</th>
                            <th>TRAP Count</th>
                            <th>FADE Count</th>
                            <th>Audit Flags</th>
                        </tr>
                    </thead>
                    <tbody>"""

    for slate in recent_slates:
        flg_class = "none"
        if "6+" in slate["rg_flag"]:
            flg_class = "danger"
        elif "Fade" in slate["rg_flag"]:
            flg_class = "warning"
            
        html += f"""
                        <tr>
                            <td><code>{slate["date"]}</code></td>
                            <td><strong>{slate["top_stack"]}</strong></td>
                            <td>{slate["conf"]}</td>
                            <td>{slate["itt"]}</td>
                            <td>{slate["actual"]}</td>
                            <td>{slate["traps"]}</td>
                            <td>{slate["fades"]}</td>
                            <td><span class="status-badge {flg_class}">{slate["rg_flag"]}</span></td>
                        </tr>"""

    html += """
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Audit Flags Section -->
        <div class="section">
            <h2>Audit Flags</h2>
            <div style="max-height: 320px; overflow-y: auto; border: 1px solid var(--border-color); border-radius: 8px;">"""
            
    if audit_flags_history:
        for flg in audit_flags_history:
            html += f"""
                <div class="flag-item">
                    <div class="flag-meta">
                        <div class="flag-title">{flg["type"]}</div>
                        <div class="flag-desc">{flg["desc"]}</div>
                    </div>
                    <div class="flag-date">{flg["date"]}</div>
                </div>"""
    else:
        html += """
                <div style="padding: 20px; text-align: center; color: var(--text-muted); font-size: 14px;">
                    No audit flags triggered yet.
                </div>"""

    html += """
            </div>
        </div>

        <!-- Collapsible Digests -->
        <div class="section">
            <h2>Recent Digests</h2>"""
            
    if recent_digests:
        for dig in recent_digests:
            html += f"""
            <details>
                <summary>Digest - {dig["date"]}</summary>
                <pre>{dig["content"]}</pre>
            </details>"""
    else:
        html += """
            <div style="text-align: center; color: var(--text-muted); font-size: 14px; padding: 10px 0;">
                No digests generated yet.
            </div>"""

    html += """
        </div>

        <!-- CSV Downloads -->
        <div class="section">
            <h2>Running Data Downloads</h2>
            <div class="links-grid">"""
            
    csv_links = [
        ("trap_arm_log.csv", "Trap Pitchers Log"),
        ("cold_high_br_log.csv", "Cold High blended rating Log"),
        ("fade_risk_log.csv", "Fade Risk Log"),
        ("hot_msmi_log.csv", "Hot MSMI Log"),
        ("top_stack_log.csv", "Top Stack Log"),
        ("right_game_wrong_team_log.csv", "RGWT Audit Log"),
        ("anti_chalk_smash_log.csv", "Anti-Chalk Smash Log"),
        ("steam_log.csv", "Steam Log"),
        ("platoon_trap_log.csv", "Platoon Trap Log"),
        ("strong_edge_log.csv", "Strong Edge Log"),
        ("elite_platoon_log.csv", "Elite Platoon Log"),
        ("sharp_fade_pitcher_log.csv", "Sharp Fade Pitchers Log"),
        ("dqi_log.csv", "DQI Log"),
        ("pitcher_volatile_log.csv", "Volatile Pitchers Log"),
        ("pitcher_walks_hazard_log.csv", "Walks/Hazard Pitchers Log"),
        ("pen_fatigue_log.csv", "Bullpen Fatigue Log"),
        ("burst_log.csv", "Burst Log")
    ]
    
    for fn, label in csv_links:
        raw_url = f"https://raw.githubusercontent.com/kklosowiak/MlbDFS/audit/july-2026/scratch/passive_tracker/signals/{fn}"
        html += f"""
                <a href="{raw_url}" target="_blank" class="link-card">
                    <span class="link-name">{label}</span>
                    <span class="link-arrow">&rarr;</span>
                </a>"""

    html += """
            </div>
        </div>
    </div>
</body>
</html>"""

    # Write file
    try:
        with open(dashboard_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"Successfully generated dashboard at {dashboard_path}")
    except Exception as e:
        print(f"Error writing dashboard HTML: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
