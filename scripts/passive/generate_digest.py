import os
import sys
import csv
import json
import argparse
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

def get_yesterday_et_str():
    dt_utc = datetime.now(timezone.utc)
    if ZoneInfo:
        dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
    else:
        dt_et = dt_utc - timedelta(hours=4)
    yesterday_et = dt_et - timedelta(days=1)
    return yesterday_et.strftime("%Y-%m-%d")

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

def main():
    parser = argparse.ArgumentParser(description="OMEGA Daily Digest Generator")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD), defaults to yesterday")
    args = parser.parse_args()

    date_str = args.date or get_yesterday_et_str()

    target_dir = os.path.join("scratch", "passive_tracker", "digests")
    os.makedirs(target_dir, exist_ok=True)
    digest_path = os.path.join(target_dir, f"digest_{date_str}.txt")

    # Load prediction files to see which capture was used
    slates_dir = os.path.join("scratch", "passive_tracker", "slates")
    results_2220 = os.path.join(slates_dir, f"omega-results_{date_str}_2220UTC.json")
    results_1530 = os.path.join(slates_dir, f"omega-results_{date_str}_1530UTC.json")

    capture_status = "not found"
    is_fallback = False
    lock_data = None
    if os.path.exists(results_2220):
        try:
            with open(results_2220, "r", encoding="utf-8") as f:
                lock_data = json.load(f)
            if lock_data.get("teams"):
                capture_status = "6:20pm snapshot confirmed"
        except Exception:
            pass

    if not lock_data and os.path.exists(results_1530):
        try:
            with open(results_1530, "r", encoding="utf-8") as f:
                lock_data = json.load(f)
            if lock_data.get("teams"):
                capture_status = "fell back to 11:30am"
                is_fallback = True
        except Exception:
            pass

    if is_fallback:
        try:
            repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            if repo_root not in sys.path:
                sys.path.insert(0, repo_root)
            from utils.notifier import Notifier
            notifier = Notifier()
            msg = (
                f"⚠️ *OMEGA STALE CAPTURE ALERT* ⚠️\n\n"
                f"*Date*: `{date_str}`\n"
                f"*Status*: Missing 6:20pm ET capture!\n"
                f"*Action*: Digest fell back to stale 11:30am ET snapshot.\n\n"
                f"_Check GitHub Actions logs for omega_capture.yml._"
            )
            notifier.send_message(msg)
        except Exception as e:
            print(f"Warning: Could not fire Telegram alert for stale capture fallback: {e}")

    if not lock_data or not lock_data.get("teams"):
        # No slate today
        with open(digest_path, "w", encoding="utf-8") as f:
            f.write(f"=== OMEGA SIGNAL DIGEST - {date_str} ===\n")
            if is_fallback:
                f.write("⚠️ WARNING: STALE CAPTURE FALLBACK (6:20pm capture missing; fell back to 11:30am snapshot)\n")
            f.write("NO SLATE - off day or no data captured.\n")
            f.write("=== END ===\n")
        print(f"Generated empty digest for {date_str} (no slate).")
        sys.exit(0)

    # Read active signal logs for this date from the CSVs
    signals_dir = os.path.join("scratch", "passive_tracker", "signals")
    
    # Helpers to load only today's rows
    def get_today_rows(file_name):
        path = os.path.join(signals_dir, file_name)
        return [r for r in read_csv_rows(path) if r.get('date') == date_str]

    trap_vuln_today = get_today_rows("trap_vulnerable_log.csv")
    trap_short_today = get_today_rows("trap_short_leash_log.csv")
    trap_today = trap_vuln_today + trap_short_today
    cold_br_today = get_today_rows("cold_high_br_log.csv")
    fade_today = get_today_rows("fade_risk_log.csv")
    hot_msmi_today = get_today_rows("hot_msmi_log.csv")
    top_stack_today = get_today_rows("top_stack_log.csv")
    rgwt_today = get_today_rows("right_game_wrong_team_log.csv")
    anti_chalk_today = get_today_rows("anti_chalk_smash_log.csv")
    steam_today = get_today_rows("steam_log.csv")
    plat_trap_today = get_today_rows("platoon_trap_log.csv")
    strong_edge_today = get_today_rows("strong_edge_log.csv")
    sharp_fade_today = get_today_rows("sharp_fade_pitcher_log.csv")
    volatile_today = get_today_rows("pitcher_volatile_log.csv")
    walks_hazard_today = get_today_rows("pitcher_walks_hazard_log.csv")
    pen_fatigue_today = get_today_rows("pen_fatigue_log.csv")
    burst_today = get_today_rows("burst_log.csv")

    # Construct digest lines
    lines = []
    lines.append(f"=== OMEGA SIGNAL DIGEST - {date_str} ===")
    if is_fallback:
        lines.append("⚠️ WARNING: STALE CAPTURE FALLBACK (6:20pm capture missing; fell back to 11:30am snapshot)")
    lines.append("")
    lines.append(f"CAPTURE: {capture_status}")

    # Top Stack
    if top_stack_today:
        ts = top_stack_today[0]
        itt = safe_float(ts.get('ITT'))
        act = safe_float(ts.get('actual_runs'))
        diff = safe_float(ts.get('run_diff'))
        lines.append(f"TOP STACK: {ts.get('team')} | conf={ts.get('attack_conf')} | ITT={itt} | actual={act} | diff={diff:+.1f} (note: team-level attack_conf has an unreliable historical correlation to stack outcomes per the July audit)")
    else:
        lines.append("TOP STACK: None")

    # Trap Arms
    lines.append(f"TRAP ARMS ({len(trap_today)} instances):")
    for tr in trap_today:
        pitcher = tr.get('pitcher')
        team = tr.get('pitcher_team')
        type_lbl = tr.get('trap_type', 'Neutral')
        conf = tr.get('attack_conf')
        itt = safe_float(tr.get('ITT'))
        act = safe_float(tr.get('actual_runs_against'))
        diff = safe_float(tr.get('run_diff'))
        ip = tr.get('pitcher_actual_ip')
        er = tr.get('pitcher_actual_er')
        
        # Over-delivered if IP >= 5 and ER <= 2
        try:
            is_over = float(ip) >= 5.0 and int(er) <= 2
        except:
            is_over = False
        deliv = "OVER-DELIVERED" if is_over else "NORMAL"
        lines.append(f"  {pitcher} ({type_lbl}) vs {team}: attack_conf={conf} ITT={itt} actual={act} diff={diff:+.1f} | {ip}IP {er}ER -> {deliv}")

    # Fade Risk
    lines.append(f"FADE_RISK ({len(fade_today)} instances):")
    for fd in fade_today:
        team = fd.get('team')
        div = fd.get('divergence')
        mon = fd.get('money_pct')
        itt = safe_float(fd.get('ITT'))
        act = safe_float(fd.get('actual_runs'))
        res = "CORRECT FADE" if fd.get('fade_correct') == 'Y' else "FADE FAILED"
        lines.append(f"  {team}: div={div} mon%={mon} | ITT={itt} actual={act}R -> {res}")

    # Steam
    lines.append(f"STEAM ({len(steam_today)} team fires):")
    for st in steam_today:
        team = st.get('team')
        conf = st.get('attack_conf')
        itt = safe_float(st.get('ITT'))
        act = safe_float(st.get('actual_runs'))
        lines.append(f"  {team}: conf={conf} ITT={itt} | actual={act}R (note: is_steam is a refuted/reversed signal per the July audit)")

    # Hot MSMI Top 3
    hot_sorted = sorted(hot_msmi_today, key=lambda x: safe_float(x.get('actual_dk_pts')), reverse=True)
    lines.append("HOT_MSMI TOP 3:")
    for h_row in hot_sorted[:3]:
        lines.append(f"  {h_row.get('player')} ({h_row.get('team')}): {h_row.get('actual_dk_pts')} DK pts")

    # Anti-Chalk Smash
    lines.append(f"ANTI_CHALK_SMASH ({len(anti_chalk_today)} fires):")
    for ac in anti_chalk_today:
        player = ac.get('player')
        team = ac.get('team')
        blended = ac.get('blended_rating')
        act = ac.get('actual_dk_pts')
        diff = safe_float(ac.get('pts_diff'))
        lines.append(f"  {player} ({team}): blended={blended} | actual={act}DKpts | {diff:+.1f} vs baseline")

    # Cold High BR
    lines.append(f"COLD_HIGH_BR_WARNING ({len(cold_br_today)} fires):")
    for cb in cold_br_today:
        player = cb.get('player')
        team = cb.get('team')
        blended = cb.get('blended_rating')
        act = cb.get('actual_dk_pts')
        diff = safe_float(cb.get('pts_diff'))
        lines.append(f"  {player} ({team}): blended={blended} | actual={act}DKpts | {diff:+.1f} vs baseline (note: this flag has an unreliable historical hit rate per the July audit)")

    # Platoon Trap
    lines.append(f"PLATOON_TRAP ({len(plat_trap_today)} fires):")
    for pt in plat_trap_today:
        player = pt.get('player')
        team = pt.get('team')
        act = pt.get('actual_dk_pts')
        diff = safe_float(pt.get('pts_diff'))
        lines.append(f"  {player} ({team}): actual={act}DKpts | {diff:+.1f} vs baseline")

    # Strong Edge
    lines.append(f"STRONG_EDGE ({len(strong_edge_today)} fires):")
    for se in strong_edge_today:
        player = se.get('player')
        team = se.get('team')
        act = se.get('actual_dk_pts')
        diff = safe_float(se.get('pts_diff'))
        lines.append(f"  {player} ({team}): actual={act}DKpts | {diff:+.1f} vs baseline")

    # Sharp Fade Pitchers
    lines.append(f"SHARP_FADE PITCHERS ({len(sharp_fade_today)} instances):")
    for sf_row in sharp_fade_today:
        pitcher = sf_row.get('pitcher')
        team = sf_row.get('pitcher_team')
        itt = safe_float(sf_row.get('ITT'))
        act = safe_float(sf_row.get('actual_runs_against'))
        diff = safe_float(sf_row.get('run_diff'))
        lines.append(f"  {pitcher} vs {team}: ITT={itt} actual={act}R diff={diff:+.1f}")

    # Volatile Pitchers
    lines.append(f"VOLATILE PITCHERS ({len(volatile_today)}):")
    for vol in volatile_today:
        pitcher = vol.get('pitcher')
        itt = safe_float(vol.get('ITT'))
        act = safe_float(vol.get('actual_runs_against'))
        delta = safe_float(vol.get('conf_delta'))
        lines.append(f"  {pitcher}: conf_delta={delta:+.1f} | ITT={itt} actual={act}R")

    # Walks Hazard Pitchers
    lines.append(f"WALKS/HAZARD PITCHERS ({len(walks_hazard_today)}):")
    for wh in walks_hazard_today:
        pitcher = wh.get('pitcher')
        wp = wh.get('walks_penalty')
        hz = wh.get('is_hazard')
        itt = safe_float(wh.get('ITT'))
        act = safe_float(wh.get('actual_runs_against'))
        diff = safe_float(wh.get('run_diff'))
        lines.append(f"  {pitcher} (WALKS={wp} HAZ={hz}): ITT={itt} actual={act}R diff={diff:+.1f}")

    # Gassed/Fatigued Bullpen
    lines.append(f"GASSED/FATIGUED PEN ({len(pen_fatigue_today)} teams):")
    for pf in pen_fatigue_today:
        team = pf.get('team')
        itt = safe_float(pf.get('ITT'))
        act = safe_float(pf.get('actual_runs'))
        res = "HIT" if act >= itt else "MISS"
        lines.append(f"  {team}: actual={act}R vs ITT={itt} -> {res}")

    # Burst Stacks
    lines.append(f"BURST ({len(burst_today)} teams):")
    for bs in burst_today:
        team = bs.get('team')
        itt = safe_float(bs.get('ITT'))
        act = safe_float(bs.get('actual_runs'))
        res = "CORRECT" if bs.get('burst_correct') == 'Y' else "MISS"
        lines.append(f"  {team}: actual={act}R vs ITT={itt} -> {res}")

    # Right Game Wrong Team
    lines.append("RIGHT GAME WRONG TEAM:")
    for rg in rgwt_today:
        game = rg.get('game')
        both = rg.get('both_scored_6plus')
        h_won = rg.get('higher_conf_team_won_scoring')
        lines.append(f"  {game}: both scored 6+? {both} | higher-conf team won scoring? {h_won}")

    # ==================== RUNNING ACCURACY STATISTICS ====================
    # Read ALL history from CSVs to compute overall averages
    all_trap_vuln = read_csv_rows(os.path.join(signals_dir, "trap_vulnerable_log.csv"))
    all_trap_short = read_csv_rows(os.path.join(signals_dir, "trap_short_leash_log.csv"))
    all_fade = read_csv_rows(os.path.join(signals_dir, "fade_risk_log.csv"))
    all_ts = read_csv_rows(os.path.join(signals_dir, "top_stack_log.csv"))
    all_msmi = read_csv_rows(os.path.join(signals_dir, "hot_msmi_log.csv"))
    all_steam = read_csv_rows(os.path.join(signals_dir, "steam_log.csv"))
    all_ac = read_csv_rows(os.path.join(signals_dir, "anti_chalk_smash_log.csv"))
    all_pt = read_csv_rows(os.path.join(signals_dir, "platoon_trap_log.csv"))
    all_se = read_csv_rows(os.path.join(signals_dir, "strong_edge_log.csv"))
    all_sf = read_csv_rows(os.path.join(signals_dir, "sharp_fade_pitcher_log.csv"))
    all_vol = read_csv_rows(os.path.join(signals_dir, "pitcher_volatile_log.csv"))
    all_wh = read_csv_rows(os.path.join(signals_dir, "pitcher_walks_hazard_log.csv"))
    all_pf = read_csv_rows(os.path.join(signals_dir, "pen_fatigue_log.csv"))
    all_bs = read_csv_rows(os.path.join(signals_dir, "burst_log.csv"))
    
    unique_dates = set(r.get('date') for r in all_ts)
    n_slates = len(unique_dates)

    # Trap arm vulnerable vs short leash split
    vul_arms = all_trap_vuln
    sh_arms = all_trap_short
    
    def pct_underscored_itt(rows):
        if not rows: return 0.0
        # Underscored means Opposing Runs < ITT (i.e. run_diff < 0)
        underscored = sum(1 for x in rows if safe_float(x.get('run_diff')) < 0)
        return float(round((underscored / len(rows)) * 100, 1))
        
    def avg_run_diff(rows):
        if not rows: return 0.0
        diffs = [safe_float(x.get('run_diff')) for x in rows]
        return float(round(sum(diffs) / len(rows), 2))

    vul_pct = pct_underscored_itt(vul_arms)
    vul_diff = avg_run_diff(vul_arms)
    
    sh_pct = pct_underscored_itt(sh_arms)
    sh_diff = avg_run_diff(sh_arms)

    # Fade Risk
    fade_size = len(all_fade)
    fade_corr_pct = float(round((sum(1 for x in all_fade if x.get('fade_correct') == 'Y') / fade_size) * 100, 1)) if fade_size > 0 else 0.0
    fade_diff = avg_run_diff(all_fade)

    # Top Stack
    ts_size = len(all_ts)
    ts_hit_pct = float(round((sum(1 for x in all_ts if x.get('model_correct') == 'Y') / ts_size) * 100, 1)) if ts_size > 0 else 0.0

    # Hot MSMI
    msmi_size = len(all_msmi)
    msmi_avg = float(round(sum(safe_float(x.get('actual_dk_pts')) for x in all_msmi) / msmi_size, 2)) if msmi_size > 0 else 0.0

    # Steam
    steam_size = len(all_steam)
    steam_corr_pct = float(round((sum(1 for x in all_steam if x.get('steam_correct') == 'Y') / steam_size) * 100, 1)) if steam_size > 0 else 0.0
    steam_diff = avg_run_diff(all_steam)

    # Anti-Chalk Smash
    ac_size = len(all_ac)
    ac_avg_diff = float(round(sum(safe_float(x.get('pts_diff')) for x in all_ac) / ac_size, 2)) if ac_size > 0 else 0.0

    # Platoon Trap
    pt_size = len(all_pt)
    pt_under_pct = float(round((sum(1 for x in all_pt if safe_float(x.get('pts_diff')) < 0) / pt_size) * 100, 1)) if pt_size > 0 else 0.0

    # Strong Edge
    se_size = len(all_se)
    se_avg_diff = float(round(sum(safe_float(x.get('pts_diff')) for x in all_se) / se_size, 2)) if se_size > 0 else 0.0

    # Sharp Fade Pitcher
    sf_size = len(all_sf)
    sf_und_pct = float(round((sum(1 for x in all_sf if safe_float(x.get('run_diff')) < 0) / sf_size) * 100, 1)) if sf_size > 0 else 0.0

    # Volatile Pitcher
    vol_size = len(all_vol)
    # Volatile: attacking team overscored ITT (i.e. run_diff > 0)
    vol_over_pct = float(round((sum(1 for x in all_vol if safe_float(x.get('run_diff')) > 0) / vol_size) * 100, 1)) if vol_size > 0 else 0.0

    # Walks Hazard Pitcher
    wh_size = len(all_wh)
    # Walks/Hazard: attacking team overscored ITT (i.e. run_diff > 0)
    wh_over_pct = float(round((sum(1 for x in all_wh if safe_float(x.get('run_diff')) > 0) / wh_size) * 100, 1)) if wh_size > 0 else 0.0

    # Gassed Pen
    pf_size = len(all_pf)
    pf_hit_pct = float(round((sum(1 for x in all_pf if safe_float(x.get('run_diff')) >= 0) / pf_size) * 100, 1)) if pf_size > 0 else 0.0

    # Burst Stacks
    bs_size = len(all_bs)
    bs_hit_pct = float(round((sum(1 for x in all_bs if x.get('burst_correct') == 'Y') / bs_size) * 100, 1)) if bs_size > 0 else 0.0

    lines.append("")
    lines.append(f"RUNNING ACCURACY ({n_slates} slates tracked):")
    lines.append(f"  TRAP/Vulnerable: {vul_pct}% underscored ITT | avg diff {vul_diff:+.2f}R")
    lines.append(f"  TRAP/Short Leash: {sh_pct}% underscored ITT | avg diff {sh_diff:+.2f}R")
    lines.append(f"  FADE_RISK: {fade_corr_pct}% correct | avg diff {fade_diff:+.2f}R")
    lines.append(f"  Top Stack hit ITT: {ts_hit_pct}% (note: team-level attack_conf has no predictive power per the July audit)")
    lines.append(f"  HOT_MSMI avg: {msmi_avg} DK pts")
    lines.append(f"  STEAM: {steam_corr_pct}% correct | avg {steam_diff:+.2f}R (note: steam is a refuted/reversed signal per the July audit)")
    lines.append(f"  ANTI_CHALK_SMASH: avg {ac_avg_diff:+.2f} DK pts vs baseline")
    lines.append(f"  PLATOON_TRAP: {pt_under_pct}% underperformed baseline")
    lines.append(f"  STRONG_EDGE: avg {se_avg_diff:+.2f} DK pts vs baseline")
    lines.append(f"  SHARP_FADE pitchers: {sf_und_pct}% attacking team underscored ITT")
    lines.append(f"  VOLATILE pitchers - attacking team overscored ITT: {vol_over_pct}%")
    lines.append(f"  WALKS/HAZARD pitchers - attacking team overscored ITT: {wh_over_pct}%")
    lines.append(f"  GASSED pen teams: {pf_hit_pct}% hit ITT")
    lines.append(f"  BURST teams: {bs_hit_pct}% hit ITT (note: burst is a refuted signal per the July audit)")

    # Audit Flags
    audit_flags = []
    
    # 1. TRAP over-delivery (IP >= 5 and ER <= 2)
    for tr in trap_today:
        try:
            ip = float(tr.get('pitcher_actual_ip', 0.0))
            er = int(tr.get('pitcher_actual_er', 0))
            if ip >= 5.0 and er <= 2:
                audit_flags.append(f"TRAP Arm Outperformed Expectation: {tr.get('pitcher')} ({ip} IP, {er} ER)")
        except:
            pass

    # 2. FADE_RISK failure (Runs >= ITT)
    for fd in fade_today:
        if fd.get('fade_correct') == 'N':
            audit_flags.append(f"FADE_RISK Outperformed ITT: {fd.get('team')} scored {fd.get('actual_runs')} vs ITT={fd.get('ITT')}")

    # 3. Right game wrong team match (both scored 6+)
    for rg in rgwt_today:
        if rg.get('both_scored_6plus') == 'Y':
            audit_flags.append(f"Right-Game-Wrong-Team Match: {rg.get('game')} (Both scored 6+ runs)")

    # 4. COLD_HIGH_BR_WARNING failure (Outscored baseline by +5+ pts)
    for cb in cold_br_today:
        try:
            diff = float(cb.get('pts_diff', 0.0))
            if diff >= 5.0:
                audit_flags.append(f"COLD_HIGH_BR Hitter Outperformed Baseline: {cb.get('player')} outscored baseline by +{diff:.1f} pts (note: this flag has an unreliable historical hit rate per the July audit)")
        except:
            pass

    lines.append("")
    lines.append("AUDIT FLAGS:")
    if audit_flags:
        for flg in audit_flags:
            lines.append(f"  {flg}")
    else:
        lines.append("  None")

    lines.append("")
    lines.append("=== END ===")

    # Write file
    with open(digest_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"Successfully generated digest for {date_str} with {len(lines)} lines.")

if __name__ == "__main__":
    main()
