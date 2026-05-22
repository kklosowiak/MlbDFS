"""Shared xwOBA estimates — align platoon UI with stack/hitter engine."""


def ops_to_xwoba(ops):
    """Map OPS to approximate xwOBA when Statcast xwOBA is unavailable."""
    if not ops or ops <= 0:
        return 0.320
    return max(0.250, min(0.480, (float(ops) * 1.20) - 0.075))


def xwoba_to_phy_score(xwoba):
    """Map matchup/team xwOBA to a 0–100 PHY display score (slate-comparable)."""
    x = float(xwoba or 0.330)
    return round(max(0.0, min(100.0, ((x - 0.280) / 0.140) * 100)), 1)


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
