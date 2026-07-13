"""CONF v13 — decision-layer scoring (decoupled from OMEGA rank)."""

from __future__ import annotations

import json
import os
import re

from config import config
from utils.team_prop_pressure import LABEL_COLD, LABEL_HOT, LABEL_WARM


def load_weights() -> dict:
    """Load model signal weights from data/weights.json (falls back to hardcoded defaults)."""
    weights_path = os.path.join(config.DATA_DIR, "weights.json")
    if os.path.exists(weights_path):
        try:
            with open(weights_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    # Fallback to defaults
    return {
        "stacks": {
            "is_sharp": 12.0,
            "is_trap": -24.0,
            "is_burst": 12.0,
            "is_gassed": 14.0,
            "is_hot_run_msmi": 12.0,
            "is_cold_streak_msmi": -24.0
        },
        "pitchers": {
            "is_trap": -24.0,
            "true_talent_penalty": -12.0,
            "is_sharp": 10.0,
            "is_shark": 10.0,
            "early_innings_volatility": -10.0
        }
    }


def _clamp(conf):
    return max(0, min(100, int(round(conf))))


def _has_high_conviction_stack(t):
    """Need 2+ quality signals for CONF >= 85."""
    signals = 0
    if t.get("dqi_status") == "TRUST":
        signals += 1
    if float(t.get("divergence", 0) or 0) >= 10:
        signals += 1
    # Bullpen/leash status counts as at most 1 signal to avoid double-counting
    opp_outs = float(t.get("opp_pitcher_outs", 18.0) or 18.0)
    if t.get("is_gassed") and opp_outs <= 15.5:
        signals += 1
    elif t.get("bullpen_fatigue", 0) >= 85 or t.get("is_gassed"):
        signals += 1

    # Prop pressure label no longer influences high conviction stack triggers (retired)
    # New tactical GPP signals count as high conviction anchors!
    if t.get("is_anti_chalk_smash"):
        signals += 1
    if t.get("is_pitch_alignment"):
        signals += 1

    # Matchup conviction signals
    if float(t.get("implied_total", 4.5) or 4.5) >= 5.0:
        signals += 1
    if t.get("is_true_talent_penalty") or t.get("is_trap"):
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
    # Load signal weights from config so future tuning of weights.json takes effect
    _sw = load_weights().get("stacks", {})

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

    if t.get("is_burst"):
        conf += float(_sw.get("is_burst", 12.0))
        reasons.append("BURST: star-heavy lineup with exploitable SP or pen.")

    # OMEGA v17.2: is_shark REMOVED from stack confidence (+12 CONF)
    # Backtest shows -25pp below baseline when applied to team run scoring.
    # is_sharp retains the boost (institutionally validated).
    if t.get("is_sharp"):
        conf += float(_sw.get("is_sharp", 12.0))
        reasons.append("Sharp / institutional interest on this side.")

    # 2. Divergence (Sharp money vs Public tickets - GPP calibrated v16.1)
    div = float(t.get("divergence", 0) or 0)
    dqi_status = t.get("dqi_status")
    
    if div <= -20:
        conf += 10.0
        reasons.append(f"Institutional GPP leverage: Heavy public fade ({div:+.0f}% div).")
    elif div <= -12:
        conf += 6.0
        reasons.append(f"Under-the-radar GPP leverage: Public fade ({div:+.0f}% div).")
    elif div >= 10 and div < 20 and dqi_status != "TRUST":
        # Steam trap penalty - sharps betting win probability, not run-scoring ceiling
        conf -= 8.0
        reasons.append(f"Public/ML steam trap: Divergence ({div:+.0f}% div) drags run ceiling.")

    # Public Steam Trap Penalty
    if t.get("is_public_steam_trap"):
        conf -= 8.0
        reasons.append("🚨 PUBLIC STEAM TRAP: Retail total steamed up but sharp bookmakers held steady (-8).")

    # Implied Total Velocity (Sharp total movement close to lock)
    vel_dir = t.get("sharp_velocity_direction", 0)
    if vel_dir == 1:
        conf += 4.0
        reasons.append("⚡ SHARP TOTAL STEAM BOOST: Late sharp total movement pushes run ceiling higher (+4).")
    elif vel_dir == -1:
        conf -= 6.0
        reasons.append("📉 SHARP TOTAL STEAM FADE: Late sharp total movement drags run ceiling lower (-6).")

    # 3. Game Total Signals
    ts = (t.get("total_signal") or "").upper()
    if "U-DIV" in ts:
        conf -= 10.0
        reasons.append("Game total under steam — run ceiling risk.")
    elif "O-DIV" in ts or "OVER" in ts:
        conf += 4.0

    # 4. Vegas Implied Run Total Brackets
    # Calibrated on 12,526 team slots / 440 dates / 3 seasons (2024-2026)
    # Baseline: 4.358 avg runs. Real jump at 4.8, elite tier at 5.5+
    itt = float(t.get("implied_total", 4.5) or 4.5)
    if itt >= 5.5:
        conf += 10.0
        reasons.append(f"ELITE implied run total ({itt:.1f}) — 6.62 avg runs historically.")
    elif itt >= 4.8:
        conf += 10.0
        reasons.append(f"High implied run total ({itt:.1f} runs) — strong run environment.")
    elif itt >= 4.5:
        conf += 6.0
        reasons.append(f"Solid implied run total ({itt:.1f} runs).")
    elif itt >= 4.0:
        conf += 0.0
        # ITT 4.0-4.5 is barely above baseline — neutral, no bonus or penalty
        reasons.append(f"Average implied run total ({itt:.1f} runs).")
    elif itt >= 3.8:
        conf -= 8.0
        reasons.append(f"Below-average implied run total ({itt:.1f} runs) — ceiling limited.")
    elif itt >= 3.5:
        conf -= 8.0
        reasons.append(f"Low implied run total ({itt:.1f} runs) — ceiling capped.")
    else:
        conf -= 8.0
        reasons.append(f"Very low implied run total ({itt:.1f} runs) — avoid stacking.")

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
        num_games = len(p_reports) // 2 if p_reports else 15
        if num_games <= 0:
            num_games = 15
        dampener = min(1.0, num_games / 15.0)
        base_trap_penalty = abs(float(_sw.get("is_trap", -24.0)))
        scaled_penalty = max(8.0, base_trap_penalty * dampener)
        conf -= scaled_penalty
        reasons.append("CHALK TRAP: market loves this stack more than model.")

    # 6. Lineup Status
    lineup = t.get("lineup_status") or ""
    if lineup == "CONFIRMED":
        conf += 3.0
        reasons.append("Confirmed lineup — projection stable.")
    elif lineup == "PROJECTED_HIGH_CONF":
        conf -= 2.0
        reasons.append("Projected lineup (High Conf) — consensus validated.")
    elif lineup == "PROJECTED_LOW_CONF":
        conf -= 8.0
        reasons.append("Projected lineup (Low Conf) — scraper disagreement penalty (-8).")
    elif lineup == "PROJECTED" or lineup == "ROSTER FALLBACK":
        conf -= 7.0
        reasons.append(f"Projected/Fallback lineup ({lineup}) — higher uncertainty.")

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
        # OMEGA v13.6.1: Optimized Team Slate Slump penalty
        conf -= abs(float(_sw.get("is_cold_streak_msmi", -24.0)))
        reasons.append("Team Slate Slump (MSMI): Elevated rolling K% surge & OPS drop.")
    elif t.get("is_hot_run_msmi") or t.get("is_hot_run"):
        # OMEGA v13.6.1: Optimized Team Hot Run boost
        conf += float(_sw.get("is_hot_run_msmi", 12.0))
        reasons.append("Team Hot Run (MSMI): Surging rolling OPS & reduced K%.")

    # 9. Tactical GPP Injections
    # OMEGA v19.3: ANTI_CHALK_SMASH suppressed when team is in a cold streak.
    # A team with elevated rolling K% / OPS drop is not a contrarian leverage spot.
    if t.get("is_anti_chalk_smash") and not (t.get("is_cold_streak_msmi") or t.get("is_cold_streak")):
        conf += 8.0
        reasons.append("ANTI-CHALK SMASH: Elite SP matchup vulnerability provides massive slate leverage.")

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
        if opp_p.get("form_status") == "COLD" and xwoba >= 0.305:
            # OMEGA v17.1 (Fix 5 — xwOBA gate): only boost stacks with a real offense behind them
            # Prevents weak-hitting teams from getting the cold SP bonus they can't capitalize on
            sp_boost += 12.0
            sp_reasons.append(f"Attacking cold SP {opp_p_name} ({opp_p.get('recent_era')} ERA L3).")
        elif opp_p.get("form_status") == "COLD" and xwoba < 0.305:
            sp_reasons.append(f"Cold SP {opp_p_name} noted but offense too weak to boost ({xwoba:.3f} xwOBA < .305).")
        if opp_p.get("sharp_fade") and not opp_p.get("is_trap"):
            sp_boost += 6.0
            sp_reasons.append(f"Opposing SP sharp fade ({opp_p_name}) — stack-friendly caution arm.")

        # OMEGA v13.7: LOW_CEILING boost — backtested at +5.8pp over baseline (41.8% vs 36.0%)
        # Standalone HAZARD excluded — backtest showed 15.4% hit rate, below baseline
        if opp_p.get("is_low_ceiling"):
            sp_boost += 6.0
            sp_reasons.append(f"Opp SP {opp_p_name} flagged LOW CEILING (K-line ⩽4.0) — stack-friendly.")
            # Convergence bonus: both LOW_CEILING + HAZARD together hit at 50.0% (24 matchups)
            if opp_p.get("is_hazard"):
                sp_boost += 4.0
                sp_reasons.append(f"LOW CEILING + HAZARD convergence vs elite offense — +4 convergence.")

        # OMEGA v17.2: TRUE TALENT PENALTY stack boost
        # Backtested: opponents of TTP pitchers score ≥5 runs at 64.3% (n=28, vs 43.6% baseline, +20.7pp)
        # TTP = pitcher with K-BB% < 14% AND HR/9 > 1.6 AND IP >= 50 — can't miss bats, gets hit for power
        # Only boost legitimate offenses (xwOBA gate) to avoid inflating weak-lineup stacks
        if opp_p.get("true_talent_penalty") and xwoba >= 0.305:
            _pw = load_weights().get("pitchers", {})
            ttp_val = abs(float(_pw.get("true_talent_penalty", -15.0))) * 1.2
            sp_boost += ttp_val
            sp_reasons.append(
                f"🎯 TRUE TALENT PENALTY: {opp_p_name} can't miss bats (K-BB%<14%), "
                f"gives up power (HR/9>1.6), and has IP>=50 — elite stack spot (+{ttp_val:.1f})."
            )
        elif opp_p.get("true_talent_penalty") and xwoba < 0.305:
            sp_reasons.append(
                f"TTP noted vs {opp_p_name} but offense too weak to capitalize ({xwoba:.3f} xwOBA)."
            )
        
        # Tough SP penalty
        phys = float(opp_p.get("physics_score", 0) or 0)
        if isinstance(opp_p.get("alpha_score"), dict):
            alpha = opp_p["alpha_score"]
            if isinstance(alpha, dict):
                phys = max(phys, float(alpha.get("physics", 0) or 0))
            else:
                phys = max(phys, float(alpha or 0))
        if phys >= 20.0:
            # OMEGA v17.1 (Fix 2): Tiered Tough SP Penalty — physics-proportional, not flat
            # Tier 1: 20–35 physics = vulnerable arm (4+ ERA risk, walk risk, low CSW) → lighter penalty
            # Tier 2: 35–55 physics = solid mid-tier SP → moderate penalty
            # Tier 3: 55+ physics = true ace / front-line arm → full penalty
            # Backtest: 0 matchups penalized vs old rules across 184 June matchups
            p_mkt = float(opp_p.get("market_score", 0.0) or 0.0)
            p_conf = str(opp_p.get("confidence", "low")).lower()
            
            # Determine dampening factor based on data quality
            damp_factor = 1.0
            is_volatile = False
            volatility_reason = ""
            
            if p_conf in ("low", "med"):
                damp_factor = 0.0  # 100% dampening (eliminate penalty)
                is_volatile = True
                volatility_reason = "low-sample SP"
            elif p_mkt == 0.0:
                damp_factor = 0.5  # 50% dampening
                is_volatile = True
                volatility_reason = "unanchored market SP"

            # Physics-tiered base penalty
            if phys >= 55.0:
                base_penalty = 24.0   # True ace — full penalty
                tier_label = "ace-tier"
                bp_dampening_mult = 0.85  # Retain 85% of penalty vs. gassed pen
            elif phys >= 35.0:
                base_penalty = 16.0   # Solid arm — moderate penalty
                tier_label = "solid-tier"
                bp_dampening_mult = 0.65  # Retain 65% of penalty vs. gassed pen
            else:
                base_penalty = 8.0    # Vulnerable arm (20–35) — light penalty
                tier_label = "vulnerable-tier"
                bp_dampening_mult = 0.40  # Retain 40% of penalty vs. gassed pen

            bp_fatigue = float(t.get("bullpen_fatigue", 0) or 0)
            if bp_fatigue >= 90 or t.get("is_gassed"):
                penalty = base_penalty * bp_dampening_mult
                if is_volatile:
                    penalty *= damp_factor
                    reasons.append(f"Tough but volatile ({volatility_reason}) {tier_label} SP ({opp_p_name}), opponent pen exhausted.")
                else:
                    reasons.append(f"Tough {tier_label} SP profile ({opp_p_name}), but opponent bullpen is exhausted.")
            else:
                penalty = base_penalty
                if is_volatile:
                    penalty *= damp_factor
                    reasons.append(f"Tough but volatile ({volatility_reason}) {tier_label} SP ({opp_p_name}) — penalty dampened.")
                else:
                    reasons.append(f"Tough {tier_label} SP underlying profile ({opp_p_name}).")
            
            # Apply 50% scale if SP is a TRAP
            if opp_p.get("is_trap"):
                penalty *= 0.50
                reasons.append(f"Attacking TRAP SP ({opp_p_name}) — skill penalty scaled to 50%.")
            
            conf -= penalty

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
        # Load opposing bullpen quality
        opp_team = t.get("opponent")
        opp_bp_era = 3.90
        try:
            import os
            import json
            cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "bullpen_season_cache.json")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    bullpen_season = json.load(f)
                from utils.normalization import normalize_player_name
                norm_opp = normalize_player_name(opp_team)
                for team_key, data in bullpen_season.items():
                    if normalize_player_name(team_key) == norm_opp:
                        opp_bp_era = float(data.get("era", 3.90) or 3.90)
                        break
        except Exception:
            pass
            
        gassed_base = float(_sw.get("is_gassed", 14.0))
        if opp_bp_era < 3.50:
            val = round(gassed_base * (8.0 / 14.0), 1)
            bp_boost += val
            bp_reasons.append(f"Opposing elite pen fatigued (ERA: {opp_bp_era:.2f}) — moderate ceiling (+{val:.1f}).")
        elif opp_bp_era > 4.20:
            val = round(gassed_base * (19.0 / 14.0), 1)
            bp_boost += val
            bp_reasons.append(f"Opposing poor pen fatigued (ERA: {opp_bp_era:.2f}) — massive ceiling (+{val:.1f}).")
        else:
            bp_boost += gassed_base
            bp_reasons.append(f"Opposing pen exhausted — late-inning ceiling (+{gassed_base:.1f}).")
        
    opp_outs = float(t.get("opp_pitcher_outs", 18.0) or 18.0)
    if t.get("is_gassed") and opp_outs <= 15.5:
        bp_boost += 12.0
        bp_reasons.append("GASSED BULLPEN ATTACK: Attacking fatigued bullpen behind short-leash starter (+12).")

    if bp_boost > 0:
        capped_bp_boost = min(20.0, bp_boost)
        conf += capped_bp_boost
        if capped_bp_boost < bp_boost:
            reasons.append(f"Bullpen Attack Boost capped at +20: {', '.join(bp_reasons)}.")
        else:
            reasons.extend(bp_reasons)

    # 12. Props Board Pressure
    plabel = t.get("prop_pressure_label")
    pscore = int(t.get("prop_pressure_score", 0) or 0)
    # Informational only — prop pressure labels no longer influence stack confidence (retired)
    if plabel == LABEL_HOT:
        names = ", ".join((t.get("prop_pressure_hitters") or [])[:3])
        reasons.append(
            f"Elite prop board ({pscore}, {t.get('prop_target_count', 0)} TARGET) — {names or 'lineup'}."
        )
    elif plabel == LABEL_WARM:
        reasons.append(f"Moderate prop interest ({pscore}, WARM) — secondary board signal.")
    elif plabel == LABEL_COLD and xwoba >= 0.335:
        reasons.append("Elite xwOBA noted vs cold prop board.")

    if not reasons:
        reasons.append("Neutral stack profile on this slate.")

    # Check for short-leash, low-K trigger (Fix B / Trigger Def 3)
    three_flags_fire = False
    short_leash_enabled = bool(_sw.get("short_leash_soft_cap_enabled", True))
    if short_leash_enabled and opp_p:
        eiv_present = opp_p.get("early_innings_volatility", False)
        reasons_sp = opp_p.get("attack_reasons", []) or opp_p.get("reasons", []) or []
        for r in reasons_sp:
            if "Early-innings volatility" in r:
                eiv_present = True
        
        k_line = None
        k_line_raw = opp_p.get("k_line")
        if k_line_raw is not None and k_line_raw != '-':
            try:
                k_line = float(k_line_raw)
            except ValueError:
                pass
                
        if eiv_present and (k_line is not None and k_line <= 4.0):
            three_flags_fire = True
    # OMEGA v20.1: Change B - ANTI_CHALK ceiling in low run environment
    if t.get("is_anti_chalk_smash") and not (t.get("is_cold_streak_msmi") or t.get("is_cold_streak")):
        itt = float(t.get("implied_total", 4.5) or 4.5)
        if itt < 4.5 and conf > 80 and (conf - 8.0) <= 80:
            conf -= 3.0
            for i, r in enumerate(reasons):
                if "ANTI-CHALK SMASH" in r:
                    reasons[i] = "ANTI-CHALK SMASH: Elite SP matchup vulnerability provides massive slate leverage (capped to +5 CONF for ITT < 4.5)."
                    break

    # Same-side starter cap (Zack Wheeler effect)
    own_pitcher = next((p for p in p_reports if p.get("team") == t.get("team")), None)
    if own_pitcher and own_pitcher.get("attack_conf", 50.0) >= 85.0:
        conf -= 5.0
        reasons.append(f"Same-side starter elite warning ({own_pitcher['pitcher']} CONF {own_pitcher['attack_conf']}%): potential shortened game, capping stack ceiling.")

    # High Conviction Gate Check

    # (Require 2+ signals to exceed 75 CONF)
    raw_conf = conf
    if conf > 80:
        x = conf - 80
        conf = 80.0 + (20.0 * x) / (x + 12.0)

    conf = _clamp(conf)
    if conf >= 75:
        ok, _ = _has_high_conviction_stack(t)
        
        strict_soft_cap = False
        if three_flags_fire:
            spec_signals = 0
            if t.get("is_steam") or t.get("is_steam_support"):
                spec_signals += 1
            if t.get("dqi_status") == "TRUST":
                spec_signals += 1
            if t.get("is_gassed") or float(t.get("bullpen_fatigue", 0) or 0) >= 85:
                spec_signals += 1
                
            if spec_signals < 2:
                ok = False
                strict_soft_cap = True
        
        if not ok:
            if strict_soft_cap:
                conf = 75.0
                reasons.append("Soft-capped above 75 — short-leash SP requires 2+ of STEAM/DQI-TRUST/GASSED-PEN.")
            else:
                # Apply 0.35 soft-cap above 75 instead of a non-monotonic cap from 70
                conf = 75.0 + (conf - 75.0) * 0.35
                reasons.append("Soft-capped above 75 — need 2+ conviction signals (DQI/div/pen/props).")

    return _clamp(conf), reasons


def score_pitcher_confidence(p, t_reports):
    conf = 50.0
    reasons = []
    # Load signal weights from config so future tuning of weights.json takes effect
    _w = load_weights().get("pitchers", {})

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
        trap_penalty = abs(float(_w.get("is_trap", -30.0)))
        conf -= trap_penalty
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

    if p.get("is_volatile"):
        conf -= 4
        reasons.append("Volatile pregame signal movement (-4).")

    if p.get("is_low_ceiling"):
        conf -= 8
        reasons.append("Low K ceiling on props.")

    if p.get("is_volatile") and p.get("is_low_ceiling"):
        p["is_high_bust_risk"] = True
        reasons.append("Compound risk warning: volatile + low ceiling (is_high_bust_risk).")

    if p.get("is_outlier_driven"):
        conf -= 10
        ex_best = p.get("recent_era_ex_best", "-")
        reasons.append(f"Recent form driven by single outlier start (ex-best ERA: {ex_best}) (-10).")

    # OMEGA v21.2: Rolling ERA and walk rate decline penalties
    # OMEGA v21.3 (July 13): recent_era_5g blocks removed — dead code.
    #   recent_era_5g is None for all pitchers in production due to pitcher_form_cache.json
    #   coverage gap (cache only refreshes for today's slate, ~24 pitchers vs. full pool).
    #   Backlog item #3 in OMEGA_DECISIONS.md tracks the fix.
    # OMEGA v21.3 (July 13): siera_div penalty reduced -4 -> -2 (unvalidated judgment call;
    #   both regression runs show near-zero independent coefficient once L3 ERA is controlled).
    recent_era = p.get("recent_era")
    recent_bb9 = p.get("recent_bb9")
    siera = p.get("siera")

    if recent_era is not None and recent_era >= 4.50:
        conf -= 6
        reasons.append(f"Elevated L3 ERA ({recent_era:.2f}) (-6).")

    if siera is not None:
        siera_val = float(siera)
        if recent_era is not None and (recent_era - siera_val) >= 1.50:
            conf -= 2
            reasons.append(f"L3 ERA ({recent_era:.2f}) significantly exceeds SIERA ({siera_val:.2f}) (-2).")

    if recent_bb9 is not None and recent_bb9 >= 4.5:
        conf -= 6
        reasons.append(f"Control crisis: elevated L3 BB/9 ({recent_bb9:.2f}) (-6).")

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
        # Elite prop board no longer penalizes pitcher confidence (retired)
        if opp_t.get("prop_pressure_label") == LABEL_HOT and (n_tgt >= 3 or (n_tgt >= 2 and n_st >= 2)):
            reasons.append(
                f"{opp} elite prop board ({n_tgt} TARGET, {n_st} runs/RBI TARGET) noted."
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
                conf -= 7
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

    # 7. Game Total Environment — SP Modifier
    # Calibrated on 11,683 SP starts / 440 dates / 3 seasons (2024-2026)
    # Total < 7.5 → QS 45.4% (+10.2pp) | Total >= 10.0 → QS 26.3% (-8.9pp)
    own_t = next((t for t in t_reports if t.get("team") == p.get("team")), None)
    own_itt  = float((own_t or {}).get("implied_total", 4.5) or 4.5)
    opp_itt2 = float((opp_t or {}).get("implied_total", 4.5) or 4.5)
    game_total_proxy = own_itt + opp_itt2
    if game_total_proxy < 7.5:
        conf += 8.0
        reasons.append(f"Low game total ({game_total_proxy:.1f}) — elite pitcher environment historically.")
    elif game_total_proxy < 8.5:
        conf += 4.0
        reasons.append(f"Below-average game total ({game_total_proxy:.1f}) — pitcher-friendly environment.")
    elif game_total_proxy >= 10.0:
        conf -= 8.0
        reasons.append(f"High game total ({game_total_proxy:.1f}) — pitcher gets shelled historically.")
    elif game_total_proxy >= 9.5:
        conf -= 5.0
        reasons.append(f"Above-average game total ({game_total_proxy:.1f}) — hitter-friendly environment.")

    # 8. Sharp Money Backing
    # OMEGA v15.0: is_whale REMOVED from +10 pitcher CONF boost (r=-0.0330; public money != edge)
    # is_sharp and is_shark retain the boost
    if p.get("is_sharp") or p.get("is_shark"):
        sharp_boost = float(_w.get("is_sharp", 10.0))
        conf += sharp_boost
        reasons.append("Sharp money backing this pitcher.")

    # 9. Pinnacle SP Boost (implied probability delta >= 4% in totals < 8.5) (OMEGA v16.0)
    if p.get("pinnacle_boost_active"):
        conf += 10.0
        reasons.append("Pinnacle SP Boost — sharps backing this low-scoring matchup.")

    # 10. Underdog Pitcher Steam Boost (ML move <= -15, underdog, total < 9.0) (OMEGA v17.0)
    # Backtested: Underdog steam hit K Over at 71.4% (75% when game total < 9.0) and massive steam (<= -20) hit at 77.8%!
    if own_t:
        is_underdog = (own_itt < 4.2)
        ml_move = float(p.get("ml_move", 0.0) or 0.0)
        if ml_move <= -15 and is_underdog and game_total_proxy < 9.0:
            boost_val = 10.0 if ml_move <= -20 else 6.0
            conf += boost_val
            reasons.append(f"Underdog Pitcher Steam Boost ({ml_move:+.0f} move) — backtested edge.")

    # Early-innings volatility (stamina risk)
    if p.get("early_innings_volatility"):
        eiv_penalty = abs(float(_w.get("early_innings_volatility", -10.0)))
        conf -= eiv_penalty
        reasons.append("Early-innings volatility (IP/start < 4.5) — low QS ceiling.")

    # 10. Intraday Volatility
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

    final_conf = _clamp(conf)
    
    # OMEGA v20.3: Pitcher Variance Classifier Fade Label Reason (Item 1)
    if final_conf <= 25.0:
        if p.get("is_high_variance"):
            reasons.append("LOW-CONFIDENCE FADE: Low model confidence but high performance variance (volatile ceiling).")
        else:
            reasons.append("HIGH-CONFIDENCE FADE: Consistent low variance and poor matchups.")

    return final_conf, reasons
