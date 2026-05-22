"""Pitcher TRAP detection with sticky hold when prop odds drop from the feed."""

TRAP_K_ODDS_MIN = 125
TRAP_ML_MOVE_MIN = 10
TRAP_INFLATED_K_LINE_MIN = 4.0
SHORT_LEASH_OUTS_MAX = 15.5
SHORT_LEASH_OUTS_ODDS_MIN = 100


def _norm_odds(val):
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def compute_fresh_trap(*, ml_move, k_move, k_line, k_odds, outs_line, outs_odds):
    """Pure TRAP rules from current lines/odds (no memory)."""
    is_trap = False
    trap_is_short_leash = False
    trap_is_vulnerable = False
    is_death_sentence = False
    k_odds_f = _norm_odds(k_odds)

    if ml_move > TRAP_ML_MOVE_MIN and k_move < 0:
        is_trap = True
        trap_is_vulnerable = True
    if k_odds_f is not None and k_odds_f > TRAP_K_ODDS_MIN:
        is_trap = True
        trap_is_vulnerable = True

    # Books steamed the team but K price is off the board or still juiced (Myers-style)
    if k_line is not None and ml_move > TRAP_ML_MOVE_MIN:
        try:
            inflated_k = float(k_line) >= TRAP_INFLATED_K_LINE_MIN
        except (TypeError, ValueError):
            inflated_k = False
        if inflated_k and (k_odds_f is None or k_odds_f > TRAP_K_ODDS_MIN):
            is_trap = True
            trap_is_vulnerable = True

    if outs_line is not None and outs_odds is not None:
        try:
            if float(outs_line) <= SHORT_LEASH_OUTS_MAX and float(outs_odds) >= SHORT_LEASH_OUTS_ODDS_MIN:
                is_trap = True
                is_death_sentence = True
                trap_is_short_leash = True
        except (TypeError, ValueError):
            pass

    if trap_is_short_leash and trap_is_vulnerable:
        trap_type = "Both"
    elif trap_is_short_leash:
        trap_type = "Short Leash"
    elif trap_is_vulnerable:
        trap_type = "Vulnerable"
    else:
        trap_type = None

    return {
        "is_trap": is_trap,
        "trap_type": trap_type,
        "is_death_sentence": is_death_sentence,
    }


def props_feed_partial(*, k_odds, outs_odds, prev_pitcher):
    """True when the odds API dropped prices we had on the last run."""
    if not prev_pitcher:
        return False
    prev_k = _norm_odds(prev_pitcher.get("k_odds"))
    prev_outs = _norm_odds(prev_pitcher.get("outs_odds"))
    k_missing = k_odds is None and prev_k is not None
    outs_missing = outs_odds is None and prev_outs is not None
    return k_missing or outs_missing


def merge_prop_snapshot(k_line, k_odds, outs_line, outs_odds, prev_pitcher):
    """Fill missing odds from previous run for evaluation only."""
    if not prev_pitcher:
        return k_line, k_odds, outs_line, outs_odds, False

    merged = False
    if k_odds is None and prev_pitcher.get("k_odds") is not None:
        k_odds = prev_pitcher.get("k_odds")
        merged = True
    if outs_odds is None and prev_pitcher.get("outs_odds") is not None:
        outs_odds = prev_pitcher.get("outs_odds")
        merged = True
    return k_line, k_odds, outs_line, outs_odds, merged


def _prev_sticky_trap(prev_pitcher):
    if not prev_pitcher:
        return False
    return bool(prev_pitcher.get("sticky_trap") or prev_pitcher.get("is_trap"))


def resolve_pitcher_trap(
    *,
    prev_pitcher,
    ml_move,
    k_move,
    k_line,
    k_odds,
    outs_line,
    outs_odds,
):
    """
    Sticky TRAP: never clear solely because K/outs odds vanished between refreshes.
    Clear only when fresh K odds are present and no longer qualify as juiced.
    """
    prev_trap = _prev_sticky_trap(prev_pitcher)
    prev_type = prev_pitcher.get("trap_type") if prev_pitcher else None
    new_k = _norm_odds(k_odds)

    # Prior TRAP + missing K price on feed → hold (even if last JSON already cleared is_trap)
    if prev_trap and new_k is None:
        return {
            "is_trap": True,
            "trap_type": prev_type or "Vulnerable",
            "is_death_sentence": bool(prev_pitcher.get("is_death_sentence"))
            if prev_pitcher
            else False,
            "trap_prop_note": "K prop price missing on feed — TRAP held until lines reprice.",
            "props_feed_status": "held",
            "sticky_trap": True,
        }

    eval_k_line, eval_k_odds, eval_outs_line, eval_outs_odds, merged = merge_prop_snapshot(
        k_line, k_odds, outs_line, outs_odds, prev_pitcher
    )
    fresh = compute_fresh_trap(
        ml_move=ml_move,
        k_move=k_move,
        k_line=eval_k_line,
        k_odds=eval_k_odds,
        outs_line=eval_outs_line,
        outs_odds=eval_outs_odds,
    )

    partial = props_feed_partial(
        k_odds=k_odds, outs_odds=outs_odds, prev_pitcher=prev_pitcher
    )
    note = None
    status = "ok"
    sticky_trap = fresh["is_trap"]

    # Fresh K odds on wire — allow clear or re-arm
    if new_k is not None:
        if prev_trap and not fresh["is_trap"]:
            prev_k = _norm_odds(prev_pitcher.get("k_odds") if prev_pitcher else None)
            if prev_k is not None and new_k <= TRAP_K_ODDS_MIN:
                note = f"K prop repriced ({int(prev_k):+d} → {int(new_k):+d}) — TRAP cleared."
                status = "repriced"
                sticky_trap = False
        return {**fresh, "trap_prop_note": note, "props_feed_status": status, "sticky_trap": sticky_trap}

    # Partial feed with merged snapshot odds
    if partial and fresh["is_trap"]:
        note = "Prop odds missing on feed — TRAP kept using prior snapshot lines."
        status = "partial"
        return {**fresh, "trap_prop_note": note, "props_feed_status": status, "sticky_trap": True}

    if prev_trap:
        note = "Prop odds missing on feed — TRAP held from prior run (confidence stable)."
        status = "held"
        return {
            "is_trap": True,
            "trap_type": prev_type or fresh.get("trap_type"),
            "is_death_sentence": bool(prev_pitcher.get("is_death_sentence"))
            if prev_pitcher
            else fresh["is_death_sentence"],
            "trap_prop_note": note,
            "props_feed_status": status,
            "sticky_trap": True,
        }

    if merged:
        status = "partial"
    return {**fresh, "trap_prop_note": note, "props_feed_status": status, "sticky_trap": sticky_trap}
