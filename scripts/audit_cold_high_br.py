"""
OMEGA COLD_HIGH_BR_WARNING Reconciliation Script
Task 2 — July 2026 Pre-Audit

Pulls all COLD_HIGH_BR_WARNING instances from the production archive
(results_{date}.json + actuals_cache_{date}.json) over the last 45 days.

The flag fires when is_cold_high_br_warning=True on a hitter object.
For older archive files that lack this pre-computed field, it is
re-derived from: is_cold_streak_msmi=True AND blended_rating >= 80.

Calculates:
 - True underperformance rate vs salary-bucket/batting-order baseline
 - Average DK pts differential (actual - baseline)
 - Breakdown by batting order tier (1-4 vs 5-6 vs 7+)
 - Breakdown by team game environment (team scored 5+ vs <5 runs)

Output: console summary with verified figures.

Data source: LOCAL ARCHIVE FILES.
Classification per AGENTS.md Rule 4: Results are confirmed from production
archive data only if the script executes successfully against real files.
"""

import os
import sys
import json
from datetime import date, timedelta
from collections import defaultdict

# Ensure project root is on path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARCHIVE_DIR = os.path.join(BASE_DIR, "reports", "archive")
SCRATCH_DIR = os.path.join(BASE_DIR, "scratch")


def calculate_dk_score(hitter_stats):
    """
    DraftKings MLB Classic scoring formula.
    Uses the production function definition from utils/audit_engine.py.
    """
    return float(
        (hitter_stats.get("singles", 0) or 0) * 3 +
        (hitter_stats.get("doubles", 0) or 0) * 5 +
        (hitter_stats.get("triples", 0) or 0) * 8 +
        (hitter_stats.get("hr", 0) or 0) * 10 +
        (hitter_stats.get("rbi", 0) or 0) * 2 +
        (hitter_stats.get("runs_scored", 0) or 0) * 2 +
        (hitter_stats.get("walks", 0) or 0) * 2 +
        (hitter_stats.get("stolen_bases", 0) or 0) * 5 +
        (hitter_stats.get("hbp", 0) or 0) * 2
    )


def normalize_name(name):
    """Lowercase, strip punctuation, normalize for matching."""
    if not name:
        return ""
    s = str(name).lower().strip()
    s = s.replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(s.split())


def ip_str_to_float(ip_str):
    """Convert '5.2' -> 5.667"""
    try:
        parts = str(ip_str).split(".")
        return int(parts[0]) + (int(parts[1]) if len(parts) > 1 else 0) / 3.0
    except Exception:
        return 0.0


def find_actuals(date_str):
    archive_path = os.path.join(ARCHIVE_DIR, f"actuals_cache_{date_str}.json")
    if os.path.exists(archive_path):
        try:
            with open(archive_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    scratch_path = os.path.join(SCRATCH_DIR, "actuals_cache.json")
    if os.path.exists(scratch_path):
        try:
            with open(scratch_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
                return cache.get(date_str)
        except Exception:
            pass
    return None


def find_results(date_str):
    for suffix in ["_lock", ""]:
        path = os.path.join(ARCHIVE_DIR, f"results_{date_str}{suffix}.json")
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return None


def score_tier(player_score):
    """
    Bucket hitters into comparable tiers by player_score proxy
    (salary is not stored in archive JSON, player_score is the closest
    available metric correlated with salary).
    Tiers: high (>=70), mid (50-69), low (<50)
    """
    score = float(player_score or 0)
    if score >= 70:
        return "high"
    elif score >= 50:
        return "mid"
    return "low"


def bo_tier(batting_order):
    """Batting order tier."""
    bo = batting_order
    if bo is None:
        return "unknown"
    try:
        bo = int(bo)
    except Exception:
        return "unknown"
    if bo <= 4:
        return "1-4"
    elif bo <= 6:
        return "5-6"
    else:
        return "7+"


def run_cold_high_br_audit(days=45):
    print("")
    print("=" * 65)
    print("  OMEGA COLD_HIGH_BR_WARNING RECONCILIATION AUDIT")
    print("  Window: Last {} Days".format(days))
    print("=" * 65)

    today = date.today()

    flagged_instances = []   # All COLD_HIGH_BR_WARNING fired instances
    all_hitters_by_date = defaultdict(list)  # date -> list of (player_score_tier, bo_tier, actual_dk_pts)

    dates_checked = 0
    dates_missing_actuals = []
    dates_missing_results = []

    for i in range(days, -1, -1):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")

        results = find_results(date_str)
        if not results:
            dates_missing_results.append(date_str)
            continue

        actuals = find_actuals(date_str)
        if not actuals:
            dates_missing_actuals.append(date_str)
            continue

        dates_checked += 1
        hitters = results.get("hitters", [])
        teams = results.get("teams", [])

        # Build team -> actual runs lookup
        team_runs = {}
        for team_key, team_data in actuals.items():
            runs = team_data.get("runs")
            if runs is not None:
                team_runs[team_key.lower().strip()] = int(runs)

        # Build hitter -> actuals lookup
        hitter_actuals_map = {}  # norm_name -> dk_pts
        for team_key, team_data in actuals.items():
            hitter_rows = team_data.get("hitters", {})
            for hname, hstats in hitter_rows.items():
                norm = normalize_name(hname)
                dk_pts = calculate_dk_score(hstats)
                hitter_actuals_map[norm] = dk_pts

        # For this date, collect ALL hitters with actual DK pts
        # for building the baseline. Exclude flagged hitters from baseline pool.
        flagged_names_this_date = set()
        flagged_hitters_this_date = []

        # First pass: identify flagged hitters
        for h in hitters:
            is_flagged = h.get("is_cold_high_br_warning", False)

            # Fallback: re-derive from components if field missing (older archive files)
            if not is_flagged:
                is_cold = bool(h.get("is_cold_streak_msmi", False))
                br = float(h.get("blended_rating", 0) or 0)
                is_flagged = is_cold and br >= 80

            if is_flagged:
                norm = normalize_name(h.get("name", ""))
                flagged_names_this_date.add(norm)
                flagged_hitters_this_date.append(h)

        # Second pass: collect all non-flagged hitter actuals for baseline
        non_flagged_pool = []  # list of {score_tier, bo_tier_val, dk_pts}
        for h in hitters:
            norm = normalize_name(h.get("name", ""))
            if norm in flagged_names_this_date:
                continue
            actual_dk = hitter_actuals_map.get(norm)
            if actual_dk is None:
                continue
            ps_tier = score_tier(h.get("player_score"))
            bo_t = bo_tier(h.get("batting_order"))
            non_flagged_pool.append({
                "score_tier": ps_tier,
                "bo_tier": bo_t,
                "dk_pts": actual_dk
            })

        # Build baseline lookup: (score_tier, bo_tier) -> avg dk_pts of non-flagged
        baseline_map = defaultdict(list)
        for nf in non_flagged_pool:
            key = (nf["score_tier"], nf["bo_tier"])
            baseline_map[key].append(nf["dk_pts"])

        # Also build broader fallbacks: score_tier only, then global
        score_tier_only = defaultdict(list)
        for nf in non_flagged_pool:
            score_tier_only[nf["score_tier"]].append(nf["dk_pts"])
        global_avg = (sum(x["dk_pts"] for x in non_flagged_pool) / len(non_flagged_pool)
                      if non_flagged_pool else None)

        # Process flagged hitters
        for h in flagged_hitters_this_date:
            name = h.get("name", "Unknown")
            team = h.get("team", "Unknown")
            norm = normalize_name(name)
            bo_raw = h.get("batting_order")
            bo_t = bo_tier(bo_raw)
            ps_tier = score_tier(h.get("player_score"))
            br = float(h.get("blended_rating", 0) or 0)
            player_score = float(h.get("player_score", 0) or 0)

            # Actual DK pts
            actual_dk = hitter_actuals_map.get(norm)
            if actual_dk is None:
                # Skip if we can't find the actual
                continue

            # Baseline: (score_tier, bo_tier) -> score_tier only -> global
            key = (ps_tier, bo_t)
            if len(baseline_map[key]) >= 3:
                baseline = sum(baseline_map[key]) / len(baseline_map[key])
                baseline_source = "matched ({} comps)".format(len(baseline_map[key]))
            elif len(score_tier_only[ps_tier]) >= 3:
                baseline = sum(score_tier_only[ps_tier]) / len(score_tier_only[ps_tier])
                baseline_source = "score-tier fallback ({} comps)".format(len(score_tier_only[ps_tier]))
            elif global_avg is not None:
                baseline = global_avg
                baseline_source = "global fallback"
            else:
                continue  # skip if no baseline possible

            diff = actual_dk - baseline

            # Team runs (did team score 5+ ?)
            team_actual_runs = team_runs.get(team.lower().strip())
            team_high_env = (team_actual_runs is not None and team_actual_runs >= 5)

            flagged_instances.append({
                "date": date_str,
                "name": name,
                "team": team,
                "batting_order": bo_raw,
                "bo_tier": bo_t,
                "player_score": player_score,
                "score_tier": ps_tier,
                "blended_rating": br,
                "actual_dk_pts": actual_dk,
                "baseline_dk_pts": round(baseline, 2),
                "diff_vs_baseline": round(diff, 2),
                "baseline_source": baseline_source,
                "team_runs": team_actual_runs,
                "team_high_env": team_high_env,
            })

    # ---- Print Summary ----
    print("")
    print("Dates checked (had both results + actuals): {}".format(dates_checked))
    print("Missing results: {}".format(len(dates_missing_results)))
    print("Missing actuals: {}".format(len(dates_missing_actuals)))
    print("")
    print("Total COLD_HIGH_BR_WARNING instances found: {}".format(len(flagged_instances)))
    print("")

    if not flagged_instances:
        print("[WARNING] No flagged instances found. Check data availability.")
        return

    # --- Global stats ---
    diffs = [r["diff_vs_baseline"] for r in flagged_instances]
    underperformers = [d for d in diffs if d < 0]
    under_rate = len(underperformers) / len(diffs) * 100
    avg_diff = sum(diffs) / len(diffs)

    print("=" * 65)
    print("  VERIFIED FIGURES (from production archive data)")
    print("=" * 65)
    print("True underperformance rate (actual DK pts < baseline): {:.1f}%".format(under_rate))
    print("  ({}/{} instances below comparable non-flagged hitter baseline)".format(
        len(underperformers), len(diffs)
    ))
    print("Average DK pts differential (actual - baseline): {:+.2f}".format(avg_diff))
    print("")
    print("  For reference:")
    print("  OMEGA_CONTEXT.md states:   54.8%, -0.58 pts  [PRE-BACKFILL]")
    print("  OMEGA_DECISIONS.md states: 83.9%, -4.03 pts  [POST-BACKFILL]")
    print("")

    # --- Breakdown by batting order tier ---
    print("-" * 65)
    print("Breakdown by Batting Order Tier:")
    print("-" * 65)
    for tier_label in ["1-4", "5-6", "7+", "unknown"]:
        tier_instances = [r for r in flagged_instances if r["bo_tier"] == tier_label]
        if not tier_instances:
            continue
        tier_diffs = [r["diff_vs_baseline"] for r in tier_instances]
        t_under = len([d for d in tier_diffs if d < 0]) / len(tier_diffs) * 100
        t_avg = sum(tier_diffs) / len(tier_diffs)
        print("  BO {:<9} | N={:>3} | Under baseline: {:.1f}% | Avg diff: {:+.2f} DK pts".format(
            tier_label, len(tier_instances), t_under, t_avg
        ))

    print("")

    # --- Breakdown by team game environment ---
    print("-" * 65)
    print("Breakdown by Team Game Environment (James Wood test):")
    print("-" * 65)
    high_env = [r for r in flagged_instances if r["team_high_env"]]
    low_env = [r for r in flagged_instances if not r["team_high_env"] and r["team_runs"] is not None]
    unknown_env = [r for r in flagged_instances if r["team_runs"] is None]

    for label, group in [("Team 5+ runs", high_env), ("Team <5 runs", low_env), ("Team runs unknown", unknown_env)]:
        if not group:
            continue
        g_diffs = [r["diff_vs_baseline"] for r in group]
        g_under = len([d for d in g_diffs if d < 0]) / len(g_diffs) * 100
        g_avg = sum(g_diffs) / len(g_diffs)
        print("  {:<20} | N={:>3} | Under: {:.1f}% | Avg diff: {:+.2f} DK pts".format(
            label, len(group), g_under, g_avg
        ))

    print("")
    if high_env:
        print("  NOTE (Wood Effect): When team scored 5+ runs ({}N), under-rate = {:.1f}%".format(
            len(high_env),
            len([d for d in [r["diff_vs_baseline"] for r in high_env] if d < 0]) / len(high_env) * 100
        ))
        print("  This tests whether COLD_HIGH_BR_WARNING fails specifically in")
        print("  high-scoring game environments (the June 30 James Wood case).")

    # --- Individual instance table (all flagged) ---
    print("")
    print("-" * 65)
    print("All Flagged Instances:")
    print("-" * 65)
    print("  {:<12} {:<22} {:<5} {:<5} {:>7} {:>7} {:>7} {:<8}".format(
        "Date", "Player", "Team", "BO", "DK Pts", "Base", "Diff", "TeamRuns"
    ))
    print("  " + "-" * 63)
    for r in sorted(flagged_instances, key=lambda x: x["date"]):
        team_abbrev = r["team"].split()[-1][:5] if r["team"] else "N/A"
        print("  {:<12} {:<22} {:<5} {:<5} {:>7.2f} {:>7.2f} {:>+7.2f} {:<8}".format(
            r["date"],
            r["name"][:22],
            team_abbrev[:5],
            str(r["batting_order"] or "?"),
            r["actual_dk_pts"],
            r["baseline_dk_pts"],
            r["diff_vs_baseline"],
            str(r["team_runs"]) + "R" if r["team_runs"] is not None else "N/A"
        ))

    print("")
    print("=" * 65)
    print("NOTE: Classification per AGENTS.md Rule 4:")
    print("  These figures are confirmed from local production archive files.")
    print("  Baseline = avg DK pts of non-flagged hitters in same player_score")
    print("  tier (high/mid/low) and batting order tier on the same slate.")
    print("  Salary not stored in archive JSON; player_score used as proxy.")
    print("  is_cold_high_br_warning re-derived for older files lacking the field.")
    print("=" * 65)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OMEGA COLD_HIGH_BR_WARNING Reconciliation Audit")
    parser.add_argument("--days", type=int, default=45, help="Lookback window in days (default: 45)")
    args = parser.parse_args()
    run_cold_high_br_audit(days=args.days)
