"""Dampen confirmed team_xwoba when hourly cache refresh wiggles the same lineup."""

TEAM_XWOBA_DAMPEN_THRESHOLD = 0.015


def resolve_team_xwoba(team, prev_team, fresh_xwoba):
    """
    CONFIRMED lineups: hold prior team_xwoba unless move exceeds threshold.
    Returns (xwoba_to_use, was_dampened).
    """
    if not prev_team:
        return fresh_xwoba, False
    if team.get("lineup_status") != "CONFIRMED":
        return fresh_xwoba, False

    locked = prev_team.get("team_xwoba_locked")
    if locked is None:
        locked = prev_team.get("team_xwoba")
    if locked is None:
        return fresh_xwoba, False

    try:
        locked_f = float(locked)
        fresh_f = float(fresh_xwoba)
    except (TypeError, ValueError):
        return fresh_xwoba, False

    if abs(fresh_f - locked_f) < TEAM_XWOBA_DAMPEN_THRESHOLD:
        return round(locked_f, 3), True
    return fresh_xwoba, False
