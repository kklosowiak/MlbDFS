"""CONF v11 — decision-layer scoring (decoupled from OMEGA rank)."""

from __future__ import annotations

from utils.team_prop_pressure import LABEL_COLD, LABEL_HOT, LABEL_WARM


def _clamp(conf):
    return max(0, min(100, int(round(conf))))


def _has_high_conviction_stack(t):
    """Need 2+ quality signals for CONF >= 85."""
    signals = 0
    if t.get("dqi_status") == "TRUST":
        signals += 1
    if float(t.get("divergence", 0) or 0) >= 10:
        signals += 1
    if t.get("bullpen_fatigue", 0) >= 85 or t.get("is_gassed"):
        signals += 1
    if t.get("prop_pressure_label") in (LABEL_HOT, LABEL_WARM):
        signals += 1
    opp_trap = False
    return signals >= 2, opp_trap


def score_stack_confidence(t, p_reports):
    conf = 50.0
    reasons = []

    xwoba = float(t.get("team_xwoba", 0) or 0)
    if xwoba >= 0.340:
        conf += 22
        reasons.append(f"Elite team physics (.{str(xwoba)[2:5]} xwOBA).")
    elif xwoba >= 0.320:
        conf += 14
        reasons.append(f"Strong team physics (.{str(xwoba)[2:5]} xwOBA).")
    elif xwoba < 0.290:
        conf -= 15
        reasons.append(f"Weak team physics (.{str(xwoba)[2:5]} xwOBA).")

    if t.get("is_physics_override"):
        conf += 12
        reasons.append("PHY OVERRIDE: market undervalues true hitting ceiling.")

    if t.get("is_burst"):
        conf += 8
        reasons.append("BURST: star-heavy lineup with exploitable SP or pen.")
    if t.get("is_blind_spot"):
        conf += 10
        reasons.append("BLIND SPOT: physics far ahead of market pillar.")

    if t.get("is_shark") or t.get("is_whale") or t.get("is_sharp"):
        conf += 12
        reasons.append("Sharp / institutional interest on this side.")

    div = float(t.get("divergence", 0) or 0)
    if div >= 15:
        conf += 10
        reasons.append(f"Strong positive divergence ({div:+.0f}%).")
    elif div >= 8:
        conf += 5
    elif div <= -12:
        conf -= 12
        reasons.append(f"Sharp ticket fade on this team ({div:+.0f}%).")
    elif div <= -6:
        conf -= 6

    ts = (t.get("total_signal") or "").upper()
    if "U-DIV" in ts:
        conf -= 10
        reasons.append("Game total under steam — run ceiling risk.")
    elif "O-DIV" in ts or "OVER" in ts:
        conf += 5

    dqi_status = t.get("dqi_status")
    if dqi_status == "TRUST":
        conf += 10
        reasons.append(f"DQI TRUST ({t.get('dqi_score')}%).")
    elif dqi_status == "CAUTION":
        conf += 0
        reasons.append(f"DQI CAUTION ({t.get('dqi_score')}%).")
    elif dqi_status == "FADE":
        conf -= 15
        reasons.append(f"DQI FADE ({t.get('dqi_score')}%).")

    if t.get("is_trap"):
        conf -= 20
        reasons.append("CHALK TRAP: market loves this stack more than model.")

    lineup = t.get("lineup_status") or ""
    if lineup == "CONFIRMED":
        conf += 5
        reasons.append("Confirmed lineup — projection stable.")
    elif lineup == "PROJECTED":
        conf -= 5
        reasons.append("Projected lineup — higher uncertainty.")

    if t.get("is_volatile"):
        conf -= 10
        reasons.append("VOLATILE CONF today (≥15 pt swing) — verify before locking.")
    elif t.get("team_xwoba_dampened"):
        reasons.append("xwOBA held steady on confirmed lineup (minor refresh).")

    if t.get("is_cold_streak"):
        conf -= 8
        reasons.append("Team cold streak (elevated K% recently).")

    opp_p_name = t.get("opp_pitcher")
    opp_p = next((p for p in p_reports if p.get("pitcher") == opp_p_name), None)
    if opp_p:
        if opp_p.get("is_trap"):
            conf += 14
            reasons.append(f"Attacking TRAP SP {opp_p_name}.")
            if opp_p.get("trap_prop_note"):
                reasons.append(opp_p["trap_prop_note"])
        if opp_p.get("form_status") == "COLD":
            conf += 12
            reasons.append(f"Attacking cold SP {opp_p_name} ({opp_p.get('recent_era')} ERA L3).")
        if opp_p.get("sharp_fade") and not opp_p.get("is_trap"):
            conf += 6
            reasons.append(f"Opposing SP sharp fade ({opp_p_name}) — stack-friendly caution arm.")
        phys = float(opp_p.get("physics_score", 0) or 0)
        if isinstance(opp_p.get("alpha_score"), dict):
            alpha = opp_p["alpha_score"]
            if isinstance(alpha, dict):
                phys = max(phys, float(alpha.get("physics", 0) or 0))
            else:
                phys = max(phys, float(alpha or 0))
        if phys >= 22 and not opp_p.get("is_trap"):
            conf -= 18
            reasons.append(f"Tough SP underlying profile ({opp_p_name}).")

    bp = t.get("bullpen_fatigue", 0) or 0
    if bp >= 85 or t.get("is_gassed"):
        conf += 10
        reasons.append("Opposing pen exhausted — late-inning ceiling.")

    plabel = t.get("prop_pressure_label")
    pscore = int(t.get("prop_pressure_score", 0) or 0)
    if plabel == LABEL_HOT:
        conf += 12
        names = ", ".join((t.get("prop_pressure_hitters") or [])[:3])
        reasons.append(f"PROP PRESSURE HOT ({pscore}) — {names or 'lineup juiced'}.")
    elif plabel == LABEL_WARM:
        conf += 7
        reasons.append(f"PROP PRESSURE WARM ({pscore}) — books active on lineup.")
    elif plabel == LABEL_COLD and xwoba >= 0.335:
        conf -= 10
        reasons.append("Elite xwOBA but cold prop board — market not agreeing.")

    if not reasons:
        reasons.append("Neutral stack profile on this slate.")

    conf = _clamp(conf)
    if conf >= 85:
        ok, _ = _has_high_conviction_stack(t)
        if not ok:
            conf = min(conf, 82)
            reasons.append("Capped below 85 — need 2+ conviction signals (DQI/div/pen/props).")

    return conf, reasons


def score_pitcher_confidence(p, t_reports):
    conf = 50.0
    reasons = []

    if p.get("form_status") == "SURGING":
        conf += 15
        reasons.append(
            f"SURGING form ({p.get('recent_k9')} K/9, {p.get('recent_era')} ERA L3)."
        )
    elif p.get("form_status") == "COLD":
        conf -= 20
        reasons.append(f"COLD form ({p.get('recent_era')} ERA L3).")

    siera = float(p.get("physics_score", 0) or 0)
    if isinstance(p.get("alpha_score"), dict):
        siera = max(siera, float(p["alpha_score"].get("physics", 0) or 0))
    if siera >= 20:
        conf += 14
        reasons.append(f"Strong underlying physics ({siera:.1f}).")
    elif siera < 10:
        conf -= 14
        reasons.append(f"Weak underlying physics ({siera:.1f}).")

    if p.get("is_trap"):
        conf -= 30
        reasons.append(f"TRAP SP ({p.get('trap_type') or 'Vegas fade'}).")
    elif p.get("sharp_fade"):
        div = int(p.get("divergence", 0) or 0)
        conf -= 12
        reasons.append(f"Sharp fade ({div:+d}% div) — caution, not prop TRAP.")
        opp = p.get("opponent")
        opp_t = next((t for t in t_reports if t.get("team") == opp), None)
        if p.get("form_status") == "SURGING" and opp_t and float(opp_t.get("team_xwoba", 0.35) or 0) < 0.310:
            conf += 5
            reasons.append("Form + soft opponent offset part of fade.")
    if p.get("is_paradox"):
        conf -= 22
        reasons.append("PARADOX: elite offense opponent — pick a side.")
    if p.get("is_hazard"):
        conf -= 12
        reasons.append("HAZARD: top-slate opposing offense.")

    if p.get("is_juiced_target"):
        conf += 8
        reasons.append("K prop TARGET — strict juiced Over vs Under.")
    elif p.get("is_prop_juice"):
        conf += 4
        reasons.append("K prop JUICE on board.")

    if p.get("is_hits_allowed_juice"):
        conf -= 8
        reasons.append("Hits-allowed prop juiced Over — run risk priced in.")

    if p.get("is_low_ceiling"):
        conf -= 8
        reasons.append("Low K ceiling on props.")

    k_move = float(p.get("k_move", 0) or 0)
    if k_move >= 0.5:
        conf += 6
        reasons.append(f"K line steamed up (+{k_move:.1f}).")
    elif k_move <= -0.5:
        conf -= 5

    opp = p.get("opponent")
    opp_t = next((t for t in t_reports if t.get("team") == opp), None)
    if opp_t:
        oxw = float(opp_t.get("team_xwoba", 0.33) or 0.33)
        if oxw >= 0.340:
            conf -= 14
            reasons.append(f"Tough matchup: {opp} elite lineup xwOBA (.{str(oxw)[2:5]}).")
        elif oxw < 0.300:
            conf += 12
            reasons.append(f"Soft matchup: {opp} weak lineup xwOBA.")
        if opp_t.get("prop_pressure_label") == LABEL_HOT:
            conf -= 8
            reasons.append(f"{opp} lineup has HOT prop pressure — run environment risk.")

    if p.get("is_sharp") or p.get("is_shark") or p.get("is_whale"):
        conf += 10
        reasons.append("Sharp money backing this pitcher.")

    if p.get("is_volatile"):
        conf -= 8
        reasons.append("VOLATILE CONF intraday — re-check before lock.")

    if not reasons:
        reasons.append("Neutral pitcher profile.")

    return _clamp(conf), reasons
