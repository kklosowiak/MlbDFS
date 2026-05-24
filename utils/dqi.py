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
    Base: 30 (teams start in FADE — must earn TRUST).
    TRUST >= 75 | CAUTION >= 50 | FADE < 50

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

    if divergence < 10 and implied_total < 5.0:
        return None, None, [], []

    try:
        opp_phys = float(team.get('opp_pitcher_physics', 50.0) or 50.0)
    except (TypeError, ValueError):
        opp_phys = 50.0
    bullpen = team.get('bullpen_fatigue', 0) or 0
    tt_move = team.get('tt_move', 0.0) or 0.0
    ml_move = team.get('ml_move', 0.0) or 0.0
    is_storm = team.get('is_storm', False)
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

    div_factor = min(1.0, max(0.0, (float(divergence) - 10.0) / 15.0))
    div_pts = 5.0 + 15.0 * div_factor
    pos_pts += div_pts
    pos_factors.append(f"Divergence Sharp Interest (+{round(div_pts, 1)} pts)")

    phys_factor = min(1.0, max(0.0, (40.0 - float(opp_phys)) / 25.0))
    phys_pts = 20.0 * phys_factor
    if phys_pts > 0:
        pos_pts += phys_pts
        pos_factors.append(f"Targetable Starter SP (+{round(phys_pts, 1)} pts)")

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

    xwoba_factor = min(1.0, max(0.0, (float(team_xwoba) - 0.300) / 0.050))
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

    if is_storm:
        pos_pts += 8.0
        pos_factors.append("Storm Physics (+8 pts)")
    if is_opp_debut:
        pos_pts += 10.0
        pos_factors.append("Debut Trap SP (+10 pts)")
    if team_stack_trap:
        # OMEGA v9.8: Scaled GPP Chalk Penalty
        # Base penalty scales from 5.0 (physics >= 45) to 20.0 (physics <= 25)
        phys_val = float(team.get('physics_score', 50.0) or 50.0)
        phys_factor = min(1.0, max(0.0, (45.0 - phys_val) / 20.0))
        penalty = 5.0 + 15.0 * phys_factor
        
        # Mitigate penalty if divergence is high (representing sharp backing)
        if divergence > 10.0:
            div_mitigation = min(10.0, (divergence - 10.0) * 0.5)
            penalty = max(5.0, penalty - div_mitigation)
            
        warn_pts += penalty
        warn_factors.append(f"Stack Chalk Warning (-{round(penalty, 1)} pts)")
    if opp_pitcher_trap:
        pos_pts += 20.0
        pos_factors.append("Opposing SP Trap (+20 pts)")

    if divergence < 0:
        warn_pts += 10.0
        warn_factors.append("Negative Market Divergence (-10 pts)")

    dqi_score = 30.0 + pos_pts - warn_pts
    dqi_score = max(0.0, min(100.0, dqi_score))
    dqi_score_int = int(round(dqi_score))
    
    # Implied run total floor (3.8 runs) for GPP Trust
    status = "TRUST" if dqi_score_int >= 75 else ("CAUTION" if dqi_score_int >= 50 else "FADE")
    if status == "TRUST" and implied_total < 3.8:
        status = "CAUTION"
        warn_factors.append(f"Implied Total Floor Cap (ITT {round(implied_total, 2)} < 3.8)")
        
    # OMEGA v13.7: Sharp Fade / Negative Divergence Cap
    # A team being faded by sharps (negative divergence) cannot be trusted as a DQI TRUST stack.
    if status == "TRUST" and divergence < 0:
        status = "CAUTION"
        warn_factors.append(f"Negative Divergence TRUST Cap (Div {round(divergence, 1)}% < 0)")
        
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
