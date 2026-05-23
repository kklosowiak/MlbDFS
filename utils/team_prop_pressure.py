"""Aggregate confirmed-lineup prop interest into team-level pressure for CONF."""

from __future__ import annotations

from utils.normalization import normalize_player_name

LABEL_HOT = "HOT"
LABEL_WARM = "WARM"
LABEL_NEUTRAL = "NEUTRAL"
LABEL_COLD = "COLD"

# Strict team-level prop pressure (soft per-hitter JUICE excluded from team score)
HOT_MIN_RAW = 18
HOT_MIN_TARGETS = 2
HOT_MIN_STACK_MARKETS = 2
WARM_MIN_RAW = 12
WARM_MIN_TARGETS = 2


def _confirmed_set_for_team(team_name, confirmed_lineups):
    if not confirmed_lineups:
        return None
    for lineup_team, players in confirmed_lineups.items():
        lt = (lineup_team or "").lower()
        tn = (team_name or "").lower()
        if tn in lt or lt in tn:
            return {normalize_player_name(p) for p in (players or [])}
    return None


def _hitter_strict_prop_points(h):
    """Only strict TARGET + stack-correlated juice (not blanket is_prop_juice)."""
    pts = 0.0
    if h.get("is_juiced_target"):
        pts += 5.0
    if h.get("runs_target") or h.get("rbis_target"):
        pts += 4.0
    elif h.get("runs_juice") or h.get("rbis_juice"):
        pts += 2.0
    return pts


def compute_team_prop_pressure(team_name, hitters, confirmed_lineups=None):
    """
    Score 0–100 + label for strict prop board activity on confirmed/top hitters.
    Soft JUICE flags are excluded so most teams are not HOT by default.
    """
    roster = [h for h in (hitters or []) if h.get("team") == team_name]
    if not roster:
        return {
            "prop_pressure_score": 0,
            "prop_pressure_raw": 0.0,
            "prop_pressure_label": LABEL_COLD,
            "prop_target_count": 0,
            "prop_juice_count": 0,
            "prop_stack_market_count": 0,
            "prop_pressure_hitters": [],
            "prop_pressure_elite": False,
        }

    confirmed = _confirmed_set_for_team(team_name, confirmed_lineups)
    if confirmed:
        pool = [
            h for h in roster
            if normalize_player_name(h.get("name", "")) in confirmed
        ]
    else:
        pool = sorted(
            roster,
            key=lambda x: float(x.get("matchup_xwoba", 0) or 0),
            reverse=True,
        )[:9]

    if not pool:
        pool = roster[:9]

    n_target = sum(1 for h in pool if h.get("is_juiced_target"))
    n_juice = sum(1 for h in pool if h.get("is_prop_juice"))
    n_stack = sum(
        1 for h in pool
        if h.get("runs_juice") or h.get("rbis_juice")
        or h.get("runs_target") or h.get("rbis_target")
    )
    raw = sum(_hitter_strict_prop_points(h) for h in pool)
    max_raw = len(pool) * 9.0
    score = int(min(100, round((raw / max(max_raw, 1.0)) * 100)))

    top_names = sorted(
        pool,
        key=lambda x: _hitter_strict_prop_points(x),
        reverse=True,
    )[:4]
    top_names = [h.get("name", "") for h in top_names if _hitter_strict_prop_points(h) > 0]

    return {
        "prop_pressure_score": score,
        "prop_pressure_raw": round(raw, 1),
        "prop_pressure_label": LABEL_NEUTRAL,
        "prop_target_count": n_target,
        "prop_juice_count": n_juice,
        "prop_stack_market_count": n_stack,
        "prop_pressure_hitters": top_names,
        "prop_pressure_elite": False,
    }


def _is_hot_board(m: dict) -> bool:
    """Absolute HOT gate — any team meeting criteria qualifies (no slate cap)."""
    if m["prop_pressure_raw"] < HOT_MIN_RAW:
        return False
    if m["prop_target_count"] < HOT_MIN_TARGETS:
        return False
    return m["prop_target_count"] >= 3 or (
        m["prop_stack_market_count"] >= HOT_MIN_STACK_MARKETS
        and m["prop_target_count"] >= HOT_MIN_TARGETS
    )


def _is_warm_board(m: dict) -> bool:
    if _is_hot_board(m):
        return False
    if m["prop_target_count"] >= WARM_MIN_TARGETS and m["prop_pressure_raw"] >= WARM_MIN_RAW:
        return True
    return m["prop_target_count"] >= 1 and m["prop_pressure_raw"] >= 16


def _assign_team_labels(team_metrics: list[tuple[dict, dict]]):
    """Apply HOT/WARM/COLD from strict per-team thresholds only."""
    for _t, m in team_metrics:
        if _is_hot_board(m):
            m["prop_pressure_label"] = LABEL_HOT
            m["prop_pressure_elite"] = True
        elif _is_warm_board(m):
            m["prop_pressure_label"] = LABEL_WARM
            m["prop_pressure_elite"] = False
        elif (
            m["prop_target_count"] == 0
            and m["prop_pressure_raw"] <= 3
            and m["prop_stack_market_count"] == 0
        ):
            m["prop_pressure_label"] = LABEL_COLD
            m["prop_pressure_elite"] = False
        else:
            m["prop_pressure_label"] = LABEL_NEUTRAL
            m["prop_pressure_elite"] = False


def attach_team_prop_pressure(teams, hitters, confirmed_lineups=None):
    """Mutates each team dict with prop pressure fields."""
    pairs = []
    for t in teams or []:
        m = compute_team_prop_pressure(t.get("team") or "", hitters, confirmed_lineups)
        pairs.append((t, m))

    _assign_team_labels(pairs)

    for t, m in pairs:
        t.update(m)
    return teams
