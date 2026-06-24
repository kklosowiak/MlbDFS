"""
Weight Proposer (READ-ONLY)
============================
Analyzes data/signal_validation_history.json to surface weight adjustment
proposals for human review. This module NEVER modifies any model file.

GUARDRAILS:
  - Requires at least MIN_DAYS days of history before proposing any change.
  - Maximum change per signal: MAX_DELTA_PCT (20%) in either direction.
  - Minimum absolute sample count: MIN_SAMPLES per signal before it qualifies.
  - Proposals are capped at sane absolute bounds (no weight can exceed ±60).

USAGE:
  from utils.weight_proposer import propose_weight_adjustments
  result = propose_weight_adjustments()
  # result["proposals"]  -> list of {signal, category, current, proposed, delta, reason, confidence}
  # result["meta"]       -> summary metadata
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HISTORY_PATH = os.path.join(ROOT, "data", "signal_validation_history.json")
WEIGHTS_PATH = os.path.join(ROOT, "data", "weights.json")

# Safety guardrails
MIN_DAYS = 7          # Minimum days of history required before any proposal
MIN_SAMPLES = 10      # Minimum cumulative signal triggers across history
MAX_DELTA_PCT = 0.20  # Max ±20% weight change per proposal cycle
ABS_MAX_WEIGHT = 60.0 # Hard cap on any weight's absolute value

# Expected "baseline" hit rates by signal type (null hypothesis if signal had no edge)
# Stack signals: success = team scores 5+ runs (~38% league-wide baseline)
# Pitcher signals: success = pitcher gets QS/6K (~28% baseline)
STACK_BASELINE = 0.38
PITCHER_BASELINE = 0.28

# Signal → weight key mapping (matches weights.json schema)
SIGNAL_MAP = {
    # Stack signals (stacks.{key})
    "is_sharp":           ("stacks", "is_sharp",           "stack",   True),
    "is_trap":            ("stacks", "is_trap",            "stack",   False),  # False = negative signal
    "is_burst":           ("stacks", "is_burst",           "stack",   True),
    "is_gassed":          ("stacks", "is_gassed",          "stack",   True),
    "is_hot_run_msmi":    ("stacks", "is_hot_run_msmi",    "stack",   True),
    "is_cold_streak_msmi":("stacks", "is_cold_streak_msmi","stack",   False),
    # Pitcher signals (pitchers.{key}) — stored with sp_ prefix in signals dict
    "sp_is_trap":         ("pitchers", "is_trap",          "pitcher", False),
    "sp_is_sharp":        ("pitchers", "is_sharp",         "pitcher", True),
    "sp_is_shark":        ("pitchers", "is_shark",         "pitcher", True),
    "sp_true_talent_penalty": ("pitchers", "true_talent_penalty", "pitcher", False),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _load_json(path: str) -> dict | None:
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_current_weights() -> dict:
    """Load weights.json or fall back to hardcoded defaults."""
    data = _load_json(WEIGHTS_PATH)
    if data:
        return data
    return {
        "stacks": {
            "is_sharp": 12.0, "is_trap": -24.0, "is_burst": 12.0,
            "is_gassed": 14.0, "is_hot_run_msmi": 12.0, "is_cold_streak_msmi": -24.0,
        },
        "pitchers": {
            "is_trap": -24.0, "true_talent_penalty": -12.0,
            "is_sharp": 10.0, "is_shark": 10.0, "early_innings_volatility": -10.0,
        },
    }


def _aggregate_signal_history(records: dict) -> dict[str, dict]:
    """
    Rolls up per-date signal records into cumulative hit/total counts.
    records is: {date_str -> {signals: {signal_key: {hits, total}}, ...}}
    """
    cumulative: dict[str, dict] = {}
    for date_str, day_data in records.items():
        signals = day_data.get("signals", {})
        for sig, counts in signals.items():
            agg = cumulative.setdefault(sig, {"hits": 0, "total": 0, "days_seen": 0})
            agg["hits"]     += counts.get("hits", 0)
            agg["total"]    += counts.get("total", 0)
            if counts.get("total", 0) > 0:
                agg["days_seen"] += 1
    return cumulative


def _hit_rate(hits: int, total: int) -> float | None:
    if total == 0:
        return None
    return hits / total


def _propose_delta(
    signal_key: str,
    category: str,
    is_positive: bool,
    current_weight: float,
    observed_hr: float,
    baseline: float,
    total_samples: int,
) -> tuple[float, str, str]:
    """
    Compute the proposed weight delta and generate a human-readable rationale.

    Returns: (proposed_weight, direction, reason)
    """
    edge = observed_hr - baseline  # positive = outperforming baseline
    max_delta = abs(current_weight) * MAX_DELTA_PCT

    if is_positive:
        # Positive signals: if edge is large, the signal has real alpha → slight boost
        # If edge is negative (signal performing worse than random), soften weight
        if edge > 0.10:  # Signal crushing baseline by >10pp
            raw_delta = min(max_delta, abs(current_weight) * 0.10)
            direction = "↑"
            reason = (
                f"Hit rate {observed_hr:.1%} vs {baseline:.1%} baseline "
                f"(+{edge:.1%} edge over {total_samples} samples) → "
                f"signal has strong alpha, proposing modest boost."
            )
        elif edge < -0.08:  # Signal underperforming baseline by >8pp
            raw_delta = -min(max_delta, abs(current_weight) * 0.10)
            direction = "↓"
            reason = (
                f"Hit rate {observed_hr:.1%} vs {baseline:.1%} baseline "
                f"({edge:.1%} edge over {total_samples} samples) → "
                f"signal underperforming, proposing softening."
            )
        else:
            return current_weight, "→", f"Hit rate {observed_hr:.1%} within expected range ({baseline:.1%} baseline). No change needed."
    else:
        # Negative signals (traps, cold streaks): lower observed HR → signal is working well
        # Higher observed HR → penalty may be too harsh or signal is noise
        if edge < -0.10:  # Flagged teams scoring much less than baseline → working great
            raw_delta = -min(max_delta, abs(current_weight) * 0.10)  # deepen penalty
            direction = "↑ Penalty"
            reason = (
                f"Flagged teams: hit rate {observed_hr:.1%} vs {baseline:.1%} baseline "
                f"({edge:.1%} below baseline over {total_samples} samples) → "
                f"signal is working well, proposing to deepen penalty."
            )
        elif edge > 0.08:  # Flagged teams scoring more than baseline → penalty may be too strong
            raw_delta = min(max_delta, abs(current_weight) * 0.10)  # soften penalty
            direction = "↓ Penalty"
            reason = (
                f"Flagged teams: hit rate {observed_hr:.1%} vs {baseline:.1%} baseline "
                f"(+{edge:.1%} above baseline over {total_samples} samples) → "
                f"flag may be over-penalizing, proposing to soften."
            )
        else:
            return current_weight, "→", f"Hit rate {observed_hr:.1%} within expected range ({baseline:.1%} baseline). No change needed."

    proposed = current_weight + raw_delta
    proposed = max(-ABS_MAX_WEIGHT, min(ABS_MAX_WEIGHT, proposed))
    return round(proposed, 1), direction, reason


# ---------------------------------------------------------------------------
# Main API
# ---------------------------------------------------------------------------

def propose_weight_adjustments() -> dict:
    """
    Analyzes signal validation history and returns weight proposals.
    READ-ONLY — this function never writes any file.

    Returns:
        {
          "proposals": [...],  # list of proposal dicts
          "meta": {...},       # days analyzed, total samples, generated_at
          "status": "ok" | "insufficient_data" | "no_history",
          "message": str,
        }
    """
    history = _load_json(HISTORY_PATH)
    current_weights = _load_current_weights()

    if not history:
        return {
            "proposals": [],
            "meta": {"days_analyzed": 0, "generated_at": datetime.now(timezone.utc).isoformat()},
            "status": "no_history",
            "message": (
                "No validation history found. The nightly validator runs at ~4:05am ET "
                "and builds data/signal_validation_history.json. Check back after the next run."
            ),
        }

    records = history.get("records", history) if isinstance(history, dict) else {}
    # If the history is already a flat records dict (date → report), use as-is
    if records and not isinstance(list(records.values())[0], dict):
        records = history

    days_analyzed = len(records)

    if days_analyzed < MIN_DAYS:
        return {
            "proposals": [],
            "meta": {
                "days_analyzed": days_analyzed,
                "days_required": MIN_DAYS,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            },
            "status": "insufficient_data",
            "message": (
                f"Only {days_analyzed} day(s) of validation history available. "
                f"Need at least {MIN_DAYS} days before proposals are reliable. "
                f"Check back in {MIN_DAYS - days_analyzed} more day(s)."
            ),
        }

    cumulative = _aggregate_signal_history(records)
    proposals = []
    total_samples_all = 0

    for sig_key, (cat, weight_key, signal_type, is_positive) in SIGNAL_MAP.items():
        agg = cumulative.get(sig_key)
        if not agg:
            continue

        total = agg["total"]
        hits = agg["hits"]
        total_samples_all += total

        if total < MIN_SAMPLES:
            continue  # Not enough data for this signal

        baseline = STACK_BASELINE if signal_type == "stack" else PITCHER_BASELINE
        observed_hr = _hit_rate(hits, total)
        if observed_hr is None:
            continue

        current_weight = current_weights.get(cat, {}).get(weight_key)
        if current_weight is None:
            continue

        proposed_weight, direction, reason = _propose_delta(
            sig_key, cat, is_positive,
            current_weight, observed_hr, baseline, total
        )

        # Sample size → confidence label
        if total >= 50:
            confidence = "HIGH"
        elif total >= 25:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        delta = round(proposed_weight - current_weight, 1)

        proposals.append({
            "signal":         sig_key,
            "category":       cat,
            "weight_key":     weight_key,
            "current_weight": current_weight,
            "proposed_weight": proposed_weight,
            "delta":          delta,
            "direction":      direction,
            "observed_hit_rate": round(observed_hr * 100, 1),
            "baseline_hit_rate": round(baseline * 100, 1),
            "total_samples":  total,
            "days_seen":      agg["days_seen"],
            "confidence":     confidence,
            "reason":         reason,
            "has_change":     delta != 0.0,
        })

    # Sort: changes first, then by confidence (HIGH → MEDIUM → LOW)
    conf_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    proposals.sort(key=lambda p: (not p["has_change"], conf_order.get(p["confidence"], 3)))

    changes = [p for p in proposals if p["has_change"]]
    no_changes = [p for p in proposals if not p["has_change"]]

    return {
        "proposals": proposals,
        "meta": {
            "days_analyzed":   days_analyzed,
            "signals_tracked": len(proposals),
            "signals_with_change": len(changes),
            "signals_stable":  len(no_changes),
            "total_samples":   total_samples_all,
            "generated_at":    datetime.now(timezone.utc).isoformat(),
            "guardrails": {
                "min_days":       MIN_DAYS,
                "min_samples":    MIN_SAMPLES,
                "max_delta_pct":  f"{MAX_DELTA_PCT:.0%}",
                "abs_max_weight": ABS_MAX_WEIGHT,
            },
        },
        "status": "ok",
        "message": (
            f"Analyzed {days_analyzed} days of validation history. "
            f"{len(changes)} signal(s) have proposed weight adjustments. "
            f"All proposals are read-only — no model changes have been applied."
        ),
    }
