"""
OMEGA COLD_HIGH_BR_WARNING Reconciliation Script
Task 2 — July 2026 Pre-Audit

Pulls all COLD_HIGH_BR_WARNING instances from the production archive
(results_{date}.json + actuals_cache_{date}.json) over the last 45 days.

The field is_cold_high_br_warning is read DIRECTLY from each hitter object
as stored in the production archive. No fallback recalculation from
is_cold_streak_msmi or rolling deltas is used. Archive files where the
field is absent (pre-June 28, 2026 implementation) are skipped entirely
and reported as a data gap.

Calculates (on available post-implementation data):
 - True underperformance rate vs player-score-tier/batting-order baseline
 - Average DK pts differential (actual - baseline)
 - Breakdown by batting order tier (1-4 vs 5-6 vs 7+)
 - Breakdown by team game environment (team scored 5+ vs <5 runs)

Output: console summary with verified figures.

Data source: LOCAL ARCHIVE FILES.
Classification per AGENTS.md Rule 4: Results are confirmed from production
archive data only if the script executes successfully against real files.
The field is_cold_high_br_warning is read directly from each hitter object
as stored in the production archive — no standalone recalculation is used.
"""

import os
import sys
import json
from datetime import date, timedelta
from collections import defaultdict

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARCHIVE_DIR = os.path.join(BASE_DIR, "reports", "archive")
SCRATCH_DIR = os.path.join(BASE_DIR, "scratch")


def calculate_dk_score(hitter_stats):
    """DraftKings MLB Classic scoring — matches utils/audit_engine.py."""
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
    if not name:
        return ""
    s = str(name).lower().strip()
    s = s.replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(s.split())


def find_actuals(date_str):
    archive_path = os.path.join(ARCHIVE_DIR, "actuals_cache_{}.json".format(date_str))
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
        path = os.path.join(ARCHIVE_DIR, "results_{}{}.json".format(date_str, suffix))
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
    return None


def score_tier(player_score):
    """Proxy salary tier from player_score (salary not stored in archive JSON)."""
    score = float(player_score or 0)
    if score >= 70:
        return "high"
    elif score >= 50:
        return "mid"
    return "low"


def bo_tier(batting_order):
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
    return "7+"


def run_cold_high_br_audit(days=45):
    print("")
    print("=" * 65)
    print("  OMEGA COLD_HIGH_BR_WARNING RECONCILIATION AUDIT")
    print("  Window: Last {} Days".format(days))
    print("=" * 65)

    today = date.today()

    flagged_instances = []

    dates_with_field = []    # results files where field was present
    dates_field_absent = []  # results files where field was absent (pre-implementation)
    dates_missing_results = []
    dates_missing_actuals = []

    for i in range(days, -1, -1):
        target_date = today - timedelta(days=i)
        date_str = target_date.strftime("%Y-%m-%d")

        # June 30: actuals not yet cached — documented data gap, skip
        if date_str == "2026-06-30":
            continue

        results = find_results(date_str)
        if not results:
            dates_missing_results.append(date_str)
            continue

        actuals = find_actuals(date_str)
        if not actuals:
            dates_missing_actuals.append(date_str)
            continue

        hitters = results.get("hitters", [])

        # Gate: check whether is_cold_high_br_warning exists in this file.
        # Field was implemented June 28, 2026. Pre-implementation files lack it.
        # Do NOT use fallback recalculation — skip the entire date.
        field_present = any("is_cold_high_br_warning" in h for h in hitters)
        if not field_present:
            dates_field_absent.append(date_str)
            continue

        dates_with_field.append(date_str)

        # Build team -> actual runs lookup
        team_runs = {}
        for team_key, team_data in actuals.items():
            runs = team_data.get("runs")
            if runs is not None:
                team_runs[team_key.lower().strip()] = int(runs)

        # Build hitter -> actual DK pts lookup
        hitter_actuals_map = {}
        for team_key, team_data in actuals.items():
            for hname, hstats in team_data.get("hitters", {}).items():
                norm = normalize_name(hname)
                hitter_actuals_map[norm] = calculate_dk_score(hstats)

        # Identify flagged hitters — DIRECT FIELD READ ONLY, no fallback
        flagged_norms = set()
        flagged_hitters_this_date = []
        for h in hitters:
            if bool(h.get("is_cold_high_br_warning", False)):
                norm = normalize_name(h.get("name", ""))
                flagged_norms.add(norm)
                flagged_hitters_this_date.append(h)

        # Collect non-flagged hitters for baseline
        non_flagged_pool = []
        for h in hitters:
            norm = normalize_name(h.get("name", ""))
            if norm in flagged_norms:
                continue
            actual_dk = hitter_actuals_map.get(norm)
            if actual_dk is None:
                continue
            non_flagged_pool.append({
                "score_tier": score_tier(h.get("player_score")),
                "bo_tier": bo_tier(h.get("batting_order")),
                "dk_pts": actual_dk
            })

        # Build baseline lookups
        baseline_map = defaultdict(list)
        score_tier_map = defaultdict(list)
        for nf in non_flagged_pool:
            baseline_map[(nf["score_tier"], nf["bo_tier"])].append(nf["dk_pts"])
            score_tier_map[nf["score_tier"]].append(nf["dk_pts"])
        global_avg = (sum(x["dk_pts"] for x in non_flagged_pool) / len(non_flagged_pool)
                      if non_flagged_pool else None)

        for h in flagged_hitters_this_date:
            name = h.get("name", "Unknown")
            norm = normalize_name(name)
            team = h.get("team", "Unknown")
            bo_raw = h.get("batting_order")
            bo_t = bo_tier(bo_raw)
            ps_tier = score_tier(h.get("player_score"))
            br = float(h.get("blended_rating", 0) or 0)

            actual_dk = hitter_actuals_map.get(norm)
            if actual_dk is None:
                continue

            key = (ps_tier, bo_t)
            if len(baseline_map[key]) >= 3:
                baseline = sum(baseline_map[key]) / len(baseline_map[key])
                baseline_source = "matched ({} comps)".format(len(baseline_map[key]))
            elif len(score_tier_map[ps_tier]) >= 3:
                baseline = sum(score_tier_map[ps_tier]) / len(score_tier_map[ps_tier])
                baseline_source = "score-tier fallback ({} comps)".format(len(score_tier_map[ps_tier]))
            elif global_avg is not None:
                baseline = global_avg
                baseline_source = "global fallback"
            else:
                continue

            team_actual_runs = team_runs.get(team.lower().strip())
            flagged_instances.append({
                "date": date_str,
                "name": name,
                "team": team,
                "batting_order": bo_raw,
                "bo_tier": bo_t,
                "score_tier": ps_tier,
                "blended_rating": br,
                "actual_dk_pts": actual_dk,
                "baseline_dk_pts": round(baseline, 2),
                "diff_vs_baseline": round(actual_dk - baseline, 2),
                "baseline_source": baseline_source,
                "team_runs": team_actual_runs,
                "team_high_env": (team_actual_runs is not None and team_actual_runs >= 5),
            })

    # ---- Data gap report ----
    print("")
    print("DATA AVAILABILITY REPORT")
    print("-" * 65)
    print("Dates in window (excl. June 30 actuals gap): {}".format(days))
    print("Dates with results + actuals + field PRESENT: {} -- {}".format(
        len(dates_with_field),
        ", ".join(dates_with_field) if dates_with_field else "none"
    ))
    print("Dates skipped -- field ABSENT (pre-June 28):  {}".format(len(dates_field_absent)))
    print("Dates skipped -- missing results archive:     {}".format(len(dates_missing_results)))
    print("Dates skipped -- missing actuals cache:       {}".format(len(dates_missing_actuals)))
    print("June 30: excluded -- actuals cache not yet populated (documented gap)")
    print("")
    print("  Note: is_cold_high_br_warning implemented June 28, 2026.")
    print("  All archive files generated before that date lack the field.")
    print("  No fallback recalculation used -- those dates are excluded.")
    print("")

    n = len(flagged_instances)
    print("Total flagged instances found (direct field read only): {}".format(n))
    print("")

    # ---- Insufficient data path ----
    if n < 15:
        print("=" * 65)
        print("  RESULT: INSUFFICIENT POST-IMPLEMENTATION SAMPLE")
        print("=" * 65)
        print("")
        print("N={} instance(s) confirmed from direct is_cold_high_br_warning".format(n))
        print("reads. Minimum 15 instances required for a meaningful rate.")
        print("(Statistical confidence requires ~30+ for signal validation.)")
        print("")
        if flagged_instances:
            print("Instance(s) found:")
            for r in flagged_instances:
                print("  {} | {} ({}) | BO {} | DK pts: {:.1f} | Baseline: {:.1f} | Diff: {:+.1f} | Team: {}R".format(
                    r["date"], r["name"], r["team"],
                    r["batting_order"] or "?",
                    r["actual_dk_pts"], r["baseline_dk_pts"], r["diff_vs_baseline"],
                    r["team_runs"] if r["team_runs"] is not None else "N/A"
                ))
            print("")
        print("RECONCILIATION FINDING:")
        print("")
        print("  OMEGA_CONTEXT.md  states: 54.8% underperformance, -0.58 DFS delta")
        print("  OMEGA_DECISIONS.md states: 83.9% underperformance, -4.03 DFS delta")
        print("")
        print("  Both figures were calculated via the June 28 backtest script which")
        print("  ran against 53 historical slates. Those slates predate the field")
        print("  implementation, so the backtest script must have re-derived the flag")
        print("  from is_cold_streak_msmi + blended_rating >= 80 on hitter objects.")
        print("  That is a logic-level check, not a read of the stored flag.")
        print("")
        print("  This audit script cannot confirm or refute either doc figure from")
        print("  the direct field -- the data simply does not exist yet.")
        print("")
        print("  DO NOT UPDATE OMEGA_CONTEXT.md OR OMEGA_DECISIONS.md based on")
        print("  this run. Schedule re-run when 20-30 post-June-28 slates have")
        print("  accumulated (estimated: mid-July 2026).")
        print("")
        print("=" * 65)
        print("NOTE: Classification per AGENTS.md Rule 4:")
        print("  The finding of insufficient data IS confirmed from production")
        print("  archive files. The conclusion is not a logic-level check.")
        print("  The doc figures (83.9% / 54.8%) remain at logic-level status")
        print("  until a direct-field audit with N>=15 is completed.")
        print("=" * 65)
        return

    # ---- Full stats (future run when N >= 15) ----
    diffs = [r["diff_vs_baseline"] for r in flagged_instances]
    underperformers = [d for d in diffs if d < 0]
    under_rate = len(underperformers) / len(diffs) * 100
    avg_diff = sum(diffs) / len(diffs)

    print("=" * 65)
    print("  VERIFIED FIGURES (direct is_cold_high_br_warning field reads)")
    print("=" * 65)
    print("Under-baseline rate: {:.1f}% ({}/{})".format(under_rate, len(underperformers), n))
    print("Avg DK pts diff (actual - baseline): {:+.2f}".format(avg_diff))
    print("")
    print("  OMEGA_CONTEXT.md:   54.8%, -0.58 pts [logic-level, pre-backfill]")
    print("  OMEGA_DECISIONS.md: 83.9%, -4.03 pts [logic-level, post-backfill]")
    print("")

    # BO tier breakdown
    print("-" * 65)
    print("Breakdown by Batting Order Tier:")
    for tier_label in ["1-4", "5-6", "7+", "unknown"]:
        grp = [r for r in flagged_instances if r["bo_tier"] == tier_label]
        if not grp:
            continue
        g_diffs = [r["diff_vs_baseline"] for r in grp]
        print("  BO {:<9} | N={:>3} | Under: {:.1f}% | Avg diff: {:+.2f}".format(
            tier_label, len(grp),
            len([d for d in g_diffs if d < 0]) / len(g_diffs) * 100,
            sum(g_diffs) / len(g_diffs)
        ))

    print("")
    print("-" * 65)
    print("Breakdown by Team Game Environment:")
    for label, grp in [
        ("Team 5+ runs", [r for r in flagged_instances if r["team_high_env"]]),
        ("Team <5 runs", [r for r in flagged_instances if not r["team_high_env"] and r["team_runs"] is not None]),
    ]:
        if not grp:
            continue
        g_diffs = [r["diff_vs_baseline"] for r in grp]
        print("  {:<20} | N={:>3} | Under: {:.1f}% | Avg diff: {:+.2f}".format(
            label, len(grp),
            len([d for d in g_diffs if d < 0]) / len(g_diffs) * 100,
            sum(g_diffs) / len(g_diffs)
        ))

    print("")
    print("-" * 65)
    print("All Instances:")
    print("  {:<12} {:<22} {:<5} {:<5} {:>7} {:>7} {:>7} {:<8}".format(
        "Date", "Player", "Team", "BO", "DK Pts", "Base", "Diff", "TeamRuns"
    ))
    print("  " + "-" * 63)
    for r in sorted(flagged_instances, key=lambda x: x["date"]):
        team_abbrev = r["team"].split()[-1][:5] if r["team"] else "N/A"
        print("  {:<12} {:<22} {:<5} {:<5} {:>7.2f} {:>7.2f} {:>+7.2f} {:<8}".format(
            r["date"], r["name"][:22], team_abbrev[:5],
            str(r["batting_order"] or "?"),
            r["actual_dk_pts"], r["baseline_dk_pts"], r["diff_vs_baseline"],
            str(r["team_runs"]) + "R" if r["team_runs"] is not None else "N/A"
        ))

    print("")
    print("=" * 65)
    print("NOTE: Classification per AGENTS.md Rule 4:")
    print("  Confirmed from production archive files. Direct field reads only.")
    print("=" * 65)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="OMEGA COLD_HIGH_BR_WARNING Reconciliation Audit")
    parser.add_argument("--days", type=int, default=45, help="Lookback window in days (default: 45)")
    args = parser.parse_args()
    run_cold_high_br_audit(days=args.days)
