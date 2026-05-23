"""Attack confidence for individual hitters (0-100 decision layer)."""


def score_hitter_confidence(h, team_data=None, opp_pitcher=None):
    conf = 50
    reasons = []

    xwoba = float(h.get("matchup_xwoba", 0.330) or 0.330)
    if xwoba >= 0.370:
        conf += 18
        reasons.append(f"Elite matchup xwOBA (.{str(xwoba)[2:5]}).")
    elif xwoba >= 0.345:
        conf += 10
        reasons.append(f"Strong matchup xwOBA (.{str(xwoba)[2:5]}).")
    elif xwoba < 0.300:
        conf -= 12
        reasons.append(f"Weak matchup xwOBA (.{str(xwoba)[2:5]}).")

    # Dynamic Platoon Splits via NPAS (Net Platoon Advantage Score)
    platoon_label = h.get("platoon_label", "")
    if platoon_label and "ELITE" in platoon_label.upper():
        conf += 12
        reasons.append("⚡ ELITE PLATOON MATCHUP: Hitter xwOBA and pitcher splits allowed perfectly align.")
    elif platoon_label and "TRAP" in platoon_label.upper():
        conf -= 10
        reasons.append("🚨 PLATOON TRAP: Matchup heavily neutralizes their side split.")
    else:
        # Fallback to old platoon multiplier if no NPAS label is found
        plt = float(h.get("platoon_multiplier", 1.0) or 1.0)
        if plt >= 1.08:
            conf += 12
            reasons.append(f"Platoon edge vs {h.get('pitch_hand', 'P')}HP ({h.get('platoon_label', 'split')}).")
        elif plt <= 0.92:
            conf -= 10
            reasons.append(f"Platoon fade vs {h.get('pitch_hand', 'P')}HP.")

    if h.get("runs_target") or h.get("rbis_target"):
        conf += 6
        reasons.append("Runs/RBI prop TARGET — stack-correlated juice.")
    elif h.get("runs_juice") or h.get("rbis_juice"):
        conf += 3
        reasons.append("Runs/RBI prop juice on board.")

    if h.get("is_juiced_target"):
        conf += 8
        reasons.append("Juiced prop TARGET — strict line/pricing edge.")
    elif h.get("is_prop_juice"):
        conf += 4
        reasons.append("Prop JUICE — Over favored vs Under on hits/TB.")

    # New Multi-Factor Slate Momentum Index (MSMI) for hitters
    if h.get("is_cold_streak_msmi") or h.get("is_cold_streak"):
        conf -= 12
        reasons.append("Hitter Slate Slump (MSMI): Elevated rolling K% surge & OPS slumping.")
    elif h.get("is_hot_run_msmi") or h.get("is_hot"):
        conf += 10
        reasons.append("Hitter Hot Run (MSMI): Rolling OPS surge and reduced strikeout rate.")
    if h.get("is_speed_target"):
        conf += 5
        reasons.append("Speed prop target.")

    if h.get("smash_factor"):
        conf += 8
        reasons.append("Smash factor: rolling OPS above season baseline.")

    if team_data:
        if team_data.get("stack_score", 0) >= 105:
            conf += 8
            reasons.append("Elite team stack context.")
        if team_data.get("is_steam") or team_data.get("is_shark"):
            conf += 6
            reasons.append("Team has sharp market steam/shark backing.")

    if opp_pitcher and opp_pitcher.get("is_trap"):
        conf += 10
        reasons.append(f"Opposing SP trap ({opp_pitcher.get('pitcher', 'SP')}).")

    if opp_pitcher and (opp_pitcher.get("physics_score", 0) or 0) >= 18:
        conf -= 12
        reasons.append("Opposing SP has strong underlying physics.")

    if not reasons:
        reasons.append("Neutral hitter profile on this slate.")

    return max(0, min(100, conf)), reasons
