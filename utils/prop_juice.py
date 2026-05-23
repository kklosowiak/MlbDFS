"""Strict TARGET vs soft JUICE prop detection for pitchers and hitters."""

from __future__ import annotations

MIN_JUICE_GAP_AMERICAN = 20
SOFT_JUICE_GAP_AMERICAN = 5
PITCHER_TARGET_MIN_K_LINE = 5.0
PITCHER_TARGET_MIN_PHYSICS = 55.0
HITTER_TARGET_MIN_XWOBA = 0.340
HITTER_TARGET_MIN_GAP = 15
MAX_PITCHER_TARGETS = 10
MAX_HITTER_TARGETS = 45


def _to_american(price):
    if price is None:
        return None
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if 1.0 < p < 100.0:
        if p >= 2.0:
            return int((p - 1) * 100)
        return int(-100 / (p - 1))
    return int(p)


def american_juice_gap(over_price, under_price):
    """
    Positive gap when Over is juiced vs Under on the same line/book.
    Uses American odds difference (over better = lower number when both fav side).
    """
    o = _to_american(over_price)
    u = _to_american(under_price)
    if o is None or u is None:
        return 0
    if o < 0 and u < 0:
        return u - o
    if o > 0 and u > 0:
        return o - u
    if o < 0 < u:
        return abs(o) + u
    if u < 0 < o:
        return -(abs(u) + o)
    return 0


def scan_prop_pairs(prop_rows, player_norm, side_over="Over", side_under="Under"):
    """
    Scan prop market rows for a player. Returns list of
    {book, point, over, under, gap}.
    """
    norm = player_norm
    pairs = {}
    for row in prop_rows or []:
        name = row.get("player_name") or ""
        from utils.normalization import normalize_player_name

        if normalize_player_name(name) != norm:
            continue
        book = row.get("bookmaker") or "unknown"
        pt = row.get("point")
        side = row.get("side")
        key = (book, pt)
        if key not in pairs:
            pairs[key] = {"book": book, "point": pt, "over": None, "under": None}
        price = _to_american(row.get("price"))
        if side == side_over:
            pairs[key]["over"] = price
        elif side == side_under:
            pairs[key]["under"] = price

    out = []
    for rec in pairs.values():
        if rec["over"] is None or rec["under"] is None:
            continue
        gap = american_juice_gap(rec["over"], rec["under"])
        if gap > 0:
            out.append({**rec, "gap": gap})
    return out


def evaluate_pitcher_k_juice(prop_rows, pitcher_name, *, k_line, physics_talent):
    """
    Returns is_juiced_target (strict TARGET), is_prop_juice (soft JUICE), best_gap.
    """
    from utils.normalization import normalize_player_name

    norm = normalize_player_name(pitcher_name)
    pairs = scan_prop_pairs(prop_rows, norm)
    if not pairs:
        return False, False, 0

    best_gap = max(p["gap"] for p in pairs)
    is_prop_juice = best_gap >= SOFT_JUICE_GAP_AMERICAN

    try:
        k_f = float(k_line) if k_line is not None else 0.0
    except (TypeError, ValueError):
        k_f = 0.0
    phys = float(physics_talent or 0)

    is_target = (
        is_prop_juice
        and best_gap >= MIN_JUICE_GAP_AMERICAN
        and k_f >= PITCHER_TARGET_MIN_K_LINE
        and phys >= PITCHER_TARGET_MIN_PHYSICS
    )
    return is_target, is_prop_juice, best_gap


def evaluate_hitter_prop_juice(over_price, under_price, *, matchup_xwoba=0.33):
    """Single market pair (hits or TB)."""
    gap = american_juice_gap(over_price, under_price)
    is_prop_juice = gap >= SOFT_JUICE_GAP_AMERICAN
    xw = float(matchup_xwoba or 0)
    is_target = (
        is_prop_juice
        and gap >= HITTER_TARGET_MIN_GAP
        and xw >= HITTER_TARGET_MIN_XWOBA
    )
    return is_target, is_prop_juice, gap


def apply_hitter_target_caps(hitters, max_targets=MAX_HITTER_TARGETS):
    """Keep strict TARGET only on top N by gap then xwOBA."""
    candidates = []
    for h in hitters:
        if h.get("is_juiced_target"):
            candidates.append(h)
            h["is_juiced_target"] = False
    candidates.sort(
        key=lambda x: (x.get("_juice_gap", 0), x.get("matchup_xwoba", 0)),
        reverse=True,
    )
    for h in candidates[:max_targets]:
        h["is_juiced_target"] = True
    return hitters


def apply_pitcher_target_caps(pitchers, max_targets=MAX_PITCHER_TARGETS):
    candidates = []
    for p in pitchers:
        if p.get("is_juiced_target"):
            candidates.append(p)
            p["is_juiced_target"] = False
    candidates.sort(
        key=lambda x: (x.get("_juice_gap", 0), x.get("alpha_score", 0)),
        reverse=True,
    )
    for p in candidates[:max_targets]:
        p["is_juiced_target"] = True
    return pitchers
