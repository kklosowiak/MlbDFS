"""Aggregate confirmed-lineup prop interest into team-level pressure for CONF."""

from __future__ import annotations

from utils.normalization import normalize_player_name

LABEL_HOT = "HOT"
LABEL_WARM = "WARM"
LABEL_NEUTRAL = "NEUTRAL"
LABEL_COLD = "COLD"


def _confirmed_set_for_team(team_name, confirmed_lineups):
    if not confirmed_lineups:
        return None
    for lineup_team, players in confirmed_lineups.items():
        lt = (lineup_team or "").lower()
        tn = (team_name or "").lower()
        if tn in lt or lt in tn:
            return {normalize_player_name(p) for p in (players or [])}
    return None


def _hitter_prop_points(h):
    pts = 0.0
    if h.get("is_juiced_target"):
        pts += 4.0
    elif h.get("is_prop_juice"):
        pts += 2.0
    if h.get("runs_juice") or h.get("rbis_juice"):
        pts += 2.0
    if h.get("runs_target") or h.get("rbis_target"):
        pts += 3.0
    gap = float(h.get("_juice_gap", 0) or 0)
    if gap >= 20:
        pts += 1.0
    return pts


def compute_team_prop_pressure(team_name, hitters, confirmed_lineups=None):
    """
    Score 0–100 + label for how much prop market action sits on this team's hitters.
    Uses confirmed lineup when available; else top 9 by matchup xwOBA.
    """
    roster = [h for h in (hitters or []) if h.get("team") == team_name]
    if not roster:
        return {
            "prop_pressure_score": 0,
            "prop_pressure_label": LABEL_COLD,
            "prop_target_count": 0,
            "prop_juice_count": 0,
            "prop_stack_market_count": 0,
            "prop_pressure_hitters": [],
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
    raw = sum(_hitter_prop_points(h) for h in pool)
    max_raw = len(pool) * 7.0
    score = int(min(100, round((raw / max(max_raw, 1.0)) * 100)))

    if n_target >= 2 or (n_target >= 1 and n_stack >= 2) or raw >= 14:
        label = LABEL_HOT
    elif n_target >= 1 or n_juice >= 3 or n_stack >= 2 or raw >= 8:
        label = LABEL_WARM
    elif raw <= 2 and n_juice == 0 and n_target == 0:
        label = LABEL_COLD
    else:
        label = LABEL_NEUTRAL

    top_names = sorted(
        pool,
        key=lambda x: _hitter_prop_points(x),
        reverse=True,
    )[:4]
    top_names = [h.get("name", "") for h in top_names if _hitter_prop_points(h) > 0]

    return {
        "prop_pressure_score": score,
        "prop_pressure_label": label,
        "prop_target_count": n_target,
        "prop_juice_count": n_juice,
        "prop_stack_market_count": n_stack,
        "prop_pressure_hitters": top_names,
    }


def attach_team_prop_pressure(teams, hitters, confirmed_lineups=None):
    """Mutates each team dict with prop pressure fields."""
    for t in teams or []:
        team_name = t.get("team") or ""
        metrics = compute_team_prop_pressure(team_name, hitters, confirmed_lineups)
        t.update(metrics)
    return teams
