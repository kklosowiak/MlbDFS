"""Shared xwOBA estimates — align platoon UI with stack/hitter engine."""


def ops_to_xwoba(ops):
    """
    Map OPS → approximate xwOBA when Savant xwOBA is unavailable.
    Calibrated to MLB reality (~.710 OPS ≈ .320 xwOBA, elite ~.950 OPS ≈ .400).
    Old formula (ops*1.2 - 0.075) capped most lineups at .48 and collapsed PHY.
    """
    if not ops or ops <= 0:
        return 0.310
    ops = float(ops)
    xw = 0.180 + (ops * 0.230)
    return round(max(0.250, min(0.420, xw)), 3)


def cap_matchup_xwoba(xwoba):
    """Hard ceiling for platoon-adjusted matchup xwOBA."""
    return round(min(0.420, max(0.250, float(xwoba or 0.310))), 3)


def xwoba_to_phy_score(xwoba):
    """Map lineup xwOBA to 0–100 PHY (.280 weak → .400 elite)."""
    x = float(xwoba or 0.310)
    return round(max(0.0, min(100.0, ((x - 0.280) / 0.120) * 100)), 1)


def woba_proxy_to_xwoba(woba_proxy, ops_fallback=0.0):
    """Prefer wOBA proxy from splits; fall back to OPS heuristic."""
    if woba_proxy and float(woba_proxy) >= 0.280:
        return round(float(woba_proxy), 3)
    return round(ops_to_xwoba(ops_fallback), 3)


def platoon_advantage_label(xwoba_vs_hand):
    """Primary EDGE label from xwOBA vs opposing pitcher hand."""
    x = float(xwoba_vs_hand or 0)
    if x >= 0.360:
        return "ELITE PLATOON"
    if x >= 0.335:
        return "STRONG EDGE"
    if x >= 0.310:
        return "NEUTRAL"
    if x >= 0.290:
        return "SLIGHT FADE"
    return "PLATOON TRAP"
