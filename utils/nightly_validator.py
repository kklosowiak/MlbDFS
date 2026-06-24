"""
Nightly Validation Report (READ-ONLY)
======================================
Runs automatically at ~4am ET via the nightly_maintenance_loop in server.py.
Compares yesterday's model signals against actual game outcomes.

OUTPUT (read-only, nothing in the model changes):
  reports/archive/validation_{date}.json   <- daily scorecard
  data/signal_validation_history.json      <- rolling 30-day accumulation

The daily JSON is human-readable. The dashboard /api/validation-history
endpoint surfaces the rolling history for the settings panel widget.

WHAT IT MEASURES:
  - Stack hit rate by CONF tier (did high-CONF stacks actually score 5+ runs?)
  - Pitcher hit rate by alpha tier (did high-alpha pitchers get QS/6K?)
  - Hitter hit rate by individual CONF (did high-CONF hitters get a hit?)
  - Signal-level breakdown: TRAP, TTP, COLD SP, is_sharp, etc.
"""

import json
import os
import sys
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

ARCHIVE_DIR  = os.path.join(ROOT, "reports", "archive")
DATA_DIR     = os.path.join(ROOT, "data")
HISTORY_PATH = os.path.join(DATA_DIR, "signal_validation_history.json")
MAX_HISTORY_DAYS = 60  # keep 60 days of history


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _hit_rate(hits, total):
    if total == 0:
        return None
    return round(hits / total * 100, 1)


def _tier(conf):
    if conf is None:
        return "UNK"
    if conf >= 80:
        return "ELITE (>=80)"
    if conf >= 65:
        return "HIGH (65-79)"
    if conf >= 50:
        return "MID (50-64)"
    return "LOW (<50)"


# ---------------------------------------------------------------------------
# Core validation
# ---------------------------------------------------------------------------

def run_daily_validation(date_str=None):
    """
    Scores yesterday's signals against actual outcomes.
    Returns a structured dict (also written to disk).
    Nothing in the model is modified.
    """
    if not date_str:
        try:
            from zoneinfo import ZoneInfo
            now_et = datetime.now(ZoneInfo("America/New_York"))
        except Exception:
            now_et = datetime.now(timezone.utc) - timedelta(hours=4)
        # Validate yesterday's slate
        yesterday = (now_et - timedelta(days=1)).date()
        date_str = yesterday.strftime("%Y-%m-%d")

    print(f"[VALIDATOR]: Running daily validation for {date_str}...")

    # Load model picks for this date
    results_path = os.path.join(ARCHIVE_DIR, f"results_{date_str}_lock.json")
    if not os.path.exists(results_path):
        results_path = os.path.join(ARCHIVE_DIR, f"results_{date_str}.json")
    results = _load_json(results_path)

    # Load actual outcomes
    actuals_path = os.path.join(ARCHIVE_DIR, f"actuals_cache_{date_str}.json")
    actuals = _load_json(actuals_path)

    if not results or not actuals:
        print(f"[VALIDATOR]: Missing results or actuals for {date_str} — skipping.")
        return None

    teams_list   = results.get("teams",    [])
    pitchers_list = results.get("pitchers", [])
    hitters_list  = results.get("hitters",  [])

    report = {
        "date":     date_str,
        "run_at":   datetime.now(timezone.utc).isoformat(),
        "stacks":   {},
        "pitchers": {},
        "hitters":  {},
        "signals":  {},
    }

    # ------------------------------------------------------------------
    # 1. Stack success rate by CONF tier
    # ------------------------------------------------------------------
    stack_tiers = {}
    for t in teams_list:
        team  = t.get("team")
        conf  = t.get("stack_confidence") or t.get("conf")
        if not team or conf is None:
            continue
        actual_team = actuals.get(team, {})
        runs = actual_team.get("runs")
        if runs is None:
            continue
        success = runs >= 5  # DFS stack success definition

        tier = _tier(float(conf))
        bucket = stack_tiers.setdefault(tier, {"hits": 0, "total": 0})
        bucket["total"] += 1
        if success:
            bucket["hits"] += 1

        # Track individual signals
        for signal in ["is_sharp", "is_trap", "is_burst", "is_gassed", "is_hot_run_msmi", "is_cold_streak_msmi"]:
            if t.get(signal):
                sig_bucket = report["signals"].setdefault(signal, {"hits": 0, "total": 0})
                sig_bucket["total"] += 1
                if success:
                    sig_bucket["hits"] += 1

    for tier, data in stack_tiers.items():
        report["stacks"][tier] = {
            "total":    data["total"],
            "hits":     data["hits"],
            "hit_rate": _hit_rate(data["hits"], data["total"]),
        }

    # ------------------------------------------------------------------
    # 2. Pitcher success rate by alpha tier
    # ------------------------------------------------------------------
    pitcher_tiers = {}
    for p in pitchers_list:
        team   = p.get("team")
        conf   = p.get("pitcher_confidence") or p.get("conf")
        pitcher = p.get("pitcher")
        if not team or conf is None:
            continue

        actual_team = actuals.get(team, {})
        sp_stats    = actual_team.get("sp_stats", {})
        sp_name     = sp_stats.get("name", "")
        k    = sp_stats.get("k", 0)
        er   = sp_stats.get("er", 0)
        try:
            ip = float(sp_stats.get("ip", "0.0"))
        except Exception:
            ip = 0.0

        # Success = 6K + <=2ER or dominant (IP>=6 + <=1ER)
        success = (k >= 6 and er <= 2) or (ip >= 6.0 and er <= 1)

        tier = _tier(float(conf))
        bucket = pitcher_tiers.setdefault(tier, {"hits": 0, "total": 0})
        bucket["total"] += 1
        if success:
            bucket["hits"] += 1

        # Signal-level: TRAP, TTP, sharp, cold form
        for signal in ["is_trap", "true_talent_penalty", "is_sharp", "is_shark"]:
            if p.get(signal):
                sig_bucket = report["signals"].setdefault(f"sp_{signal}", {"hits": 0, "total": 0})
                sig_bucket["total"] += 1
                if success:
                    sig_bucket["hits"] += 1

    for tier, data in pitcher_tiers.items():
        report["pitchers"][tier] = {
            "total":    data["total"],
            "hits":     data["hits"],
            "hit_rate": _hit_rate(data["hits"], data["total"]),
        }

    # ------------------------------------------------------------------
    # 3. Hitter success rate by CONF tier
    # ------------------------------------------------------------------
    hitter_tiers = {}
    for h in hitters_list:
        team  = h.get("team")
        conf  = h.get("hitter_confidence") or h.get("conf")
        name  = h.get("name") or h.get("player")
        if not team or conf is None or not name:
            continue

        from utils.normalization import normalize_player_name
        norm_name = normalize_player_name(name)

        actual_team   = actuals.get(team, {})
        hitter_actuals = actual_team.get("hitters", {})
        h_data = hitter_actuals.get(norm_name)
        if not h_data:
            continue

        hits = int(h_data.get("hits", 0))
        hr   = int(h_data.get("hr",   0))
        success = hits >= 1 or hr >= 1  # got on base or hit HR

        tier = _tier(float(conf))
        bucket = hitter_tiers.setdefault(tier, {"hits": 0, "total": 0})
        bucket["total"] += 1
        if success:
            bucket["hits"] += 1

    for tier, data in hitter_tiers.items():
        report["hitters"][tier] = {
            "total":    data["total"],
            "hits":     data["hits"],
            "hit_rate": _hit_rate(data["hits"], data["total"]),
        }

    # Compute signal hit rates
    for sig, data in report["signals"].items():
        data["hit_rate"] = _hit_rate(data["hits"], data["total"])

    # ------------------------------------------------------------------
    # Write daily report
    # ------------------------------------------------------------------
    out_path = os.path.join(ARCHIVE_DIR, f"validation_{date_str}.json")
    try:
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"[VALIDATOR]: Written -> {os.path.basename(out_path)}")
    except Exception as e:
        print(f"[VALIDATOR]: Failed to write daily report: {e}")

    # ------------------------------------------------------------------
    # Accumulate into rolling history
    # ------------------------------------------------------------------
    _update_history(date_str, report)

    _print_summary(date_str, report)
    return report


def _update_history(date_str, report):
    """Appends today's summary to signal_validation_history.json (capped at MAX_HISTORY_DAYS)."""
    history = _load_json(HISTORY_PATH) or {"dates": [], "records": {}}

    history["records"][date_str] = {
        "stacks":   report["stacks"],
        "pitchers": report["pitchers"],
        "hitters":  report["hitters"],
        "signals":  report["signals"],
    }

    # Prune old dates
    all_dates = sorted(history["records"].keys())
    if len(all_dates) > MAX_HISTORY_DAYS:
        for old in all_dates[:-MAX_HISTORY_DAYS]:
            del history["records"][old]

    history["dates"] = sorted(history["records"].keys())
    history["last_updated"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(HISTORY_PATH, "w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"[VALIDATOR]: Failed to update history: {e}")


def _print_summary(date_str, report):
    print(f"\n  === Validation Summary: {date_str} ===")
    print(f"  {'Category':<28} {'Tier':<18} {'Hits':>5} {'Total':>6} {'Rate':>7}")
    print("  " + "-"*65)
    for cat, tiers in [("Stacks", report["stacks"]), ("Pitchers", report["pitchers"]), ("Hitters", report["hitters"])]:
        for tier in ["ELITE (>=80)", "HIGH (65-79)", "MID (50-64)", "LOW (<50)"]:
            if tier not in tiers:
                continue
            d = tiers[tier]
            rate = f"{d['hit_rate']}%" if d['hit_rate'] is not None else "—"
            print(f"  {cat:<28} {tier:<18} {d['hits']:>5} {d['total']:>6} {rate:>7}")

    if report["signals"]:
        print(f"\n  Signal-Level:")
        for sig, d in sorted(report["signals"].items()):
            rate = f"{d['hit_rate']}%" if d['hit_rate'] is not None else "—"
            print(f"    {sig:<30} {d['hits']:>4}/{d['total']:<5}  {rate}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run daily signal validation")
    parser.add_argument("--date", help="Date to validate (YYYY-MM-DD). Defaults to yesterday.")
    args = parser.parse_args()
    run_daily_validation(args.date)
