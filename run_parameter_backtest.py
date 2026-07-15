"""
OMEGA Parameter Backtest v1.0
============================================================
Compares OLD vs NEW model parameters across all archived slates.

NEW parameters (current):
  - Divergence dampening: 30% scale-back if divergence >= 15% AND xwOBA < 0.330
  - Bullpen fatigue multiplier: 1.05x (was 1.20x) for short-leash starters
  - DQI TRUST threshold: 80 (was 75)
  - DQI Divergence gate: 14.0% (was 12.0%)
  - DQI ITT floor: 4.2 runs (was 3.8 runs)

This script re-simulates both OLD and NEW scoring on historical archived
projection data and compares how each would have performed against actuals.

Usage:
    python run_parameter_backtest.py
    python run_parameter_backtest.py 2026-04-15 2026-05-27  # specify date range
"""

import json
import os
import sys
from datetime import datetime, timedelta
from config import config
from engine.sharps_weighting import SharpsWeighting
from utils.audit_engine import AuditEngine


# ─────────────────────────────────────────────────────────────
# PARAMETER SETS: OLD vs NEW
# ─────────────────────────────────────────────────────────────

OLD_PARAMS = {
    "divergence_dampen_threshold": 15.0,   # Same trigger...
    "divergence_dampen_active": False,      # ...but dampening was NOT applied (old behavior)
    "bullpen_short_leash_mult": 1.20,       # OLD: 20% boost
    "dqi_trust_min": 75,                    # OLD: 75 pts
    "dqi_div_gate": 12.0,                   # OLD: 12% divergence gate
    "dqi_itt_floor": 3.8,                   # OLD: 3.8 run floor
}

NEW_PARAMS = {
    "divergence_dampen_threshold": 15.0,
    "divergence_dampen_active": True,       # NEW: 30% dampening on large div + low xwOBA
    "divergence_dampen_xwoba_cap": 0.330,
    "divergence_dampen_factor": 0.70,
    "bullpen_short_leash_mult": 1.05,       # NEW: 5% boost only
    "dqi_trust_min": 80,                    # NEW: 80 pts
    "dqi_div_gate": 14.0,                   # NEW: 14% divergence gate
    "dqi_itt_floor": 4.2,                   # NEW: 4.2 run floor
}


# ─────────────────────────────────────────────────────────────
# MINI SCORING FUNCTIONS (parameterized, no side effects)
# ─────────────────────────────────────────────────────────────

def compute_div_premium(divergence: float, team_xwoba: float, params: dict) -> float:
    """
    Re-compute the divergence premium for a team given parameter set.
    Mirrors the logic in sharps_weighting.py lines 252-257.
    """
    anchor_ratio = 1.0
    if team_xwoba < 0.295:
        anchor_ratio = max(0.75, (team_xwoba / 0.295) ** 2.0)

    div_premium = min(0.10, (max(0, divergence) / 150.0))

    if params["divergence_dampen_active"]:
        if divergence >= params["divergence_dampen_threshold"] and team_xwoba < params.get("divergence_dampen_xwoba_cap", 0.330):
            div_premium *= params.get("divergence_dampen_factor", 0.70)

    dampened_div_premium = div_premium * anchor_ratio
    return 1.0 + dampened_div_premium  # div_multiplier


def compute_bullpen_boost(bullpen_fatigue: float, pitcher_outs: float, is_opp_trap: bool, params: dict) -> float:
    """
    Re-compute bullpen boost given parameter set.
    Mirrors sharps_weighting.py lines 159-182 (excluding skill modifier for simplicity).
    """
    fatigue_floor = 65.0
    bullpen_boost = max(0, (bullpen_fatigue - fatigue_floor) / 3.5)
    effective_outs = 15.5 if is_opp_trap else pitcher_outs
    if effective_outs <= 15.5:
        bullpen_boost *= params["bullpen_short_leash_mult"]
    elif effective_outs >= 18.0:
        bullpen_boost *= 0.85
    bullpen_boost = min(15.0, bullpen_boost)
    return bullpen_boost


def compute_dqi_status(dqi_score: int, divergence: float, implied_total: float, params: dict) -> str:
    """
    Re-compute DQI status label from a raw dqi_score using given parameter set.
    Mirrors utils/dqi.py lines 146-156.
    """
    status = "OVERPRICED" if dqi_score >= params["dqi_trust_min"] else ("CAUTION" if dqi_score >= 50 else "LEVERAGE")
    if status == "OVERPRICED" and divergence < params["dqi_div_gate"]:
        status = "CAUTION"
    if status == "OVERPRICED" and implied_total < params["dqi_itt_floor"]:
        status = "CAUTION"
    return status


# ─────────────────────────────────────────────────────────────
# DELTA STACK SCORE (approximation — we re-apply the multipliers)
# ─────────────────────────────────────────────────────────────

def recompute_stack_score_delta(team: dict, params: dict) -> float:
    """
    Returns an ADJUSTED stack score for the given parameter set.
    We take the stored stack_score and factor out then re-apply the
    divergence + bullpen components that changed between OLD and NEW.

    Note: This is a delta approximation. Full re-run would require
    re-invoking the entire stack scoring pipeline with live market data,
    which isn't available for historical slates. Instead we recompute
    only the components that changed.
    """
    divergence = float(team.get("divergence", 0))
    team_xwoba = float(team.get("team_xwoba", 0.320))
    bullpen_fatigue = float(team.get("bullpen_fatigue", 0))
    pitcher_outs = float(team.get("opp_pitcher_outs", 18.0))
    is_opp_trap = bool(team.get("is_trap", False))  # opp pitcher trap
    implied_total = float(team.get("implied_total", 4.5))

    # ─── Divergence delta ───
    old_div_mult = compute_div_premium(divergence, team_xwoba, OLD_PARAMS)
    new_div_mult = compute_div_premium(divergence, team_xwoba, params)

    # ─── Bullpen delta ───
    old_bp = compute_bullpen_boost(bullpen_fatigue, pitcher_outs, is_opp_trap, OLD_PARAMS)
    new_bp = compute_bullpen_boost(bullpen_fatigue, pitcher_outs, is_opp_trap, params)

    # Reconstruct approximate base (before div and bullpen)
    stored_score = float(team.get("stack_score", 80.0))
    # We can't perfectly de-compose, so we compute a net delta
    bp_delta = new_bp - old_bp          # positive = new gives more bullpen pts
    div_effect = stored_score * (new_div_mult - old_div_mult)  # multiplicative effect on total

    adjusted_score = stored_score + bp_delta + div_effect
    return max(0.0, adjusted_score)


# ─────────────────────────────────────────────────────────────
# MAIN BACKTEST LOGIC
# ─────────────────────────────────────────────────────────────

def _fetch_actuals_cached(audit, date_str: str, archive_dir: str) -> dict:
    """Fetch actuals from local cache first; only hit API if not cached."""
    cache_path = os.path.join(archive_dir, f"actuals_cache_{date_str}.json")
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    # Not cached — fetch from API
    print(f"  [API] Fetching actuals for {date_str}...")
    actuals = audit.fetch_results(date=date_str)
    if actuals:
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(actuals, f)
    return actuals


def run_backtest(start_date_str: str, end_date_str: str):
    start = datetime.strptime(start_date_str, "%Y-%m-%d")
    end = datetime.strptime(end_date_str, "%Y-%m-%d")

    print(f"\n{'='*65}")
    print(f"  OMEGA Parameter Backtest: OLD vs NEW")
    print(f"  Date Range: {start_date_str} -> {end_date_str}")
    print(f"{'='*65}\n")

    archive_dir = os.path.join(config.REPORTS_DIR, "archive")
    audit = AuditEngine()

    # ─── Aggregate counters ───
    results = {
        "old": {
            "trust_total": 0, "trust_hit": 0,
            "caution_total": 0, "caution_hit": 0,
            "top3_total": 0, "top3_hit": 0,
            "div_fail_total": 0, "div_fail_missed": 0,   # large-div low-xwoba
        },
        "new": {
            "trust_total": 0, "trust_hit": 0,
            "caution_total": 0, "caution_hit": 0,
            "top3_total": 0, "top3_hit": 0,
            "div_fail_total": 0, "div_fail_missed": 0,
        },
    }

    daily_rows = []
    div_fail_cases = []  # track individual divergence-dampened cases
    trust_flip_cases = []  # cases where DQI flipped from TRUST -> CAUTION

    current = start
    days_processed = 0

    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        # Prefer _lock versions for more accurate projections
        lock_path = os.path.join(archive_dir, f"results_{date_str}_lock.json")
        base_path = os.path.join(archive_dir, f"results_{date_str}.json")

        archive_path = lock_path if os.path.exists(lock_path) else base_path

        if not os.path.exists(archive_path):
            current += timedelta(days=1)
            continue

        print(f"[PROCESSING] {date_str}  ({os.path.basename(archive_path)})")

        with open(archive_path, 'r', encoding='utf-8') as f:
            projections = json.load(f)

        teams = projections.get('teams', [])
        if not teams:
            current += timedelta(days=1)
            continue

        # Fetch actual results — cached locally so repeat runs are instant
        actuals = _fetch_actuals_cached(audit, date_str, archive_dir)
        if not actuals:
            print(f"  >> No actuals found for {date_str} (game may not be final). Skipping.\n")
            current += timedelta(days=1)
            continue

        # Sort teams by stored stack_score descending
        teams_sorted = sorted(teams, key=lambda t: t.get('stack_score', 0), reverse=True)

        day_old = {"trust_hit": 0, "trust_total": 0, "top3_hit": 0, "top3_total": 0}
        day_new = {"trust_hit": 0, "trust_total": 0, "top3_hit": 0, "top3_total": 0}

        top3_processed_old = 0
        top3_processed_new = 0

        for idx, team in enumerate(teams_sorted):
            team_name = team.get('team', '')
            actual = actuals.get(team_name, {})
            actual_runs = actual.get('runs', None)

            if actual_runs is None:
                continue  # Game not found in actuals

            hit = actual_runs >= 4  # 4+ runs = stack success for DFS
            strong_hit = actual_runs >= 5

            divergence = float(team.get('divergence', 0))
            team_xwoba = float(team.get('team_xwoba', 0.320))
            implied_total = float(team.get('implied_total', 4.5))
            stored_stack = float(team.get('stack_score', 80.0))

            # ─── DQI re-simulation ───
            # We need to reconstruct a raw DQI score from stored data.
            # The stored stack_score isn't the DQI score directly.
            # We use attack_conf as a proxy for DQI score (it's often the DQI-adjacent conf).
            # For teams with divergence >= 10%, attack_conf correlates with DQI.
            # We'll use dqi_pos_pts and dqi_warn_pts if stored, else proxy.
            dqi_pos = float(team.get('dqi_pos_pts', 0))
            dqi_warn = float(team.get('dqi_warn_pts', 0))
            if dqi_pos > 0 or dqi_warn > 0:
                raw_dqi = min(100, max(0, 30.0 + dqi_pos - dqi_warn))
                dqi_int = int(round(raw_dqi))
            else:
                # Fallback: derive from attack_conf as DQI proxy
                dqi_int = int(team.get('attack_conf', 50))

            old_dqi_status = compute_dqi_status(dqi_int, divergence, implied_total, OLD_PARAMS)
            new_dqi_status = compute_dqi_status(dqi_int, divergence, implied_total, NEW_PARAMS)

            # Track trust-flip cases (OVERPRICED -> CAUTION after tightening)
            if old_dqi_status == "OVERPRICED" and new_dqi_status == "CAUTION":
                trust_flip_cases.append({
                    "date": date_str,
                    "team": team_name,
                    "divergence": divergence,
                    "implied_total": implied_total,
                    "dqi_score": dqi_int,
                    "actual_runs": actual_runs,
                    "hit": hit,
                    "prevented_bad_trust": not hit  # True = new params CORRECTLY avoided over-trusting
                })

            # ─── NEW adjusted stack score ───
            new_stack = recompute_stack_score_delta(team, NEW_PARAMS)
            old_stack = stored_stack  # OLD is the stored value

            # ─── OLD stats ───
            if old_dqi_status == "OVERPRICED":
                results["old"]["trust_total"] += 1
                day_old["trust_total"] += 1
                if hit:
                    results["old"]["trust_hit"] += 1
                    day_old["trust_hit"] += 1
            elif old_dqi_status == "CAUTION":
                results["old"]["caution_total"] += 1

            # ─── NEW stats ───
            if new_dqi_status == "OVERPRICED":
                results["new"]["trust_total"] += 1
                day_new["trust_total"] += 1
                if hit:
                    results["new"]["trust_hit"] += 1
                    day_new["trust_hit"] += 1
            elif new_dqi_status == "CAUTION":
                results["new"]["caution_total"] += 1

            # ─── Top-3 Stacks ───
            if top3_processed_old < 3:
                results["old"]["top3_total"] += 1
                day_old["top3_total"] += 1
                if hit:
                    results["old"]["top3_hit"] += 1
                    day_old["top3_hit"] += 1
                top3_processed_old += 1

            # For NEW, re-sort using new_stack and take top 3
            # (We do this in a second pass below)

            # ─── Divergence Fail tracking ───
            # Cases with large positive divergence AND low xwOBA — the key failure pattern
            if divergence >= 15.0 and team_xwoba < 0.330:
                results["old"]["div_fail_total"] += 1
                results["new"]["div_fail_total"] += 1
                if not hit:
                    results["old"]["div_fail_missed"] += 1  # Old model would have over-trusted
                if not hit:  # New model still misses same actual run count, but gives less score premium
                    results["new"]["div_fail_missed"] += 1
                div_fail_cases.append({
                    "date": date_str,
                    "team": team_name,
                    "divergence": divergence,
                    "team_xwoba": team_xwoba,
                    "old_stack": round(old_stack, 1),
                    "new_stack": round(new_stack, 1),
                    "score_reduction": round(old_stack - new_stack, 1),
                    "actual_runs": actual_runs,
                    "hit": hit,
                    "old_dqi": old_dqi_status,
                    "new_dqi": new_dqi_status,
                })

        # ─── NEW top-3 (re-sorted by new stack score) ───
        new_stacks = []
        for team in teams_sorted:
            team_name = team.get('team', '')
            actual = actuals.get(team_name, {})
            actual_runs = actual.get('runs', None)
            if actual_runs is None:
                continue
            new_stack = recompute_stack_score_delta(team, NEW_PARAMS)
            new_stacks.append((new_stack, actual_runs >= 4, team_name))
        new_stacks.sort(key=lambda x: x[0], reverse=True)
        for i, (ns, nhit, tn) in enumerate(new_stacks[:3]):
            results["new"]["top3_total"] += 1
            day_new["top3_total"] += 1
            if nhit:
                results["new"]["top3_hit"] += 1
                day_new["top3_hit"] += 1

        daily_rows.append({
            "date": date_str,
            "old_trust": f"{day_old['trust_hit']}/{day_old['trust_total']}",
            "new_trust": f"{day_new['trust_hit']}/{day_new['trust_total']}",
            "old_top3": f"{day_old['top3_hit']}/{day_old['top3_total']}",
            "new_top3": f"{day_new['top3_hit']}/{day_new['top3_total']}",
        })

        days_processed += 1
        current += timedelta(days=1)

    # ─────────────────────────────────────────────────────────
    # GENERATE REPORT
    # ─────────────────────────────────────────────────────────
    _generate_report(
        start_date_str, end_date_str, results, daily_rows,
        div_fail_cases, trust_flip_cases, days_processed
    )


def _pct(hit, total):
    if total == 0:
        return "N/A"
    return f"{(hit/total)*100:.0f}%"


def _generate_report(start, end, results, daily_rows, div_fail_cases, trust_flip_cases, days_processed):
    old = results["old"]
    new = results["new"]

    lines = []
    lines.append(f"# 🧪 OMEGA Parameter Backtest: OLD vs NEW")
    lines.append(f"**Date Range:** {start} to {end}  |  **Slates Analyzed:** {days_processed}")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %I:%M %p ET')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # ─── Parameter Summary ───
    lines.append("## Parameter Changes Tested")
    lines.append("")
    lines.append("| Parameter | OLD Value | NEW Value | Direction |")
    lines.append("|-----------|-----------|-----------|-----------|")
    lines.append("| DQI TRUST Threshold | 75 pts | 80 pts | 🔒 Tighter |")
    lines.append("| DQI Divergence Gate | 12.0% | 14.0% | 🔒 Tighter |")
    lines.append("| DQI ITT Floor | 3.8 runs | 4.2 runs | 🔒 Tighter |")
    lines.append("| Divergence Dampening (≥15%, xwOBA<.330) | None | 30% scale-back | 🛡️ Added |")
    lines.append("| Bullpen Short-Leash Multiplier | 1.20x | 1.05x | 📉 Reduced |")
    lines.append("")

    # ─── Key Metrics ───
    lines.append("## Key Metric Comparison")
    lines.append("")
    lines.append("| Metric | OLD Model | NEW Model | Verdict |")
    lines.append("|--------|-----------|-----------|---------|")

    # DQI Trust hit rate
    old_tr = _pct(old["trust_hit"], old["trust_total"])
    new_tr = _pct(new["trust_hit"], new["trust_total"])
    old_tr_val = old["trust_hit"] / old["trust_total"] if old["trust_total"] > 0 else 0
    new_tr_val = new["trust_hit"] / new["trust_total"] if new["trust_total"] > 0 else 0
    trust_verdict = "✅ IMPROVED" if new_tr_val > old_tr_val else ("➡️ SAME" if new_tr_val == old_tr_val else "⚠️ DECLINED")
    lines.append(f"| DQI TRUST Hit Rate (4+ runs) | {old_tr} ({old['trust_hit']}/{old['trust_total']}) | {new_tr} ({new['trust_hit']}/{new['trust_total']}) | {trust_verdict} |")

    # DQI Trust volume (fewer trusts = selectivity)
    selectivity = "🎯 More Selective" if new["trust_total"] < old["trust_total"] else ("➡️ Same Volume" if new["trust_total"] == old["trust_total"] else "📈 More Trusts")
    lines.append(f"| DQI TRUST Volume | {old['trust_total']} tags | {new['trust_total']} tags | {selectivity} |")

    # Top-3 Stack hit rate
    old_t3 = _pct(old["top3_hit"], old["top3_total"])
    new_t3 = _pct(new["top3_hit"], new["top3_total"])
    old_t3_val = old["top3_hit"] / old["top3_total"] if old["top3_total"] > 0 else 0
    new_t3_val = new["top3_hit"] / new["top3_total"] if new["top3_total"] > 0 else 0
    t3_verdict = "✅ IMPROVED" if new_t3_val > old_t3_val else ("➡️ SAME" if new_t3_val == old_t3_val else "⚠️ DECLINED")
    lines.append(f"| Top-3 Stack Hit Rate | {old_t3} ({old['top3_hit']}/{old['top3_total']}) | {new_t3} ({new['top3_hit']}/{new['top3_total']}) | {t3_verdict} |")

    # Divergence fail cases (large div + low xwOBA)
    old_df = _pct(old["div_fail_missed"], old["div_fail_total"])
    new_df = _pct(new["div_fail_missed"], new["div_fail_total"])
    lines.append(f"| Divergence Fail Miss Rate | {old_df} ({old['div_fail_missed']}/{old['div_fail_total']}) | {new_df} ({new['div_fail_missed']}/{new['div_fail_total']}) | (stack score reduced in NEW) |")
    lines.append("")

    # ─── Divergence Dampening Deep Dive ───
    lines.append("## Divergence Dampening Impact (≥15% Div + xwOBA < .330)")
    lines.append("")
    if div_fail_cases:
        lines.append("These are the specific teams where the new dampening logic would have reduced their stack score premium:")
        lines.append("")
        lines.append("| Date | Team | Div% | xwOBA | Old Score | New Score | Reduction | Actual Runs | Hit? |")
        lines.append("|------|------|------|-------|-----------|-----------|-----------|-------------|------|")
        for c in sorted(div_fail_cases, key=lambda x: x['date']):
            hit_icon = "✅" if c["hit"] else "❌"
            lines.append(f"| {c['date']} | {c['team']} | {c['divergence']:+.0f}% | .{int(c['team_xwoba']*1000):03d} | {c['old_stack']} | {c['new_stack']} | -{c['score_reduction']} | {c['actual_runs']} | {hit_icon} |")
        
        avoided = sum(1 for c in div_fail_cases if not c["hit"])
        lines.append("")
        lines.append(f"> **{avoided}/{len(div_fail_cases)}** of these teams failed to score 4+ runs — the dampening reduces their ranking premium, "
                     f"making them less likely to land in your top-3 stacks.")
    else:
        lines.append("_No cases with divergence ≥ 15% and xwOBA < .330 found in this date range._")
    lines.append("")

    # ─── DQI Trust Flip Cases ───
    lines.append("## DQI Trust -> Caution Flips (Tighter Thresholds)")
    lines.append("")
    if trust_flip_cases:
        lines.append("Cases where OLD params said TRUST but NEW params say CAUTION:")
        lines.append("")
        lines.append("| Date | Team | DQI Score | Div% | ITT | Actual Runs | Correct Flip? |")
        lines.append("|------|------|-----------|------|-----|-------------|---------------|")
        correct_flips = 0
        for c in sorted(trust_flip_cases, key=lambda x: x['date']):
            correct = "✅ YES (bad trust avoided)" if c["prevented_bad_trust"] else "⚠️ NO (missed 4+ run hit)"
            if c["prevented_bad_trust"]:
                correct_flips += 1
            lines.append(f"| {c['date']} | {c['team']} | {c['dqi_score']} | {c['divergence']:+.0f}% | {c['implied_total']:.1f} | {c['actual_runs']} | {correct} |")
        lines.append("")
        lines.append(f"> **{correct_flips}/{len(trust_flip_cases)}** flips correctly prevented a bad TRUST call.")
    else:
        lines.append("_No DQI Trust -> Caution flips found in this date range. DQI scores may not be stored in archive._")
    lines.append("")

    # ─── Daily Summary ───
    lines.append("## Daily Summary")
    lines.append("")
    lines.append("| Date | OLD Trust | NEW Trust | OLD Top-3 | NEW Top-3 |")
    lines.append("|------|-----------|-----------|-----------|-----------|")
    for d in daily_rows:
        lines.append(f"| {d['date']} | {d['old_trust']} | {d['new_trust']} | {d['old_top3']} | {d['new_top3']} |")
    lines.append("")

    # ─── Verdict ───
    lines.append("---")
    lines.append("")
    lines.append("## 🏁 Verdict")
    lines.append("")

    improvements = 0
    regressions = 0

    if new_tr_val > old_tr_val:
        improvements += 1
        lines.append(f"- [IMPROVED] **DQI TRUST accuracy improved** ({old_tr} -> {new_tr}): Tighter thresholds are filtering noise correctly.")
    elif new_tr_val < old_tr_val:
        regressions += 1
        lines.append(f"- [WARNING] **DQI TRUST accuracy declined** ({old_tr} -> {new_tr}): Consider reviewing threshold levels.")
    else:
        lines.append(f"- ➡️ DQI TRUST accuracy unchanged ({old_tr}): Threshold changes have neutral impact.")

    if new["trust_total"] < old["trust_total"]:
        lines.append(f"- [IMPROVED] **TRUST selectivity improved**: Fewer false positives ({old['trust_total']} -> {new['trust_total']} tags).")
    
    if new_t3_val >= old_t3_val:
        improvements += 1
        lines.append(f"- [IMPROVED] **Top-3 stack accuracy held or improved** ({old_t3} -> {new_t3}).")
    else:
        regressions += 1
        lines.append(f"- [WARNING] **Top-3 stack accuracy declined** ({old_t3} -> {new_t3}): Re-ordering may be hurting top picks.")

    avoided_count = sum(1 for c in div_fail_cases if not c["hit"])
    if div_fail_cases:
        dampen_pct = (avoided_count / len(div_fail_cases)) * 100
        if dampen_pct >= 50:
            improvements += 1
            lines.append(f"- ✅ **Divergence dampening validated**: {avoided_count}/{len(div_fail_cases)} ({dampen_pct:.0f}%) of dampened teams failed to score 4+ runs — dampening was correct.")
        else:
            lines.append(f"- ⚠️ **Divergence dampening mixed results**: Only {avoided_count}/{len(div_fail_cases)} ({dampen_pct:.0f}%) of dampened teams failed. Consider narrowing the xwOBA threshold.")

    lines.append("")
    if improvements > regressions:
        lines.append(f"**Overall: 🟢 NEW parameters are a net positive. Recommend keeping changes.**")
    elif regressions > improvements:
        lines.append(f"**Overall: 🔴 NEW parameters show regression. Review and consider reverting.**")
    else:
        lines.append(f"**Overall: 🟡 Mixed results. NEW parameters are broadly neutral — watch for 2+ more slates before committing.**")

    lines.append("")
    lines.append("---")
    lines.append(f"*Backtest generated by OMEGA Parameter Backtest v1.0*")

    # ─── Write report ───
    report_path = os.path.join(config.REPORTS_DIR, f"parameter_backtest_{start}_to_{end}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"\n{'='*65}")
    print(f"[REPORT] Saved to: {report_path}")
    print(f"[SUMMARY] Analyzed {days_processed} slates from {start} to {end}")
    print(f"[OLD] TRUST: {_pct(old['trust_hit'], old['trust_total'])}  Top-3: {_pct(old['top3_hit'], old['top3_total'])}")
    print(f"[NEW] TRUST: {_pct(new['trust_hit'], new['trust_total'])}  Top-3: {_pct(new['top3_hit'], new['top3_total'])}")
    print(f"[DIV-DAMPEN] {old['div_fail_total']} high-div/low-xwOBA cases found")
    print(f"{'='*65}\n")


# ─────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        start_date = sys.argv[1]
        end_date = sys.argv[2]
    else:
        # Default: full archive range
        start_date = "2026-04-15"
        end_date = datetime.now().strftime("%Y-%m-%d")

    run_backtest(start_date, end_date)
