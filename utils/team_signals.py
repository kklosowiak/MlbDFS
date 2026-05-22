"""Team matrix signal flags — single source of truth for UI pills."""

BLIND_SPOT_MIN_GAP = 55.0


def team_blind_spot_gap(physics_score, market_score, market_raw=None):
    """
    PHY − MKT using the same scale as the Teams matrix columns (0–100 pillar scores).
    Prefer market_raw when present (full Vegas pillar); market_score should match it on new runs.
    """
    phy = float(physics_score or 0)
    mkt = float(market_score or 0)
    if market_raw is not None:
        try:
            mkt = float(market_raw)
        except (TypeError, ValueError):
            pass
    return round(phy - mkt, 1)


def apply_team_blind_spot(team):
    """Set blind_spot_gap + is_blind_spot on a team dict (mutates in place)."""
    gap = team_blind_spot_gap(
        team.get("physics_score"),
        team.get("market_score"),
        team.get("market_raw"),
    )
    team["blind_spot_gap"] = gap
    team["is_blind_spot"] = gap >= BLIND_SPOT_MIN_GAP
    return team
