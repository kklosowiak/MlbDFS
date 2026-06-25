"""Attack confidence for individual hitters (0-100 decision layer)."""
import re

def score_hitter_confidence(h, team_data=None, opp_pitcher=None):
    conf = 50
    reasons = []



    # 1. Individual Matchup xwOBA (Physics Component)
    xwoba = float(h.get("matchup_xwoba", 0.330) or 0.330)
    if xwoba >= 0.370:
        conf += 18
        reasons.append(f"Elite matchup xwOBA ({xwoba:.3f}).")
    elif xwoba >= 0.345:
        conf += 10
        reasons.append(f"Strong matchup xwOBA ({xwoba:.3f}).")
    elif xwoba < 0.300:
        conf -= 12
        reasons.append(f"Weak matchup xwOBA ({xwoba:.3f}).")

    # 2. Dynamic Platoon Splits via NPAS (Net Platoon Advantage Score)
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
            reasons.append(f"Platoon edge vs {h.get('pitch_hand', 'P')}HP.")
        elif plt <= 0.92:
            conf -= 10
            reasons.append(f"Platoon fade vs {h.get('pitch_hand', 'P')}HP.")

    # 3. Prop Betting Targets & Juice
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

    # 4. Multi-Factor Slate Momentum Index (MSMI) & Streaks
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

    # Continuous Form Index (Sprint 1)
    recent_ops = float(h.get("recent_ops", 0.0) or 0.0)
    season_ops = float(h.get("season_ops", 0.0) or 0.0)
    if season_ops > 0.0 and recent_ops > 0.0:
        ratio = (recent_ops - season_ops) / season_ops
        form_boost = max(-15.0, min(15.0, ratio * 20.0))
        conf += form_boost
        reasons.append(f"Continuous Form Index boost ({form_boost:+.1f} CONF) based on L7 OPS {recent_ops:.3f} vs Season OPS {season_ops:.3f}")

    # Statcast Batted-Ball Profiles (Sprint 1)
    barrel_pct = float(h.get("barrel_pct", 0.0) or 0.0)
    hard_hit_pct = float(h.get("hard_hit_pct", 0.0) or 0.0)
    if barrel_pct >= 12.0 and hard_hit_pct >= 45.0:
        conf += 8.0
        reasons.append(f"Statcast Batted-Ball profile edge: Barrel% ({barrel_pct:.1f}%) and HardHit% ({hard_hit_pct:.1f}%) are elite.")

    # 5. Team Stack & Market Sentiment Context
    if team_data:
        if team_data.get("stack_score", 0) >= 105:
            conf += 8
            reasons.append("Elite team stack context.")
        if team_data.get("is_steam") or team_data.get("is_shark"):
            conf += 6
            reasons.append("Team has sharp market steam/shark backing.")

    # 6. Opposing Starting Pitcher Form & Quality
    if opp_pitcher:
        if opp_pitcher.get("is_trap"):
            conf += 10
            reasons.append(f"Opposing SP trap ({opp_pitcher.get('pitcher', 'SP')}).")
        
        if opp_pitcher.get("form_status") == "COLD":
            conf += 10
            reasons.append(f"Attacking cold opposing pitcher ({opp_pitcher.get('pitcher', 'SP')}).")
            
        opp_sp_phys = opp_pitcher.get("physics_score", 0) or 0
        if opp_sp_phys >= 18:
            conf -= 12
            reasons.append("Opposing SP has strong underlying physics.")
        elif opp_sp_phys < 10 and not opp_pitcher.get("is_trap"):
            conf += 12
            reasons.append("Attacking pitcher with weak underlying physics.")

    # 7. Opposing Bullpen Fatigue
    opp_bf = h.get("bullpen_fatigue", 0) or (team_data.get("bullpen_fatigue", 0) if team_data else 0)
    is_gassed = team_data.get("is_gassed", False) if team_data else False
    if opp_bf >= 85 or is_gassed:
        conf += 8
        reasons.append(f"Attacking gassed opposing bullpen (Fatigue: {opp_bf}%).")
    elif opp_bf >= 65:
        conf += 4
        reasons.append(f"Attacking fatigued opposing bullpen (Fatigue: {opp_bf}%).")

    # 8. Ballpark Weather (Temperature & Wind Vectors)
    weather_lbl = (team_data.get("weather_label") if team_data else None) or h.get("weather_label") or ""
    weather_lbl_upper = weather_lbl.upper()
    if "DOME" not in weather_lbl_upper and "INDOOR" not in weather_lbl_upper:
        temp_match = re.search(r'(\d+)°', weather_lbl)
        if temp_match:
            temp = int(temp_match.group(1))
            if temp >= 80:
                conf += 5
                reasons.append(f"Hitter-friendly weather: warm temperature ({temp}°F).")
            elif temp < 60:
                conf -= 6
                reasons.append(f"Pitcher-friendly weather: cold temperature ({temp}°F).")
        
        if "OUT TO" in weather_lbl_upper:
            wind_speed_match = re.search(r'(\d+)\s*MPH', weather_lbl_upper)
            if wind_speed_match:
                speed = int(wind_speed_match.group(1))
                if speed >= 10:
                    conf += 6
                    reasons.append(f"Hitter-friendly wind: blowing out to center at {speed} mph.")

    if not reasons:
        reasons.append("Neutral hitter profile on this slate.")

    # Batting Order Modifier (applied after existing confidence calculation)
    raw_order = h.get("batting_order")
    if raw_order is not None:
        try:
            batting_order = int(float(raw_order))
            if batting_order > 0:
                if batting_order in (1, 2):
                    conf += 5
                    reasons.append("Batting Order Spot 1-2 boost (+5)")
                elif batting_order in (3, 4):
                    conf += 2
                    reasons.append("Batting Order Spot 3-4 boost (+2)")
                elif batting_order in (5, 6):
                    pass # 0 modifier
                elif batting_order in (7, 8):
                    conf -= 5
                    reasons.append(f"Batting Order Spot {batting_order} penalty (-5)")
                elif batting_order == 9:
                    conf -= 12
                    reasons.append("Batting Order Spot 9 penalty (-12)")
        except (ValueError, TypeError):
            pass

    return max(0, min(100, conf)), reasons
