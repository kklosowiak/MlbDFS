"""CONF v13 — decision-layer scoring (decoupled from OMEGA rank)."""

from __future__ import annotations

import re
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
    if t.get("prop_pressure_elite") or t.get("prop_pressure_label") == LABEL_HOT:
        signals += 1
    # New tactical GPP signals count as high conviction anchors!
    if t.get("is_anti_chalk_smash"):
        signals += 1
    if t.get("is_pitch_alignment"):
        signals += 1
    
    # Gassed Bullpen Attack counts as high conviction anchor
    opp_outs = float(t.get("opp_pitcher_outs", 18.0) or 18.0)
    if t.get("is_gassed") and opp_outs <= 15.5:
        signals += 1
        
    opp_trap = False
    return signals >= 2, opp_trap


def parse_weather(label):
    """
    Parses weather label string (e.g., '🟢 75° / In from Center') into:
    (status: str, temp: int, wind_dir: str, wind_speed: int)
    """
    if not label:
        return "Neutral", 70, "Neutral", 0

    status = "Neutral"
    if "🔴" in label:
        status = "Red"
    elif "🟠" in label:
        status = "Orange"
    elif "🟡" in label:
        status = "Yellow"

    temp = 70
    temp_match = re.search(r'(\d+)°', label)
    if temp_match:
        temp = int(temp_match.group(1))

    wind_dir = "Neutral"
    if "Out" in label:
        wind_dir = "Out"
    elif "In" in label:
        wind_dir = "In"

    wind_speed = 0
    speed_match = re.search(r'(\d+)mph', label)
    if speed_match:
        wind_speed = int(speed_match.group(1))

    return status, temp, wind_dir, wind_speed


def score_stack_confidence(t, p_reports):
    conf = 50.0
    reasons = []

    # 1. xwOBA (Physics)
    xwoba = float(t.get("team_xwoba", 0) or 0)
    if xwoba >= 0.340:
        conf += 18.0
        reasons.append(f"Elite team physics (.{str(xwoba)[2:5]} xwOBA).")
    elif xwoba >= 0.320:
        conf += 12.0
        reasons.append(f"Strong team physics (.{str(xwoba)[2:5]} xwOBA).")
    elif xwoba < 0.290:
        conf -= 15.0
        reasons.append(f"Weak team physics (.{str(xwoba)[2:5]} xwOBA).")

    if t.get("is_physics_override"):
        conf += 12.0
        reasons.append("PHY OVERRIDE: market undervalues true hitting ceiling.")

    if t.get("is_burst"):
        conf += 8.0
        reasons.append("BURST: star-heavy lineup with exploitable SP or pen.")
    if t.get("is_blind_spot"):
        conf += 10.0
        reasons.append("BLIND SPOT: physics far ahead of market pillar.")

    if t.get("is_shark") or t.get("is_whale") or t.get("is_sharp"):
        conf += 12.0
        reasons.append("Sharp / institutional interest on this side.")

    # 2. Divergence (Sharp money vs Public tickets)
    div = float(t.get("divergence", 0) or 0)
    if div >= 15:
        conf += 10.0
        reasons.append(f"Strong positive divergence ({div:+.0f}%).")
    elif div >= 8:
        conf += 1.0
    elif div <= -12:
        conf -= 10.0
        reasons.append(f"Sharp ticket fade on this team ({div:+.0f}%).")
    elif div <= -6:
        conf -= 8.0

    # 3. Game Total Signals
    ts = (t.get("total_signal") or "").upper()
    if "U-DIV" in ts:
        conf -= 10.0
        reasons.append("Game total under steam — run ceiling risk.")
    elif "O-DIV" in ts or "OVER" in ts:
        conf += 4.0

    # 4. Vegas Implied Run Total Brackets
    itt = float(t.get("implied_total", 4.5) or 4.5)
    if itt >= 5.0:
        conf += 8.0
        reasons.append(f"High implied run total ({itt:.1f} runs).")
    elif itt >= 4.4:
        conf += 4.0
        reasons.append(f"Solid implied run total ({itt:.1f} runs).")
    elif itt < 3.8:
        conf -= 10.0
        reasons.append(f"Low implied run total ({itt:.1f} runs) — ceiling capped.")
    elif itt < 3.3:
        conf -= 18.0
        reasons.append(f"Extremely low implied run total ({itt:.1f} runs).")

    # 5. DQI Status
    dqi_status = t.get("dqi_status")
    if dqi_status == "TRUST":
        conf += 10.0
        reasons.append(f"DQI TRUST ({t.get('dqi_score')}%).")
    elif dqi_status == "CAUTION":
        conf += 0.0
        reasons.append(f"DQI CAUTION ({t.get('dqi_score')}%).")
    elif dqi_status == "FADE":
        conf -= 15.0
        reasons.append(f"DQI FADE ({t.get('dqi_score')}%).")

    if t.get("is_trap"):
        conf -= 24.0
        reasons.append("CHALK TRAP: market loves this stack more than model.")

    # 6. Lineup Status
    lineup = t.get("lineup_status") or ""
    if lineup == "CONFIRMED":
        conf += 3.0
        reasons.append("Confirmed lineup — projection stable.")
    elif lineup == "PROJECTED":
        conf -= 7.0
        reasons.append("Projected lineup — higher uncertainty.")

    if t.get("is_volatile"):
        conf -= 12.0
        reasons.append("VOLATILE CONF today (≥15 pt swing) — verify before locking.")
    elif t.get("team_xwoba_dampened"):
        reasons.append("xwOBA held steady on confirmed lineup (minor refresh).")

    # 7. Weather & Umpire (Hitter Stacks)
    w_label = t.get("weather_label", "")
    if w_label:
        w_status, w_temp, w_wind_dir, w_wind_speed = parse_weather(w_label)
        if w_status == "Red":
            conf -= 25.0
            reasons.append("WEATHER POSTPONEMENT RISK: Red warning.")
        elif w_status == "Orange":
            conf -= 12.0
            reasons.append("WEATHER DELAY RISK: Orange warning.")
        
        # Temp boost only applies to outdoor environments
        if w_temp >= 80 and "Indoor" not in w_label:
            conf += 11.0
            reasons.append(f"High temperature boost ({w_temp}°F).")
        
        if w_wind_dir == "Out" and w_wind_speed >= 10:
            conf += 7.0
            reasons.append(f"Hitter-friendly wind blowing out ({w_wind_speed} mph).")
        elif w_wind_dir == "In" and w_wind_speed >= 10:
            conf -= 3.0
            reasons.append(f"Wind blowing in ({w_wind_speed} mph) — dampens power.")

    ump_f = float(t.get("umpire_factor", 1.0) or 1.0)
    if ump_f >= 1.04:
        conf += 5.0
        reasons.append(f"Hitter-friendly umpire assigned ({t.get('umpire_name', 'Unknown')}).")
    elif ump_f <= 0.96:
        conf -= 5.0
        reasons.append(f"Pitcher-friendly umpire assigned ({t.get('umpire_name', 'Unknown')}).")

    # 8. Slate Momentum Index (MSMI)
    if t.get("is_cold_streak_msmi") or t.get("is_cold_streak"):
        conf -= 18.0
        reasons.append("Team Slate Slump (MSMI): Elevated rolling K% surge & OPS drop.")
    elif t.get("is_hot_run_msmi") or t.get("is_hot_run"):
        conf += 8.0
        reasons.append("Team Hot Run (MSMI): Surging rolling OPS & reduced K%.")

    # 9. Tactical GPP Injections
    if t.get("is_anti_chalk_smash"):
        conf += 8.0
        reasons.append("⚓ ANTI-CHALK SMASH: Elite SP matchup vulnerability provides massive slate leverage.")

    if t.get("is_pitch_alignment"):
        conf += 8.0
        reasons.append("🎯 PITCH ALIGNMENT: 60%+ of starting lineup matches opposing SP's top 2 weapons.")

    # 10. GPP Leverage Fade Risk
    if t.get("is_fade_risk"):
        conf -= 17.0
        reasons.append("⚠️ GPP FADE RISK: High implied total backed by public but faded by sharps (-17).")

    # 11. Matchup Pitching Boosts (Capped to avoid double-counting)
    opp_p_name = t.get("opp_pitcher")
    opp_p = next((p for p in p_reports if p.get("pitcher") == opp_p_name), None)
    
    sp_boost = 0
    sp_reasons = []
    if opp_p:
        if opp_p.get("is_trap"):
            sp_boost += 16.0
            sp_reasons.append(f"Attacking TRAP SP {opp_p_name}.")
            if opp_p.get("trap_prop_note"):
                sp_reasons.append(opp_p["trap_prop_note"])
        if opp_p.get("form_status") == "COLD":
            sp_boost += 12.0
            sp_reasons.append(f"Attacking cold SP {opp_p_name} ({opp_p.get('recent_era')} ERA L3).")
        if opp_p.get("sharp_fade") and not opp_p.get("is_trap"):
            sp_boost += 6.0
            sp_reasons.append(f"Opposing SP sharp fade ({opp_p_name}) — stack-friendly caution arm.")
        
        # Tough SP penalty
        phys = float(opp_p.get("physics_score", 0) or 0)
        if isinstance(opp_p.get("alpha_score"), dict):
            alpha = opp_p["alpha_score"]
            if isinstance(alpha, dict):
                phys = max(phys, float(alpha.get("physics", 0) or 0))
            else:
                phys = max(phys, float(alpha or 0))
        if phys >= 22 and not opp_p.get("is_trap"):
            bp_fatigue = float(t.get("bullpen_fatigue", 0) or 0)
            if bp_fatigue >= 90 or t.get("is_gassed"):
                conf -= 9.0
                reasons.append(f"Tough SP underlying profile ({opp_p_name}), but opponent bullpen is exhausted.")
            else:
                conf -= 24.0
                reasons.append(f"Tough SP underlying profile ({opp_p_name}).")

    if sp_boost > 0:
        capped_sp_boost = min(20.0, sp_boost)
        conf += capped_sp_boost
        if capped_sp_boost < sp_boost:
            reasons.append(f"SP Matchup Boost capped at +20: {', '.join(sp_reasons)}.")
        else:
            reasons.extend(sp_reasons)

    # Bullpen Matchup Boost (Capped to avoid double-counting)
    bp_boost = 0
    bp_reasons = []
    bp_fatigue = float(t.get("bullpen_fatigue", 0) or 0)
    
    if bp_fatigue >= 85 or t.get("is_gassed"):
        bp_boost += 14.0
        bp_reasons.append("Opposing pen exhausted — late-inning ceiling.")
        
    opp_outs = float(t.get("opp_pitcher_outs", 18.0) or 18.0)
    if t.get("is_gassed") and opp_outs <= 15.5:
        bp_boost += 12.0
        bp_reasons.append("GASSED BULLPEN ATTACK: Attacking fatigued bullpen behind short-leash starter (+12).")

    if bp_boost > 0:
        capped_bp_boost = min(15.0, bp_boost)
        conf += capped_bp_boost
        if capped_bp_boost < bp_boost:
            reasons.append(f"Bullpen Attack Boost capped at +15: {', '.join(bp_reasons)}.")
        else:
            reasons.extend(bp_reasons)

    # 12. Props Board Pressure
    plabel = t.get("prop_pressure_label")
    pscore = int(t.get("prop_pressure_score", 0) or 0)
    if t.get("prop_pressure_elite") and plabel == LABEL_HOT:
        conf += 8.0
        names = ", ".join((t.get("prop_pressure_hitters") or [])[:3])
        reasons.append(
            f"Elite prop board ({pscore}, {t.get('prop_target_count', 0)} TARGET) — {names or 'lineup'}."
        )
    elif plabel == LABEL_WARM:
        conf += 4.0
        reasons.append(f"Moderate prop interest ({pscore}, WARM) — secondary board signal.")
    elif plabel == LABEL_COLD and xwoba >= 0.335:
        conf -= 10.0
        reasons.append("Elite xwOBA but cold prop board — market not agreeing.")

    if not reasons:
        reasons.append("Neutral stack profile on this slate.")

    # High Conviction Gate Check
    # (Require 2+ signals to exceed 82 CONF)
    raw_conf = conf
    if conf > 80:
        x = conf - 80
        conf = 80.0 + (20.0 * x) / (x + 12.0)

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

    # 1. Form Status
    if p.get("form_status") == "SURGING":
        conf += 15
        reasons.append(
            f"SURGING form ({p.get('recent_k9')} K/9, {p.get('recent_era')} ERA L3)."
        )
    elif p.get("form_status") == "COLD":
        conf -= 20
        reasons.append(f"COLD form ({p.get('recent_era')} ERA L3).")

    # 2. Physics Score (SIERA/xERA based)
    siera = float(p.get("physics_score", 0) or 0)
    if isinstance(p.get("alpha_score"), dict):
        siera = max(siera, float(p["alpha_score"].get("physics", 0) or 0))
    if siera >= 20:
        conf += 14
        reasons.append(f"Strong underlying physics ({siera:.1f}).")
    elif siera < 10:
        conf -= 14
        reasons.append(f"Weak underlying physics ({siera:.1f}).")

    # 3. Market Traps and Fades
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

    # 4. Prop Line Juice
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

    # 5. K Line Steam
    k_move = float(p.get("k_move", 0) or 0)
    if k_move >= 0.5:
        conf += 6
        reasons.append(f"K line steamed up (+{k_move:.1f}).")
    elif k_move <= -0.5:
        conf -= 5

    # 6. Opponent Matchup (xwOBA, Props, Pitch Alignment, Weather & Umpire)
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
            
        n_tgt = int(opp_t.get("prop_target_count", 0) or 0)
        n_st = int(opp_t.get("prop_stack_target_count", 0) or 0)
        if opp_t.get("prop_pressure_elite") and (n_tgt >= 3 or (n_tgt >= 2 and n_st >= 2)):
            conf -= 6
            reasons.append(
                f"{opp} elite prop board ({n_tgt} TARGET, {n_st} runs/RBI TARGET) — run risk."
            )
        if opp_t.get("is_pitch_alignment"):
            conf -= 10
            reasons.append("Tough matchup: Opposing lineup has elite pitch-type alignment against SP's top weapons.")

        # Weather & Umpire integrations for Pitcher
        w_label = opp_t.get("weather_label", "")
        if w_label:
            w_status, w_temp, w_wind_dir, w_wind_speed = parse_weather(w_label)
            if w_status == "Red":
                conf -= 35
                reasons.append("WEATHER POSTPONEMENT RISK: Red warning.")
            elif w_status == "Orange":
                conf -= 20
                reasons.append("WEATHER DELAY RISK: Orange warning (starting pitcher short hook risk).")
            elif w_status == "Yellow":
                conf -= 8
                reasons.append("WEATHER WARNING: Yellow status.")
            
            if w_temp >= 80 and "Indoor" not in w_label:
                conf -= 5
                reasons.append(f"Weather temperature drag ({w_temp}°F).")
                
            if w_wind_dir == "Out" and w_wind_speed >= 10:
                conf -= 6
                reasons.append(f"Weather wind blowing out ({w_wind_speed} mph) — HR risk.")
            elif w_wind_dir == "In" and w_wind_speed >= 10:
                conf += 6
                reasons.append(f"Weather wind blowing in ({w_wind_speed} mph) — power dampener.")

        ump_f = float(opp_t.get("umpire_factor", 1.0) or 1.0)
        if ump_f >= 1.04:
            conf -= 6
            reasons.append(f"Hitter-friendly umpire assigned ({opp_t.get('umpire_name', 'Unknown')}).")
        elif ump_f <= 0.96:
            conf += 6
            reasons.append(f"Pitcher-friendly umpire assigned ({opp_t.get('umpire_name', 'Unknown')}).")

    # 7. Sharp Money Backing
    if p.get("is_sharp") or p.get("is_shark") or p.get("is_whale"):
        conf += 10
        reasons.append("Sharp money backing this pitcher.")

    # 8. Intraday Volatility
    if p.get("is_volatile"):
        conf -= 8
        reasons.append("VOLATILE CONF intraday — re-check before lock.")

    if not reasons:
        reasons.append("Neutral pitcher profile.")

    # Apply Asymptotic Compression for raw scores > 80
    raw_conf = conf
    if conf > 80:
        x = conf - 80
        conf = 80.0 + (20.0 * x) / (x + 12.0)

    return _clamp(conf), reasons
