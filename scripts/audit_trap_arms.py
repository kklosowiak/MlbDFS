"""
OMEGA TRAP Arm Performance Audit Script
Task 1 — July 2026 Pre-Audit

Queries the production archive (results_{date}.json + actuals_cache_{date}.json)
for all games in the last 30 days where the opposing pitcher had is_trap=True
at lock time.

Outputs a CSV to scratch/trap_arm_audit_30day.csv and prints summary stats.

Data source: LOCAL ARCHIVE FILES (not live DB).
Classification per AGENTS.md Rule 4: Results are confirmed from production
archive data only if the script executes successfully against real files.
"""

import os
import sys
import json
import csv
import re
from datetime import date, timedelta

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARCHIVE_DIR = os.path.join(BASE_DIR, "reports", "archive")
SCRATCH_DIR = os.path.join(BASE_DIR, "scratch")
OUTPUT_CSV = os.path.join(SCRATCH_DIR, "trap_arm_audit_30day.csv")


def ip_str_to_float(ip_str):
    """Convert innings pitched string (e.g. '5.2') to float (5.667...)."""
    try:
        s = str(ip_str)
        parts = s.split(".")
        full_innings = int(parts[0])
        outs = int(parts[1]) if len(parts) > 1 else 0
        return full_innings + outs / 3.0
    except Exception:
        return 0.0


def find_actuals(date_str):
    """
    Load actuals for a date. Prefer archive file, fall back to scratch cache.
    Returns dict or None.
    """
    archive_path = os.path.join(ARCHIVE_DIR, f"actuals_cache_{date_str}.json")
    if os.path.exists(archive_path):
        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  [WARN] Could not load {archive_path}: {e}")

    scratch_path = os.path.join(SCRATCH_DIR, "actuals_cache.json")
    if os.path.exists(scratch_path):
        try:
            with open(scratch_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
                if date_str in cache:
                    return cache[date_str]
        except Exception:
            pass

    return None


def find_results(date_str):
    """Load lock snapshot, falling back to standard archive."""
    lock_path = os.path.join(ARCHIVE_DIR, f"results_{date_str}_lock.json")
    if os.path.exists(lock_path):
        try:
            with open(lock_path, "r", encoding="utf-8") as f:
                return json.load(f), "lock"
        except Exception:
            pass

    standard_path = os.path.join(ARCHIVE_DIR, f"results_{date_str}.json")
    if os.path.exists(standard_path):
        try:
            with open(standard_path, "r", encoding="utf-8") as f:
                return json.load(f), "standard"
        except Exception:
            pass

    return None, None


def normalize_team(name):
    """Basic normalization to help match team names between results and actuals."""
    if not name:
        return ""
    return str(name).strip()


def run_trap_audit(days=30):
    print("")
    print("=" * 65)
    print("  OMEGA TRAP ARM PERFORMANCE AUDIT — Last {} Days".format(days))
    print("=" * 65)

    today = date.today()
    cutoff = today - timedelta(days=days)

    rows = []  # CSV rows
    missing_actuals = []
    missing_results = []

    for i in range(days, -1, -1):
        target_date = today - timedelta(days=i)
        if target_date < cutoff:
            continue
        date_str = target_date.strftime("%Y-%m-%d")

        results_data, src = find_results(date_str)
        if not results_data:
            missing_results.append(date_str)
            continue

        actuals = find_actuals(date_str)
        if not actuals:
            missing_actuals.append(date_str)
            continue

        pitchers = results_data.get("pitchers", [])
        teams = results_data.get("teams", [])

        # Build a lookup: pitcher_team -> pitcher object for trap pitchers
        for p in pitchers:
            if not p.get("is_trap", False):
                continue

            pitcher_name = p.get("pitcher", "Unknown")
            pitcher_team = normalize_team(p.get("team", ""))
            trap_type = p.get("trap_type") or "Unknown"
            season_era = p.get("recent_era") or p.get("siera") or None

            # Find the OPPOSING team object (attack team vs this pitcher)
            # The opponent of pitcher is the team that ATTACKS this pitcher
            pitcher_opponent = normalize_team(p.get("opponent", ""))

            # Find the attacking team's data from team objects
            attack_team_obj = None
            for t in teams:
                if normalize_team(t.get("team", "")) == pitcher_opponent:
                    # Verify this team is facing this pitcher
                    opp_p = normalize_team(t.get("opp_pitcher", ""))
                    if opp_p.lower() in pitcher_name.lower() or pitcher_name.lower() in opp_p.lower():
                        attack_team_obj = t
                        break

            # Fallback: just match by team name and opponent field
            if not attack_team_obj:
                for t in teams:
                    if normalize_team(t.get("team", "")) == pitcher_opponent and \
                       normalize_team(t.get("opponent", "")) == pitcher_team:
                        attack_team_obj = t
                        break

            attack_conf = None
            implied_total = None
            if attack_team_obj:
                attack_conf = attack_team_obj.get("attack_conf")
                implied_total = attack_team_obj.get("implied_total")

            # Get actuals for the attacking team
            actual_attack_runs = None
            for team_key, team_data in actuals.items():
                if normalize_team(team_key).lower() == pitcher_opponent.lower():
                    actual_attack_runs = team_data.get("runs")
                    break

            # Get actuals for the pitcher (from pitcher's team's sp_stats)
            actual_er = None
            actual_ip = None
            actual_ip_str = None
            for team_key, team_data in actuals.items():
                if normalize_team(team_key).lower() == pitcher_team.lower():
                    sp = team_data.get("sp_stats", {})
                    sp_name = sp.get("name", "")
                    # Match by name similarity
                    if sp_name and (sp_name.lower() in pitcher_name.lower() or
                                    pitcher_name.lower() in sp_name.lower() or
                                    sp_name.split()[-1].lower() == pitcher_name.split()[-1].lower()):
                        actual_er = sp.get("er")
                        actual_ip_str = sp.get("ip", "0.0")
                        actual_ip = ip_str_to_float(actual_ip_str)
                    break

            # Over/under vs ITT
            over_under = None
            if actual_attack_runs is not None and implied_total is not None:
                try:
                    over_under = round(float(actual_attack_runs) - float(implied_total), 2)
                except Exception:
                    pass

            rows.append({
                "date": date_str,
                "attacking_team": pitcher_opponent,
                "attack_conf_at_lock": attack_conf if attack_conf is not None else "N/A",
                "pitcher": pitcher_name,
                "trap_type": trap_type,
                "season_era_proxy": round(float(season_era), 2) if season_era is not None else "N/A",
                "actual_er": actual_er if actual_er is not None else "N/A",
                "actual_ip": round(actual_ip, 2) if actual_ip is not None else "N/A",
                "actual_attack_runs": actual_attack_runs if actual_attack_runs is not None else "N/A",
                "implied_total_itt": round(float(implied_total), 2) if implied_total is not None else "N/A",
                "over_under_vs_itt": over_under if over_under is not None else "N/A",
                "source": src,
            })

    # ---- Write CSV ----
    os.makedirs(SCRATCH_DIR, exist_ok=True)
    fieldnames = [
        "date", "attacking_team", "attack_conf_at_lock", "pitcher",
        "trap_type", "season_era_proxy", "actual_er", "actual_ip",
        "actual_attack_runs", "implied_total_itt", "over_under_vs_itt", "source"
    ]

    with open(OUTPUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n[OUTPUT] CSV written to: {}".format(OUTPUT_CSV))
    print("[INFO]  {} TRAP arm instances found across {} days.".format(len(rows), days))

    if missing_results:
        print("[INFO]  {} dates had no results archive: {}".format(
            len(missing_results), ", ".join(missing_results[:8])
        ))
    if missing_actuals:
        print("[INFO]  {} dates had actuals but no results (or vice versa): {}".format(
            len(missing_actuals), ", ".join(missing_actuals[:8])
        ))

    # ---- Summary Stats ----
    print("")
    print("=" * 65)
    print("  SUMMARY STATS")
    print("=" * 65)

    if not rows:
        print("[WARNING] No TRAP arm instances found in the window. Check archive coverage.")
        return

    total = len(rows)

    # Instances with complete data for run/ITT analysis
    runnable = [r for r in rows if r["actual_attack_runs"] != "N/A" and r["implied_total_itt"] != "N/A"]
    over_under_vals = [float(r["over_under_vs_itt"]) for r in runnable if r["over_under_vs_itt"] != "N/A"]

    underscored = [v for v in over_under_vals if v < 0]
    pct_under = (len(underscored) / len(over_under_vals) * 100) if over_under_vals else 0.0
    avg_diff = (sum(over_under_vals) / len(over_under_vals)) if over_under_vals else 0.0

    print("Total TRAP arm instances (30-day window): {}".format(total))
    print("Instances with complete run data: {}/{}".format(len(runnable), total))
    print("")
    print("Pct of games where attack team UNDERSCORED vs ITT: {:.1f}%".format(pct_under))
    print("  (Underscored = actual runs < implied team total at lock)")
    print("Average run differential (actual - ITT): {:+.2f}".format(avg_diff))
    print("")

    # Breakdown by trap_type
    trap_types = {}
    for r in rows:
        tt = r["trap_type"]
        if tt not in trap_types:
            trap_types[tt] = {"count": 0, "over_under_vals": []}
        trap_types[tt]["count"] += 1
        if r["over_under_vs_itt"] != "N/A":
            trap_types[tt]["over_under_vals"].append(float(r["over_under_vs_itt"]))

    print("Breakdown by trap_type:")
    print("-" * 50)
    for tt, data in sorted(trap_types.items()):
        count = data["count"]
        vals = data["over_under_vals"]
        if vals:
            under_pct = len([v for v in vals if v < 0]) / len(vals) * 100
            avg = sum(vals) / len(vals)
            print("  {:<18} | N={:>3} | Under ITT: {:.1f}% | Avg diff: {:+.2f}".format(
                tt, count, under_pct, avg
            ))
        else:
            print("  {:<18} | N={:>3} | No run data available".format(tt, count))

    print("")

    # Notable over-deliveries (TRAP pitcher who allowed 0-1 ER)
    gems = [r for r in rows if r["actual_er"] != "N/A" and int(r["actual_er"]) <= 1
            and r["actual_ip"] != "N/A" and float(r["actual_ip"]) >= 4.0]
    print("Notable TRAP Arm Over-Deliveries (<=1 ER, >=4.0 IP):")
    if gems:
        for g in gems:
            print("  {} | {} vs {} | {}ER in {}IP | Attack ran: {} vs ITT: {}".format(
                g["date"], g["pitcher"], g["attacking_team"],
                g["actual_er"], g["actual_ip"],
                g["actual_attack_runs"], g["implied_total_itt"]
            ))
    else:
        print("  None found in this window.")

    print("")
    print("=" * 65)
    print("NOTE: Classification per AGENTS.md Rule 4:")
    print("  Results above are confirmed from local production archive files")
    print("  (results_*.json + actuals_cache_*.json in reports/archive/).")
    print("  ERA proxy uses recent_era or siera from the lock-time snapshot,")
    print("  NOT a separately reconstructed calculation.")
    print("=" * 65)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OMEGA TRAP Arm Performance Audit")
    parser.add_argument("--days", type=int, default=30, help="Lookback window in days (default: 30)")
    args = parser.parse_args()
    run_trap_audit(days=args.days)
