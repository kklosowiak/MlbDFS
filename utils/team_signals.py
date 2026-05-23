"""Team matrix signal flags — single source of truth for UI pills."""

BLIND_SPOT_MIN_GAP = 50.0


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


# BURST: star-concentrated lineup + exploitable SP/pen script (stricter than v8 OR gate)
BURST_MIN_CONCENTRATION = 0.370
BURST_MIN_CONC_GAP = 0.020
BURST_PEN_FATIGUE = 85.0
BURST_SHORT_LEASH_OUTS = 15.0
BURST_TARGETABLE_SP_PHYS = 55.0


def evaluate_burst_signal(
    power_concentration,
    team_xwoba,
    opp_bullpen_score,
    opp_pitcher_outs,
    opp_pitcher_physics,
):
    """
    GPP burst = top-heavy power (not just a good balanced lineup) plus a path to extra innings
    vs a targetable starter and/or a cooked bullpen on a short leash.
    """
    conc = float(power_concentration or 0.330)
    xw = float(team_xwoba or 0.330)
    gap = round(conc - xw, 3)
    pen = float(opp_bullpen_score or 0)
    outs = float(opp_pitcher_outs or 18.0)
    opp_phys = float(opp_pitcher_physics or 0)

    star_power = conc >= BURST_MIN_CONCENTRATION and gap >= BURST_MIN_CONC_GAP
    targetable_sp = 0 < opp_phys <= BURST_TARGETABLE_SP_PHYS
    pen_script = (
        pen >= BURST_PEN_FATIGUE
        and outs < BURST_SHORT_LEASH_OUTS
        and conc >= 0.365
    )
    is_burst = star_power and (targetable_sp or pen_script)
    return is_burst, gap


def apply_team_burst(team, opp_pitcher_outs=18.0):
    """Recompute is_burst from stored team metrics (optional outs from opposing SP)."""
    is_burst, gap = evaluate_burst_signal(
        team.get("power_concentration"),
        team.get("team_xwoba"),
        team.get("bullpen_fatigue"),
        opp_pitcher_outs,
        team.get("opp_pitcher_physics"),
    )
    team["burst_conc_gap"] = gap
    team["is_burst"] = is_burst
    return team
