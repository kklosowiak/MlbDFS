"""
OMEGA v9.7: Divergence Quality Index (DQI) — single source of truth.
"""
import json
import os
import datetime


def calculate_dqi(team, pitchers=None):
    """
    Continuous Multi-Layer DQI Slider Model.

    GATE: Only fires when team divergence >= 10%.
    Base: 30 (teams start in LEVERAGE — must earn TRUST).
    TRUST >= 82 | CAUTION >= 50 | LEVERAGE < 50

    Returns (score, status, pos_factors, warn_factors) or (None, None, [], []) if gated.
    """
    try:
        divergence = float(team.get('divergence', 0) or 0)
    except (TypeError, ValueError):
        divergence = 0.0
    try:
        implied_total = float(team.get('implied_total', 0.0) or 0.0)
    except (TypeError, ValueError):
        implied_total = 0.0

    if divergence < 10.0:
        return None, None, [], []

    try:
        opp_phys = float(team.get('opp_pitcher_physics', 50.0) or 50.0)
    except (TypeError, ValueError):
        opp_phys = 50.0
    bullpen = team.get('bullpen_fatigue', 0) or 0
    tt_move = team.get('tt_move', 0.0) or 0.0
    ml_move = team.get('ml_move', 0.0) or 0.0
    team_xwoba = team.get('team_xwoba', 0.0) or 0.0
    power_conc = team.get('power_concentration', 0.0) or 0.0
    total_signal = team.get('total_signal', '') or ''
    trend = team.get('trend', 'STABLE') or 'STABLE'
    is_opp_debut = team.get('is_opp_debut', False)

    team_stack_trap = team.get('is_trap', False)
    opp_pitcher_trap = False
    if pitchers is not None:
        opp_p_name = team.get('opp_pitcher', '').lower().strip()
        opp_p_obj = next(
            (p for p in pitchers if p.get('pitcher', '').lower().strip() == opp_p_name),
            None,
        )
        if opp_p_obj:
            opp_pitcher_trap = opp_p_obj.get('is_trap', False)

    pos_pts = 0.0
    warn_pts = 0.0
    pos_factors = []
    warn_factors = []

    # Strictly gated at >= 10.0% divergence

    div_factor = min(1.0, max(0.0, (float(divergence) - 10.0) / 10.0))
    div_pts = 10.0 + 10.0 * div_factor
    pos_pts += div_pts
    pos_factors.append(f"Divergence Sharp Interest (+{round(div_pts, 1)} pts)")

    phys_factor = min(1.0, max(0.0, (35.0 - float(opp_phys)) / 20.0))
    phys_pts = 20.0 * phys_factor
    if phys_pts > 0:
        pos_pts += phys_pts
        pos_factors.append(f"Targetable Starter SP (+{round(phys_pts, 1)} pts)")

    # Tough SP Physics Penalty
    if opp_phys >= 75.0:
        warn_pts += 25.0
        warn_factors.append(f"Elite Opposing SP Penalty (-25 pts)")
    elif opp_phys >= 60.0:
        warn_pts += 15.0
        warn_factors.append(f"Tough Opposing SP Penalty (-15 pts)")

    # ML Shark Target Drag (Defensive steam trap)
    if team.get('is_shark', False):
        warn_pts += 20.0
        warn_factors.append("ML Shark/Sharp Target Drag (-20 pts)")

    pen_factor = min(1.0, max(0.0, (float(bullpen) - 50.0) / 50.0))
    pen_pts = 15.0 * pen_factor
    if pen_pts > 0:
        pos_pts += pen_pts
        pos_factors.append(f"Vulnerable Bullpen (+{round(pen_pts, 1)} pts)")

    if tt_move >= 0.3 or ml_move <= -10.0:
        pos_pts += 12.0
        pos_factors.append("Market Steam (+12 pts)")
    elif (tt_move <= -0.3 and ml_move >= 10.0) or (ml_move >= 15.0) or (tt_move <= -0.5):
        warn_pts += 15.0
        warn_factors.append("Reverse Steam (-15 pts)")

    if 'O-DIV' in total_signal:
        pos_pts += 10.0
        pos_factors.append("Market O-DIV (+10 pts)")
    elif 'U-DIV' in total_signal:
        warn_pts += 12.0
        warn_factors.append("Market U-DIV (-12 pts)")

    xwoba_factor = min(1.0, max(0.0, (float(team_xwoba) - 0.315) / 0.040))
    xwoba_pts = 12.0 * xwoba_factor
    if xwoba_pts > 0:
        pos_pts += xwoba_pts
        pos_factors.append(f"Offense xwOBA Hitting (+{round(xwoba_pts, 1)} pts)")

    if power_conc > 0.355:
        pos_pts += 8.0
        pos_factors.append("Power Stack (+8 pts)")

    if trend == 'SURGING':
        pos_pts += 10.0
        pos_factors.append("Surging Trend (+10 pts)")
    elif trend == 'FADING':
        warn_pts += 15.0
        warn_factors.append("Fading Trend (-15 pts)")

    run_factor = min(1.0, max(0.0, (float(implied_total) - 4.0) / 1.5))
    run_pts = 15.0 * run_factor
    if run_pts > 0:
        pos_pts += run_pts
        pos_factors.append(f"Implied Run Env (+{round(run_pts, 1)} pts)")

    # OMEGA v19.3: is_storm removed from DQI scoring (storm = divergence>=10 AND tt_move>=0.3;
    # divergence already earns +10-20 pts above and market steam captures tt_move>=0.3)
    if is_opp_debut:
        pos_pts += 10.0
        pos_factors.append("Debut Trap SP (+10 pts)")
    if team_stack_trap:
        # OMEGA v9.8: Scaled GPP Chalk Penalty
        # Base penalty scales from 5.0 (physics >= 45) to 20.0 (physics <= 25)
        phys_val = float(team.get('physics_score', 50.0) or 50.0)
        phys_factor = min(1.0, max(0.0, (45.0 - phys_val) / 20.0))
        penalty = 5.0 + 15.0 * phys_factor
        
        warn_pts += penalty
        warn_factors.append(f"Stack Chalk Warning (-{round(penalty, 1)} pts)")
    if opp_pitcher_trap:
        scaled_pts = 20.0 + (35.0 - float(opp_phys)) * 0.5
        trap_pts = max(10.0, min(30.0, scaled_pts))
        pos_pts += trap_pts
        pos_factors.append(f"Opposing SP Trap (+{round(trap_pts, 1)} pts)")

    # Divergence is guaranteed >= 10.0% positive

    dqi_score = 30.0 + pos_pts - warn_pts
    dqi_score = max(0.0, min(100.0, dqi_score))
    
    # Divergence is guaranteed >= 10.0% positive, no score cap needed
        
    dqi_score_int = int(round(dqi_score))
    
    status = "TRUST" if dqi_score_int >= 82 else ("CAUTION" if dqi_score_int >= 50 else "LEVERAGE")
    
    # Dual-Gate Cap: TRUST requires >= 12.0% divergence
    if status == "TRUST" and divergence < 12.0:
        status = "CAUTION"
        warn_factors.append(f"TRUST Status Capped (Div {round(divergence, 1)}% < 12.0% Gate)")

    # Implied run total floor (4.2 runs) for GPP Trust
    if status == "TRUST" and implied_total < 4.2:
        status = "CAUTION"
        warn_factors.append(f"Implied Total Floor Cap (ITT {round(implied_total, 2)} < 4.2)")

    # Bullpen Fatigue Floor: TRUST requires opposing bullpen >= 65
    # Data: 0/8 TRUST calls with bullpen < 65 scored 4+ runs (30-slate audit, May 2026)
    # All 4 confirmed TRUST hits had bullpen fatigue >= 65
    if status == "TRUST" and bullpen < 65:
        status = "CAUTION"
        warn_factors.append(f"TRUST Capped: Bullpen Too Fresh ({int(bullpen)} < 65 fatigue)")
        
    if isinstance(team, dict):
        team["dqi_pos_pts"] = pos_pts
        team["dqi_warn_pts"] = warn_pts

    return dqi_score_int, status, pos_factors, warn_factors


def persist_dqi_history(teams, reports_dir, pitchers=None):
    """Write dqi_history.json for teams with active DQI (divergence >= 10%)."""
    if not teams:
        return
    dqi_history_path = os.path.join(reports_dir, "dqi_history.json")
    dqi_history = {}
    if os.path.exists(dqi_history_path):
        try:
            with open(dqi_history_path, "r", encoding="utf-8") as dh:
                dqi_history = json.load(dh)
        except Exception:
            dqi_history = {}

    now_et = datetime.datetime.now().isoformat()
    for t in teams:
        team_key = t.get("team", "")
        if not team_key:
            continue
        dqi_score, dqi_status, _, _ = calculate_dqi(t, pitchers=pitchers)
        if dqi_score is not None:
            dqi_history[team_key] = {
                "score": dqi_score,
                "status": dqi_status,
                "recorded_at": now_et,
            }

    try:
        os.makedirs(reports_dir, exist_ok=True)
        with open(dqi_history_path, "w", encoding="utf-8") as dh:
            json.dump(dqi_history, dh, indent=2)
    except Exception as e:
        print(f"[DQI]: Failed to persist history: {e}")


def load_dqi_history(reports_dir):
    path = os.path.join(reports_dir, "dqi_history.json")
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}
