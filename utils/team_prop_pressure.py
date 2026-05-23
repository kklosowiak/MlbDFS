"""Aggregate confirmed-lineup prop interest into team-level pressure for CONF."""

from __future__ import annotations

from utils.normalization import normalize_player_name

LABEL_HOT = "HOT"
LABEL_WARM = "WARM"
LABEL_NEUTRAL = "NEUTRAL"
LABEL_COLD = "COLD"

# Absolute gates only — no per-slate cap. Soft JUICE never counts toward raw/HOT.
HOT_MIN_RAW = 22
HOT_MIN_TARGETS_DEEP = 3
HOT_MIN_TARGETS_STACKED = 2
HOT_MIN_STACK_TARGETS = 2
HOT_MIN_STACK_TARGETS_FOR_DEEP = 1
HOT_STACKED_MIN_RAW = 24

WARM_MIN_RAW = 14
WARM_MIN_TARGETS = 2
WARM_ALT_RAW = 11
WARM_ALT_TARGETS = 1
WARM_ALT_STACK_TARGETS = 1


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
    """Strict TARGET + stack TARGET only (no is_prop_juice, no runs/rbis JUICE)."""
    pts = 0.0
    if h.get("is_juiced_target"):
        pts += 5.0
    if h.get("runs_target") or h.get("rbis_target"):
        pts += 4.0
    return pts


def compute_team_prop_pressure(team_name, hitters, confirmed_lineups=None):
    """
    Score 0–100 + label for strict prop board activity on confirmed/top hitters.
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
            "prop_stack_target_count": 0,
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
    n_stack_target = sum(1 for h in pool if h.get("runs_target") or h.get("rbis_target"))
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
        "prop_stack_target_count": n_stack_target,
        "prop_pressure_hitters": top_names,
        "prop_pressure_elite": False,
    }


def _is_hot_board(m: dict) -> bool:
    """
    HOT only when books are on multiple strict hitters with stack-market depth.
    Typical slate: a handful of teams, not most lineups.
    """
    raw = m["prop_pressure_raw"]
    nt = m["prop_target_count"]
    nst = m.get("prop_stack_target_count", 0)

    if nt >= HOT_MIN_TARGETS_DEEP and raw >= HOT_MIN_RAW and nst >= HOT_MIN_STACK_TARGETS_FOR_DEEP:
        return True
    if (
        nt >= HOT_MIN_TARGETS_STACKED
        and nst >= HOT_MIN_STACK_TARGETS
        and raw >= HOT_STACKED_MIN_RAW
    ):
        return True
    return False


def _is_warm_board(m: dict) -> bool:
    if _is_hot_board(m):
        return False
    nt = m["prop_target_count"]
    nst = m.get("prop_stack_target_count", 0)
    raw = m["prop_pressure_raw"]
    if nt >= WARM_MIN_TARGETS and raw >= WARM_MIN_RAW:
        return True
    if (
        nt >= WARM_ALT_TARGETS
        and nst >= WARM_ALT_STACK_TARGETS
        and raw >= WARM_ALT_RAW
    ):
        return True
    return False


def _assign_team_labels(team_metrics: list[tuple[dict, dict]]):
    for _t, m in team_metrics:
        if _is_hot_board(m):
            m["prop_pressure_label"] = LABEL_HOT
            m["prop_pressure_elite"] = True
        elif _is_warm_board(m):
            m["prop_pressure_label"] = LABEL_WARM
            m["prop_pressure_elite"] = False
        elif (
            m["prop_target_count"] == 0
            and m.get("prop_stack_target_count", 0) == 0
            and m["prop_pressure_raw"] <= 2
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
