import os
import json
import sys
from datetime import datetime, timedelta
from config import config

# Add project root to sys.path just in case
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# ─────────────────────────────────────────────────────────────
# 1. CONSTANTS & UTILS
# ─────────────────────────────────────────────────────────────

def estimate_weather_boost(label):
    if not label or "Indoor" in label or "Dome" in label:
        return 0.0
    temp = 70.0
    try:
        parts = label.split()
        for p in parts:
            if "°" in p:
                temp = float(p.replace("°", ""))
                break
    except:
        pass
    
    density_boost = 0.0
    if temp >= 85:
        density_boost = 7.0
    elif temp >= 75:
        density_boost = 4.0
        
    wind_boost = 0.0
    if "Out" in label:
        wind_boost = 1.5
    elif "In" in label:
        wind_boost = -1.5
        
    return wind_boost + density_boost


def _stack_chalk_trap(physics_raw, team_xwoba, physics_display, ml_move, divergence, is_steam, is_shark, pre_trap_score):
    if (is_steam or is_shark) and ml_move <= -10:
        return False
    if pre_trap_score >= 110.0:
        return False
    weak_offense = team_xwoba < 0.300 or physics_display < 25.0 or physics_raw < 36.0
    if not weak_offense:
        return False
    sharp_in_favor = (is_steam or is_shark) and ml_move <= -10
    public_pressure = ml_move <= -12 or (divergence < -12 and not sharp_in_favor)
    return public_pressure


# Load statcast cache for True Talent boost simulation
STATCAST_CACHE = {}
try:
    cache_path = os.path.join(config.DATA_DIR, "statcast_cache.json")
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            STATCAST_CACHE = json.load(f)
except:
    pass


def compute_true_talent_boost(opp_pitcher_name):
    if not opp_pitcher_name:
        return 0.0
    try:
        from utils.normalization import normalize_player_name
        p_norm = normalize_player_name(opp_pitcher_name)
        p_profile = STATCAST_CACHE.get(p_norm, {})
        if p_profile and p_profile.get("type") == "pitcher":
            ip = float(p_profile.get("ip", 0.0))
            bb = float(p_profile.get("bb", 0.0))
            k = float(p_profile.get("k", 0.0))
            hr = float(p_profile.get("hr", 0.0))
            bf = ip * 2.9 + k + bb
            k_bb_pct = (k - bb) / bf if bf > 0 else 0.12
            hr_9 = (hr / ip * 9) if ip > 5.0 else 1.0
            if ip >= 50.0 and k_bb_pct < 0.14 and hr_9 > 1.6:
                return 2.0
    except:
        pass
    return 0.0


# ─────────────────────────────────────────────────────────────
# 2. PARAMETERIZED STACK SCORING
# ─────────────────────────────────────────────────────────────

def calculate_stack_score_parameterized(
    team_data, opp_pitcher_dict,
    is_sharp_in_alpha, sharp_bonus, is_steam_in_alpha, is_whale_standalone, keep_shark_storm
):
    team = team_data.get('team', '')
    opponent = team_data.get('opponent', '')
    ml_move = float(team_data.get('ml_move', 0.0) or 0.0)
    tt_move = float(team_data.get('tt_move', 0.0) or 0.0)
    curr_itt = float(team_data.get('implied_total', 4.5) or 4.5)
    team_xwoba = float(team_data.get('team_xwoba', 0.330) or 0.330)
    power_concentration = float(team_data.get('power_concentration', 0.330) or 0.330)
    bullpen_fatigue = float(team_data.get('bullpen_fatigue', 0.0) or 0.0)
    divergence = float(team_data.get('divergence', 0.0) or 0.0)
    
    # Opponent SP stats from opposing pitcher's dict
    opp_pitcher_physics = float(team_data.get('opp_pitcher_physics', 50.0) or 50.0)
    pitcher_outs = float(team_data.get('opp_pitcher_outs', 18.0) or 18.0)
    opp_pitcher_name = team_data.get('opp_pitcher')
    opp_pitcher_alpha = 0.0
    opp_pitcher_trap = False
    
    opp_walks_line = None
    opp_walks_odds = None
    opp_er_line = None
    opp_er_odds = None
    
    if opp_pitcher_dict:
        opp_pitcher_alpha = float(opp_pitcher_dict.get('alpha_score', 0.0) or 0.0)
        opp_pitcher_trap = bool(opp_pitcher_dict.get('is_trap', False))
        opp_walks_line = opp_pitcher_dict.get('walks_line')
        opp_walks_odds = opp_pitcher_dict.get('walks_odds')
        opp_er_line = opp_pitcher_dict.get('er_line')
        opp_er_odds = opp_pitcher_dict.get('er_odds')

    confidence = team_data.get('confidence', 'high')
    is_burst = bool(team_data.get('is_burst', False))
    is_anti_chalk_smash = bool(team_data.get('is_anti_chalk_smash', False))
    is_pitch_alignment = bool(team_data.get('is_pitch_alignment', False))
    umpire_factor = float(team_data.get('umpire_factor', 1.0) or 1.0)
    weather_boost = estimate_weather_boost(team_data.get('weather_label', ''))
    
    is_opp_debut = bool(team_data.get('is_opp_debut', False))
    is_sneaky = bool(team_data.get('is_sneaky', False))
    is_pinnacle_offense_boost = bool(team_data.get('is_pinnacle_offense_boost', False))
    is_velocity_boost = bool(team_data.get('is_velocity_boost', False))
    
    # Parse over/under divergence from total_signal
    total_signal = team_data.get('total_signal', '')
    over_divergence = 0
    under_divergence = 0
    if total_signal:
        if "O-DIV" in total_signal:
            try: over_divergence = int(total_signal.split("+")[-1])
            except: pass
        elif "U-DIV" in total_signal:
            try: under_divergence = int(total_signal.split("+")[-1])
            except: pass

    # Resolve park factor
    # Look up opposing pitcher's home/away status to identify game venue
    venue_team = opponent
    if opp_pitcher_dict:
        # If opponent pitcher is home, game is at opponent's stadium
        if opp_pitcher_dict.get('side') == 'home':
            venue_team = opponent
        else:
            venue_team = team
            
    raw_pf = config.PARK_FACTORS.get(venue_team, 1.0)
    park_factor = 1.0 + (raw_pf - 1.0) * 0.5

    # Re-compute Reliever Dyn Mult/Fatigue Mod
    dyn_mult, dyn_fatigue_mod = 1.00, 1.00
    try:
        cache_path = os.path.join(config.DATA_DIR, "bullpen_season_cache.json")
        if os.path.exists(cache_path):
            with open(cache_path, 'r') as f:
                reliever_stats = json.load(f)
            
            matched_key = None
            for k in reliever_stats.keys():
                if str(opponent).lower() in k.lower() or k.lower() in str(opponent).lower():
                    matched_key = k
                    break
                    
            if matched_key and matched_key in reliever_stats:
                stats = reliever_stats[matched_key]
                k_bb = stats["k_bb_pct"]
                era = stats["era"]
                whip = stats["whip"]
                score_val = (k_bb * 100 * 2.5) + (5.0 - era) * 10 + (1.5 - whip) * 30
                if score_val >= 60.0:
                    dyn_mult, dyn_fatigue_mod = 0.90, 0.75
                elif score_val >= 48.0:
                    dyn_mult, dyn_fatigue_mod = 0.95, 0.85
                elif score_val >= 35.0:
                    dyn_mult, dyn_fatigue_mod = 1.00, 1.00
                elif score_val >= 22.0:
                    dyn_mult, dyn_fatigue_mod = 1.07, 1.12
                else:
                    dyn_mult, dyn_fatigue_mod = 1.15, 1.25
    except:
        pass

    # 1. Physics raw
    effective_physics = (team_xwoba * 0.4) + (power_concentration * 0.6)
    physics_raw = (effective_physics - 0.260) / (0.400 - 0.260) * 100
    physics_raw = max(0.0, min(100.0, physics_raw))
    physics_raw = min(120.0, physics_raw * park_factor)

    # 2. Bullpen boost
    fatigue_floor = 65.0
    bullpen_boost = max(0.0, (bullpen_fatigue - fatigue_floor) / 2.5)
    effective_outs = 15.5 if opp_pitcher_trap else pitcher_outs
    if effective_outs <= 15.5:
        bullpen_boost *= 1.20
    elif effective_outs >= 18.0:
        bullpen_boost *= 0.85
        
    bullpen_boost *= dyn_fatigue_mod
    bullpen_boost = min(25.0, bullpen_boost)

    # 3. Market raw
    base_market_score = max(0.0, min(100.0, ((curr_itt - 3.0) / 2.5) * 100.0))
    ml_score = max(0.0, min(100.0, (abs(ml_move) / 20.0) * 100.0)) if ml_move < 0 else 0.0
    tt_score = max(0.0, min(100.0, (tt_move / 0.5) * 100.0)) if tt_move > 0 else 0.0
    market_raw = base_market_score + (ml_score * 0.25) + (tt_score * 0.25)
    market_raw = max(0.0, min(120.0, market_raw))

    # 4. Base Score
    score = 40.0 + (physics_raw * 0.80) + (market_raw * 0.20) + bullpen_boost

    # 5. Signal logic
    is_sharp = bool(team_data.get('is_sharp', False))
    is_steam = bool(team_data.get('is_steam', False))
    is_whale = bool(team_data.get('is_whale', False))
    is_shark = bool(team_data.get('is_shark', False))
    is_storm = bool(team_data.get('is_storm', False))

    alpha_signals = 0
    beta_signals = 0
    market_alphas = 0

    if is_steam:
        if is_steam_in_alpha: market_alphas += 1
        else: beta_signals += 1

    if is_sharp:
        if is_sharp_in_alpha: market_alphas += 1
        else: beta_signals += 1

    if market_alphas > 0:
        alpha_signals += 1
    convergence_boost = 1.0
    if market_alphas >= 3:
        convergence_boost = 1.10

    if is_burst: beta_signals += 1
    if tt_move > 0.5: beta_signals += 1
    if bullpen_fatigue >= 65: beta_signals += 1
    
    if keep_shark_storm:
        if is_shark: beta_signals += 1
        if is_storm and (is_sharp or is_steam): beta_signals += 1

    if is_whale:
        if is_whale_standalone:
            beta_signals += 1
        else:
            if is_sharp or is_steam:
                beta_signals += 1

    anchor_ratio = 1.0
    if team_xwoba < 0.295:
        anchor_ratio = max(0.75, (team_xwoba / 0.295) ** 2.0)

    market_premium = (alpha_signals * 0.15) + (beta_signals * 0.05)
    if is_sharp:
        market_premium += sharp_bonus

    dampened_market_premium = market_premium * anchor_ratio
    multiplier = 1.0 + dampened_market_premium

    if opp_pitcher_physics > 85 or (is_storm and opp_pitcher_physics > 70 and keep_shark_storm):
        multiplier -= 0.10

    div_premium = min(0.10, (max(0, divergence) / 150.0))
    dampened_div_premium = div_premium * anchor_ratio
    div_multiplier = 1.0 + dampened_div_premium

    magnetism_boost = 1.0
    if opp_pitcher_physics < 20.0:
        vulnerability_gap = (20.0 - opp_pitcher_physics) / 10.0
        fatigue_boost = 1.0 + (bullpen_fatigue / 100.0) * 0.30
        raw_magnetism = 1.0 + 0.20 + (vulnerability_gap ** 1.0) * 0.50 * fatigue_boost
        raw_magnetism_capped = min(1.30, raw_magnetism)
        magnetism_boost = 1.0 + (raw_magnetism_capped - 1.0) * anchor_ratio

    bullpen_skill_mult = dyn_mult

    pre_trap_combined = multiplier * div_multiplier * convergence_boost * magnetism_boost * bullpen_skill_mult
    pre_trap_combined = min(pre_trap_combined, 1.35)
    pre_trap_score = score * pre_trap_combined

    chalk_trap = _stack_chalk_trap(
        physics_raw=physics_raw, team_xwoba=team_xwoba, physics_display=physics_raw * 0.40,
        ml_move=ml_move, divergence=divergence, is_steam=is_steam, is_shark=is_shark,
        pre_trap_score=pre_trap_score
    )
    trap_multiplier = 0.90 if chalk_trap else 1.0

    combined = min(pre_trap_combined * trap_multiplier, 1.35)
    final_omega = score * combined

    is_gassed_attack = (bullpen_fatigue >= 75) and (pitcher_outs <= 15.5) and (team_xwoba >= 0.315)
    if is_gassed_attack:
        final_omega += 8.0

    if is_anti_chalk_smash:
        final_omega += 10.0
    if is_pitch_alignment:
        final_omega += 4.0

    walks_boost = 0.0
    if opp_walks_line is not None:
        try:
            wf = float(opp_walks_line)
            wo = float(opp_walks_odds) if opp_walks_odds is not None else -110.0
            prob = abs(wo) / (abs(wo) + 100.0) if wo < 0 else 100.0 / (wo + 100.0)
            base_pts = 4.0 + (wf - 1.5) * 4.0
            walks_boost = max(0.0, base_pts * (prob / 0.52))
        except:
            pass

    er_boost = 0.0
    if opp_er_line is not None:
        try:
            ef = float(opp_er_line)
            eo = float(opp_er_odds) if opp_er_odds is not None else -110.0
            prob = abs(eo) / (abs(eo) + 100.0) if eo < 0 else 100.0 / (eo + 100.0)
            base_pts = 6.0 + (ef - 2.5) * 4.0
            er_boost = max(0.0, base_pts * (prob / 0.52))
        except:
            pass

    true_talent_boost = compute_true_talent_boost(opp_pitcher_name)
    final_omega += walks_boost + er_boost + true_talent_boost

    if team_xwoba < 0.295 and dampened_market_premium > 0.10:
        final_omega = min(final_omega, score * (1.0 + min(0.22, dampened_market_premium)))

    is_sharp_backed = is_whale or (is_storm and keep_shark_storm) or (divergence > 15)
    if curr_itt < 4.0 and final_omega > 90.0 and not is_sharp_backed:
        final_omega *= 0.85
    elif curr_itt > 5.5 and final_omega < 70.0:
        final_omega *= 1.10

    if confidence == 'low':
        final_omega = min(80.0, final_omega)

    env_synergy = 1.0 + (weather_boost / 100.0)
    final_omega = (final_omega - (opp_pitcher_alpha - 80.0) * 0.5 if opp_pitcher_alpha > 80.0 else final_omega) * umpire_factor * env_synergy

    if is_opp_debut:
        final_omega *= 1.10

    ud_penalty = 0.0
    od_boost = 0.0
    if under_divergence >= 15: ud_penalty = 0.15
    elif under_divergence >= 10: ud_penalty = 0.05
    if over_divergence >= 15: od_boost = 8.0
    elif over_divergence >= 8: od_boost = 5.0

    final_omega = max(0.0, (final_omega + od_boost) * (1.0 - ud_penalty))

    if is_sneaky:
        final_omega += 4.0

    sharp_boost = 0.0
    if is_pinnacle_offense_boost: sharp_boost += 2.0
    if is_velocity_boost: sharp_boost += 3.0
    final_omega += sharp_boost

    return round(min(150.0, final_omega), 1)


# ─────────────────────────────────────────────────────────────
# 3. PRE-LOAD HISTORICAL DATA
# ─────────────────────────────────────────────────────────────

def load_all_slates(start_str, end_str):
    archive_dir = os.path.join(config.REPORTS_DIR, "archive")
    start = datetime.strptime(start_str, "%Y-%m-%d")
    end = datetime.strptime(end_str, "%Y-%m-%d")
    
    slates = []
    current = start
    while current <= end:
        date_str = current.strftime("%Y-%m-%d")
        
        lock_path = os.path.join(archive_dir, f"results_{date_str}_lock.json")
        base_path = os.path.join(archive_dir, f"results_{date_str}.json")
        archive_path = lock_path if os.path.exists(lock_path) else base_path
        
        actuals_path = os.path.join(archive_dir, f"actuals_cache_{date_str}.json")
        
        if os.path.exists(archive_path) and os.path.exists(actuals_path):
            with open(archive_path, 'r', encoding='utf-8') as f:
                projections = json.load(f)
            with open(actuals_path, 'r', encoding='utf-8') as f:
                actuals = json.load(f)
                
            slates.append({
                "date": date_str,
                "projections": projections,
                "actuals": actuals
            })
        current += timedelta(days=1)
        
    print(f"Loaded {len(slates)} slates from {start_str} to {end_str} for parameter backtesting.")
    return slates


# ─────────────────────────────────────────────────────────────
# 4. SWEEP CORE PIPELINE
# ─────────────────────────────────────────────────────────────

def evaluate_parameters(slates, is_sharp_in_alpha, sharp_bonus, is_steam_in_alpha, is_whale_standalone, keep_shark_storm, vet_paradox, non_vet_paradox):
    total_stacks = 0
    stack_hits = 0
    
    total_pitchers = 0
    pitcher_hits = 0
    
    for slate in slates:
        projections = slate["projections"]
        actuals = slate["actuals"]
        
        teams = projections.get("teams", [])
        pitchers = projections.get("pitchers", [])
        
        if not teams or not pitchers:
            continue
            
        # Re-map pitchers for quick lookup
        pitchers_by_team = {p["team"]: p for p in pitchers}
        
        # 1. Recompute and re-rank stacks
        recomputed_teams = []
        for team_data in teams:
            team_name = team_data["team"]
            opponent = team_data["opponent"]
            opp_sp = pitchers_by_team.get(opponent)
            
            new_score = calculate_stack_score_parameterized(
                team_data, opp_sp,
                is_sharp_in_alpha, sharp_bonus, is_steam_in_alpha, is_whale_standalone, keep_shark_storm
            )
            recomputed_teams.append({
                "team": team_name,
                "score": new_score
            })
            
        # Sort stacks descending
        recomputed_teams.sort(key=lambda x: x["score"], reverse=True)
        top3_stacks = [t["team"] for t in recomputed_teams[:3]]
        
        # Evaluate stack hits (4+ actual runs)
        for t_name in top3_stacks:
            actual_team = actuals.get(t_name, {})
            runs = actual_team.get("runs")
            if runs is not None:
                total_stacks += 1
                if runs >= 4:
                    stack_hits += 1
                    
        # 2. Recompute and re-rank pitchers
        recomputed_pitchers = []
        for p in pitchers:
            p_name = p["pitcher"]
            team_name = p["team"]
            opponent = p["opponent"]
            siera = float(p.get("siera", 4.10) or 4.10)
            
            # Reconstruct unpenalized alpha score
            alpha = p["alpha_score"]
            is_paradox = bool(p.get("is_paradox", False))
            
            unpenalized_alpha = alpha
            if is_paradox:
                # Determine old penalty used
                is_veteran = siera < 3.80
                old_penalty = 0.96 if is_veteran else 0.92
                unpenalized_alpha = alpha / old_penalty
                
            # Apply new paradox check against our NEW top-3 stacks
            new_is_paradox = opponent in top3_stacks
            new_alpha = unpenalized_alpha
            if new_is_paradox:
                is_veteran = siera < 3.80
                penalty = vet_paradox if is_veteran else non_vet_paradox
                new_alpha = unpenalized_alpha * penalty
                
            recomputed_pitchers.append({
                "pitcher": p_name,
                "team": team_name,
                "alpha_score": round(new_alpha, 1)
            })
            
        # Sort pitchers descending
        recomputed_pitchers.sort(key=lambda x: x["alpha_score"], reverse=True)
        top3_pitchers = recomputed_pitchers[:3]
        
        # Evaluate pitcher hits (based on boxscore stats)
        for p in top3_pitchers:
            team_name = p["team"]
            proj_name = p["pitcher"]
            
            actual_team = actuals.get(team_name, {})
            sp_stats = actual_team.get("sp_stats", {})
            status = actual_team.get("status", "Unknown")
            
            # Check scratched status
            from utils.normalization import normalize_player_name
            norm_proj = normalize_player_name(proj_name)
            norm_act = normalize_player_name(sp_stats.get('name', ''))
            
            is_scratched = norm_proj != norm_act
            
            if status == "Final" and not is_scratched:
                total_pitchers += 1
                
                # Success criteria (high K, dominant IP, or Quality Start base)
                ip_raw = sp_stats.get('ip', "0.0")
                try: ip = float(ip_raw)
                except: ip = 0.0
                k = sp_stats.get('k', 0)
                er = sp_stats.get('er', 0)
                
                high_k = (k >= 6 and er <= 2)
                dominant_ip = (ip >= 6.0 and er <= 1)
                qs_base = (ip >= 6.0 and er <= 3 and k >= 5)
                
                success = high_k or dominant_ip or qs_base
                if success:
                    pitcher_hits += 1
                    
    stack_rate = stack_hits / total_stacks if total_stacks > 0 else 0.0
    pitcher_rate = pitcher_hits / total_pitchers if total_pitchers > 0 else 0.0
    
    return stack_rate, pitcher_rate, total_stacks, total_pitchers


# ─────────────────────────────────────────────────────────────
# 5. GRID SEARCH MAIN
# ─────────────────────────────────────────────────────────────

def main():
    start_date = "2026-05-04"
    end_date = "2026-06-12"
    slates = load_all_slates(start_date, end_date)
    
    if not slates:
        print("No slate data found. Exiting.")
        return
        
    # Baseline comparison (Current Production params)
    # is_sharp_in_alpha=False, sharp_bonus=0.025, is_steam_in_alpha=True, is_whale_standalone=False, keep_shark_storm=True
    # vet_paradox=0.96, non_vet_paradox=0.92
    base_stack_r, base_pitcher_r, total_s, total_p = evaluate_parameters(
        slates,
        is_sharp_in_alpha=False, sharp_bonus=0.025, is_steam_in_alpha=True,
        is_whale_standalone=False, keep_shark_storm=True,
        vet_paradox=0.96, non_vet_paradox=0.92
    )
    print(f"\n==========================================")
    print(f" PRODUCTION BASELINE PERFORMANCE:")
    print(f"==========================================")
    print(f"  Top 3 Stacks Hit Rate (4+ runs): {base_stack_r * 100:.2f}% ({int(base_stack_r * total_s)}/{total_s})")
    print(f"  Top 3 Pitchers Success Rate:     {base_pitcher_r * 100:.2f}% ({int(base_pitcher_r * total_p)}/{total_p})")
    print(f"==========================================\n")

    # Sweep Space definitions
    sharp_configs = [
        # (is_sharp_in_alpha, sharp_bonus)
        (False, 0.025), # Baseline
        (True, 0.0),    # Just move to Alpha, no bonus
        (True, 0.025),  # Move to Alpha + 2.5% bonus
        (True, 0.05),   # Move to Alpha + 5.0% bonus
    ]
    steam_configs = [True, False] # True = Alpha, False = Beta
    whale_configs = [False, True] # False = conditional, True = standalone
    shark_storm_configs = [True, False] # True = keep, False = remove
    
    vet_paradox_configs = [0.95, 0.96, 0.97, 0.98, 0.99, 1.00]
    non_vet_paradox_configs = [0.90, 0.92, 0.94, 0.95, 0.96, 0.98, 1.00]
    
    best_joint_rate = 0.0
    best_config = None
    
    print("Running grid search sweep over 2,688 parameter combinations...")
    count = 0
    results = []
    
    for (sharp_alpha, s_bonus) in sharp_configs:
        for steam_alpha in steam_configs:
            for whale_std in whale_configs:
                for keep_ss in shark_storm_configs:
                    for vet_p in vet_paradox_configs:
                        for non_vet_p in non_vet_paradox_configs:
                            
                            stack_r, pitch_r, _, _ = evaluate_parameters(
                                slates,
                                is_sharp_in_alpha=sharp_alpha,
                                sharp_bonus=s_bonus,
                                is_steam_in_alpha=steam_alpha,
                                is_whale_standalone=whale_std,
                                keep_shark_storm=keep_ss,
                                vet_paradox=vet_p,
                                non_vet_paradox=non_vet_p
                            )
                            
                            joint_score = stack_r + pitch_r
                            
                            results.append({
                                "sharp_alpha": sharp_alpha,
                                "sharp_bonus": s_bonus,
                                "steam_alpha": steam_alpha,
                                "whale_std": whale_std,
                                "keep_ss": keep_ss,
                                "vet_p": vet_p,
                                "non_vet_p": non_vet_p,
                                "stack_rate": stack_r,
                                "pitcher_rate": pitch_r,
                                "joint_score": joint_score
                            })
                            
                            if joint_score > best_joint_rate:
                                best_joint_rate = joint_score
                                best_config = results[-1]
                                
                            count += 1
                            if count % 500 == 0:
                                print(f"  Processed {count}/2688 combinations...")
                                
    print(f"\nSweep completed! Evaluated {count} combinations.\n")
    
    # Sort results to get top combinations
    results.sort(key=lambda x: x["joint_score"], reverse=True)
    
    print("==========================================")
    print(" TOP 5 OPTIMIZED PARAMETER CONFIGURATIONS:")
    print("==========================================")
    for idx, r in enumerate(results[:5]):
        print(f"\n#{idx+1} Config (Joint Score: {r['joint_score']*100:.2f}%):")
        print(f"  - Sharp in Alpha:  {r['sharp_alpha']} (Bonus: +{r['sharp_bonus']*100:.1f}%)")
        print(f"  - Steam in Alpha:  {r['steam_alpha']} (if False, moved to Beta)")
        print(f"  - Whale Standalone: {r['whale_std']}")
        print(f"  - Keep Shark/Storm: {r['keep_ss']}")
        print(f"  - Paradox Penalty:  Vet={r['vet_p']:.2f} | Non-Vet={r['non_vet_p']:.2f}")
        print(f"  - Result: Stacks Hit = {r['stack_rate']*100:.2f}% | Pitchers Hit = {r['pitcher_rate']*100:.2f}%")
        
    print("\n==========================================")
    
    # Save the full results to a JSON file for validation and recording
    output_path = os.path.join(config.REPORTS_DIR, "parameter_sweep_results.json")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(results[:100], f, indent=4) # Save top 100 configs
    print(f"Top 100 parameter configs saved to {output_path}")

if __name__ == "__main__":
    main()
