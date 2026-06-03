from datetime import datetime
from config import config
from engine.constants import *

class SharpsWeighting:
    def __init__(self):
        # User defined thresholds
        self.ML_MOVE_MIN = 10  # 10 cents
        self.TT_MOVE_MIN = 0.3 # 0.3 runs
        self.PUBLIC_BET_MAX = 50 # 50%
        self.bullpen_talent_grades = {
            # Tier 1: Elite (Fatigue matters less, very tough bullpen)
            'Cleveland Guardians': {'grade': 'Elite', 'multiplier': 0.90, 'fatigue_mod': 0.75},
            'Milwaukee Brewers': {'grade': 'Elite', 'multiplier': 0.90, 'fatigue_mod': 0.75},
            'San Diego Padres': {'grade': 'Elite', 'multiplier': 0.92, 'fatigue_mod': 0.80},
            'Seattle Mariners': {'grade': 'Elite', 'multiplier': 0.92, 'fatigue_mod': 0.80},
            
            # Tier 2: Strong (Good depth, strong leverage arms)
            'New York Yankees': {'grade': 'Strong', 'multiplier': 0.95, 'fatigue_mod': 0.85},
            'Atlanta Braves': {'grade': 'Strong', 'multiplier': 0.95, 'fatigue_mod': 0.85},
            'Los Angeles Dodgers': {'grade': 'Strong', 'multiplier': 0.95, 'fatigue_mod': 0.85},
            'Philadelphia Phillies': {'grade': 'Strong', 'multiplier': 0.96, 'fatigue_mod': 0.88},
            'Baltimore Orioles': {'grade': 'Strong', 'multiplier': 0.96, 'fatigue_mod': 0.88},
            'Minnesota Twins': {'grade': 'Strong', 'multiplier': 0.97, 'fatigue_mod': 0.90},
            'Houston Astros': {'grade': 'Strong', 'multiplier': 0.97, 'fatigue_mod': 0.90},
            
            # Tier 3: Average (Neutral/Standard)
            'Chicago Cubs': {'grade': 'Average', 'multiplier': 1.00, 'fatigue_mod': 1.00},
            'New York Mets': {'grade': 'Average', 'multiplier': 1.00, 'fatigue_mod': 1.00},
            'Texas Rangers': {'grade': 'Average', 'multiplier': 1.00, 'fatigue_mod': 1.00},
            'Boston Red Sox': {'grade': 'Average', 'multiplier': 1.00, 'fatigue_mod': 1.00},
            'San Francisco Giants': {'grade': 'Average', 'multiplier': 1.00, 'fatigue_mod': 1.00},
            'Tampa Bay Rays': {'grade': 'Average', 'multiplier': 1.02, 'fatigue_mod': 1.02},
            'Arizona Diamondbacks': {'grade': 'Average', 'multiplier': 1.02, 'fatigue_mod': 1.02},
            'Cincinnati Reds': {'grade': 'Average', 'multiplier': 1.03, 'fatigue_mod': 1.03},
            'Kansas City Royals': {'grade': 'Average', 'multiplier': 1.03, 'fatigue_mod': 1.03},
            'St. Louis Cardinals': {'grade': 'Average', 'multiplier': 1.04, 'fatigue_mod': 1.04},
            'Pittsburgh Pirates': {'grade': 'Average', 'multiplier': 1.04, 'fatigue_mod': 1.04},
            
            # Tier 4: Below Average (Vulnerable depth, easily fatigued)
            'Detroit Tigers': {'grade': 'Below Average', 'multiplier': 1.06, 'fatigue_mod': 1.10},
            'Washington Nationals': {'grade': 'Below Average', 'multiplier': 1.07, 'fatigue_mod': 1.12},
            'Toronto Blue Jays': {'grade': 'Below Average', 'multiplier': 1.08, 'fatigue_mod': 1.15},
            'Los Angeles Angels': {'grade': 'Below Average', 'multiplier': 1.09, 'fatigue_mod': 1.15},
            'Oakland Athletics': {'grade': 'Below Average', 'multiplier': 1.10, 'fatigue_mod': 1.18},
            'Athletics': {'grade': 'Below Average', 'multiplier': 1.10, 'fatigue_mod': 1.18},
            
            # Tier 5: Weak (Extremely thin, fatigue is devastating)
            'Colorado Rockies': {'grade': 'Weak', 'multiplier': 1.15, 'fatigue_mod': 1.25},
            'Chicago White Sox': {'grade': 'Weak', 'multiplier': 1.15, 'fatigue_mod': 1.25},
            'Miami Marlins': {'grade': 'Weak', 'multiplier': 1.15, 'fatigue_mod': 1.25}
        }

        
    def calculate_pitcher_score(self, name, ml_move, tt_move, money_gap, k_prop, siera=4.10, csw=0.25, is_target=False, park_factor=100, divergence=0, is_shark=False, is_whale=False, opponent_k_boost=0, is_low_ceiling=False, projected_outs=18.0, is_trap=False, is_sharp=False, curr_ml=-110, walks_line=None, walks_odds=None, is_death_sentence=False, form_boost=0.0, pinnacle_boost_active=False):
        """
        OMEGA v10.0 SE: Tiered Alpha/Beta Pitcher Scoring (Win Prob Base Market).
        """
        # Defensive Input Normalization
        siera = float(siera) if siera is not None else 4.10
        csw = float(csw) if csw is not None else 0.25
        ml_move = float(ml_move) if ml_move is not None else 0.0
        tt_move = float(tt_move) if tt_move is not None else 0.0
        divergence = float(divergence) if divergence is not None else 0.0
        curr_ml = float(curr_ml) if curr_ml is not None else -110.0
        park_factor = float(park_factor) if park_factor is not None and park_factor != 0 else 100.0
        projected_outs = float(projected_outs) if projected_outs is not None else 18.0
        opponent_k_boost = float(opponent_k_boost) if opponent_k_boost is not None else 0.0

        s_score = max(0.0, min(100.0, (6.0 - siera) * 20.0))
        c_score = max(0.0, min(100.0, (csw / 0.35) * 100.0))
        physics_raw_base = (s_score + c_score) / 2.0
        
        # OMEGA v6.2.5: The Pure Talent Gate
        gate_active = physics_raw_base < 55.0
        
        # OMEGA v7.6: The 'Neutral K-Zone'
        k_mod = opponent_k_boost if abs(opponent_k_boost) > 3.0 else 0.0
        env_mod = (100.0 - park_factor + k_mod) / 100.0
        physics_raw = physics_raw_base * (1.0 + env_mod)
        
        # OMEGA v10.0: Market Win Probability Base
        def _ml_to_prob(ml):
            if ml == 0: return 0.5
            if ml < 0: return abs(ml) / (abs(ml) + 100.0)
            return 100.0 / (ml + 100.0)
            
        win_prob = _ml_to_prob(curr_ml)
        # Scale probability from 30% to 80% -> 0 to 100 (expanded linear scale)
        base_market_score = max(0.0, min(100.0, ((win_prob - 0.30) / 0.50) * 100.0))
        
        ml_score = max(0.0, min(100.0, (abs(ml_move) / 20.0) * 100.0)) if ml_move < 0 else 0.0
        tt_score = max(0.0, min(100.0, (abs(tt_move) / 0.7) * 100.0))
        
        market_raw = base_market_score + (ml_score * 0.20) + (tt_score * 0.20)
        market_raw = max(0.0, min(100.0, market_raw))
        
        # OMEGA v6.8.6: Talent-First Weighting
        score = 45.0 + (physics_raw * 0.45) + (market_raw * 0.20)
        
        if physics_raw_base >= 70.0:
            score += 15.0
        
        # OMEGA v6.1: Tiered Multipliers (Flattened v8.0)
        alpha_signals = 0
        beta_signals = 0
        
        if is_target and not gate_active: alpha_signals += 1
        
        # Group market signals to prevent double-counting
        # OMEGA v13.6: Removed is_whale (20.0% success rate)
        # OMEGA v13.7: Removed PITCHER_SHARK boost (0/7 hit rate; sharp team money != pitcher signal)
        market_whale_bonus = 0.0
        
        try:
            if k_prop is not None and float(k_prop) >= 6.5: beta_signals += 1
        except (ValueError, TypeError):
            pass

        if abs(tt_move) >= 0.5: beta_signals += 1
        if divergence >= 10.0: beta_signals += 1
        
        multiplier = 1.0 + (alpha_signals * 0.15) + (beta_signals * 0.05) + market_whale_bonus
            
        if park_factor >= 114.0:
            multiplier -= 0.20
            
        # Cap div boost at 10%
        div_boost = 1.0 + min(0.10, (max(0.0, divergence) / 150.0))
        
        volume_factor = min(1.0, projected_outs / 18.0)
        
        # OMEGA v7.8: Prop Trap Penalty (-15% baseline, -20% against strong offenses)
        if is_trap:
            trap_multiplier = 0.80 if opponent_k_boost < 5.0 else 0.85
        else:
            trap_multiplier = 1.0

        # OMEGA v8.5: The 'Institutional Anchor' (Market Fade)
        # If divergence is negative (market fading) and it's a high-alpha target,
        # apply a multiplicative penalty to simulate institutional skepticism.
        market_anchor = 1.0
        if divergence < -10.0 and physics_raw_base > 60.0 and is_trap:
            market_anchor = 0.90 # -10% institutional anchor
            
        # OMEGA v8.7.7: Pitcher Sharp Premium (+7.5%)
        sharp_multiplier = 1.075 if is_sharp else 1.0
            
        final_alpha = score * multiplier * div_boost * volume_factor * trap_multiplier * market_anchor * sharp_multiplier
        
        if is_low_ceiling and not is_target:
            final_alpha *= 0.90
            
        # 1. Calibrated Walks Penalty (-10.0 points)
        walks_penalty = 0.0
        if walks_line is not None:
            is_high_walks = False
            try:
                wf = float(walks_line)
                if wf >= 2.5:
                    is_high_walks = True
                elif wf >= 1.5 and walks_odds is not None:
                    wo = float(walks_odds)
                    if wo < 0:
                        is_high_walks = True
            except:
                pass
            if is_high_walks:
                walks_penalty = -10.0

        # 2. True Talent Sabermetrics Penalty (-15.0 points)
        true_talent_penalty = 0.0
        try:
            from utils.normalization import normalize_player_name
            import json
            import os
            cache_path = os.path.join(config.DATA_DIR, "statcast_cache.json")
            if os.path.exists(cache_path):
                with open(cache_path, 'r') as f:
                    cache = json.load(f)
                p_norm = normalize_player_name(name)
                p_profile = cache.get(p_norm, {})
                if p_profile and p_profile.get("type") == "pitcher":
                    ip = float(p_profile.get("ip", 0.0))
                    bb = float(p_profile.get("bb", 0.0))
                    k = float(p_profile.get("k", 0.0))
                    hr = float(p_profile.get("hr", 0.0))
                    
                    bf = ip * 2.9 + k + bb
                    k_bb_pct = (k - bb) / bf if bf > 0 else 0.12
                    hr_9 = (hr / ip * 9) if ip > 5.0 else 1.0
                    
                    if k_bb_pct < 0.14 and hr_9 > 1.4:
                        true_talent_penalty = -15.0
        except:
            pass

        final_alpha += walks_penalty + true_talent_penalty
        
        # Apply death sentence penalty (-15%)
        if is_death_sentence:
            final_alpha *= 0.85
            
        # Apply Pinnacle SP boost (+5.0 engine points)
        if pinnacle_boost_active:
            final_alpha += 5.0
            
        # Apply recent form boost
        final_alpha += form_boost
            
        return {
            "final": round(final_alpha, 1),
            "physics": round(physics_raw * 0.45, 1),
            "physics_talent": round(min(100.0, physics_raw), 1),
            "market": round(market_raw * 0.20, 1),
            "csw": round(float(csw), 3),
            "is_coors": park_factor >= 114,
            "is_trap": is_trap,
            "walks_penalty": walks_penalty < 0,
            "true_talent_penalty": true_talent_penalty < 0
        }

    def calculate_stack_score(self, team, ml_move, tt_move, curr_itt=4.5, team_xwoba=0.330, power_concentration=0.330, park_factor=1.0, bullpen_fatigue=0, divergence=0, is_whale=False, is_sharp=False, is_storm=False, is_shark=False, is_steam=False, opp_pitcher_physics=0, confidence='high', pitcher_outs=18.0, implied_total=None, is_burst=False, opponent=None, is_anti_chalk_smash=False, is_pitch_alignment=False, opp_pitcher_trap=False, opp_pitcher_name=None, opp_walks_line=None, opp_walks_odds=None, opp_er_line=None, opp_er_odds=None, umpire_factor=1.0, weather_boost=0.0, opp_pitcher_alpha=0.0, is_opp_debut=False, over_divergence=0, under_divergence=0, is_sneaky=False, is_pinnacle_offense_boost=False, is_velocity_boost=False):
        """OMEGA v9.8: Tiered Alpha/Beta Stack Scoring (Physics 2.0 Hardened)."""
        # Defensive Input Normalization
        team_xwoba = float(team_xwoba) if team_xwoba is not None else 0.330
        power_concentration = float(power_concentration) if power_concentration is not None else 0.330
        curr_itt = float(curr_itt) if curr_itt is not None else 4.5
        implied_total = float(implied_total) if implied_total is not None else curr_itt
        park_factor = float(park_factor) if park_factor is not None else 1.0
        bullpen_fatigue = float(bullpen_fatigue) if bullpen_fatigue is not None else 0.0
        ml_move = float(ml_move) if ml_move is not None else 0.0
        tt_move = float(tt_move) if tt_move is not None else 0.0
        divergence = float(divergence) if divergence is not None else 0.0
        opp_pitcher_physics = float(opp_pitcher_physics) if opp_pitcher_physics is not None else 50.0
        pitcher_outs = float(pitcher_outs) if pitcher_outs is not None else 18.0
        umpire_factor = float(umpire_factor) if umpire_factor is not None else 1.0
        weather_boost = float(weather_boost) if weather_boost is not None else 0.0
        opp_pitcher_alpha = float(opp_pitcher_alpha) if opp_pitcher_alpha is not None else 0.0
        over_divergence = float(over_divergence) if over_divergence is not None else 0.0
        under_divergence = float(under_divergence) if under_divergence is not None else 0.0

        # Resolve Dynamic Bullpen Grade
        dyn_grade, dyn_mult, dyn_fatigue_mod = "Average", 1.00, 1.00
        if opponent:
            try:
                import json
                import os
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
                            dyn_grade, dyn_mult, dyn_fatigue_mod = "Elite", 0.90, 0.75
                        elif score_val >= 48.0:
                            dyn_grade, dyn_mult, dyn_fatigue_mod = "Strong", 0.95, 0.85
                        elif score_val >= 35.0:
                            dyn_grade, dyn_mult, dyn_fatigue_mod = "Average", 1.00, 1.00
                        elif score_val >= 22.0:
                            dyn_grade, dyn_mult, dyn_fatigue_mod = "Below Average", 1.07, 1.12
                        else:
                            dyn_grade, dyn_mult, dyn_fatigue_mod = "Weak", 1.15, 1.25
            except:
                pass

        # OMEGA v7.7: Physics Hardening (Hybrid Statcast + Market ITT)
        # OMEGA v7.0: Power Concentration (Burst Potential)
        effective_physics = (team_xwoba * 0.4) + (power_concentration * 0.6)
        physics_raw = (effective_physics - 0.260) / (0.400 - 0.260) * 100
        physics_raw = max(0.0, min(100.0, physics_raw))
        # PARK_FACTORS are run multipliers (~0.92–1.15), not percentage points
        pf = float(park_factor or 1.0)
        if pf > 3.0:
            pf = 1.0 + (pf / 100.0)
        physics_raw = min(120.0, physics_raw * pf)

        # OMEGA v8.7: Linear Fatigue Pressure (Sliding Scale v1.0)
        # Pressure starts building at 65% instead of a hard cliff at 80%
        fatigue_floor = 65.0
        bullpen_boost = max(0.0, (bullpen_fatigue - fatigue_floor) / 2.5)  # OMEGA v15.0: Steeper fatigue ramp (was /3.5)
        
        # Soft starter hook multipliers to prevent over-aggression
        # If the opposing SP is a TRAP, force short leash (15.5 outs) to boost bullpen pressure
        effective_outs = 15.5 if opp_pitcher_trap else pitcher_outs
        if effective_outs <= 15.5:
            bullpen_boost *= 1.20 # Soft 20% boost for short leash
        elif effective_outs >= 18.0:
            bullpen_boost *= 0.85 # Soft 15% dampener for deep workhorse starters
            
        # OMEGA v13.5: Bullpen Skill Granularity for Fatigue Boost (Overhauled)
        skill_modifier = dyn_fatigue_mod
        bullpen_boost *= skill_modifier
        
        bullpen_boost = min(25.0, bullpen_boost)  # OMEGA v15.0: Higher cap (was 15.0 pts, now 25.0)

        # OMEGA v8.9: Absolute-Delta Hybrid Market Pillar
        # Incorporate absolute Vegas ITT (scale 3.0 to 5.5 -> 0 to 100 pts) so flat high-total stacks are rewarded
        eff_itt = implied_total if implied_total is not None else curr_itt
        base_market_score = max(0.0, min(100.0, ((eff_itt - 3.0) / 2.5) * 100.0))
        
        # Calculate delta-based movement scores
        ml_score = max(0.0, min(100.0, (abs(ml_move) / 20.0) * 100.0)) if ml_move < 0 else 0.0
        tt_score = max(0.0, min(100.0, (tt_move / 0.5) * 100.0)) if tt_move > 0 else 0.0
        
        # OMEGA v10.0: Base + Bonus Model
        # Base is the implied total. Movement acts as an additive bonus rather than averaging out.
        market_raw = base_market_score + (ml_score * 0.25) + (tt_score * 0.25)
        market_raw = max(0.0, min(120.0, market_raw))

        # OMEGA v6.9: Pitcher Vulnerability
        vulnerability_mod = (100.0 - opp_pitcher_physics) / 5.0 

        # OMEGA v15.0: Regression-Optimal Weights (Physics 80% | Market 20% | Baseline 40.0)
        # Rationale: OLS Market:Physics optimal ratio is 1.0:8.20 (was 1.0:3.57).
        # vulnerability_mod REMOVED: Pitcher quality is priced into Vegas ITT (r=+0.226 proven).
        score = 40.0 + (physics_raw * 0.80) + (market_raw * 0.20) + bullpen_boost
        
        alpha_signals = 0
        beta_signals = 0
        
        # Alpha (Market Convergence Grouping to prevent exponential stacking)
        market_alphas = 0
        # OMEGA v13.6.2: Re-enabled is_whale for stacks because the threshold has been optimized to >=25% divergence (40.9% success rate)
        if is_whale: market_alphas += 1
        # OMEGA v15.0: is_shark MOVED to beta_signals (r=-0.0879 in 2026; dampened to +5% instead of +15%)
        if is_steam: market_alphas += 1
        
        # Flatten: Group all market alphas into a max of 1 signal (+15%), 
        # but keep the convergence bonus if 3+ agree
        if market_alphas > 0:
            alpha_signals += 1
            
        convergence_boost = 1.0
        if market_alphas >= 3:
            convergence_boost = 1.10
        

        # Beta
        if is_sharp: beta_signals += 1
        if is_burst: beta_signals += 1
        if tt_move > 0.5: beta_signals += 1
        if bullpen_fatigue >= 65: beta_signals += 1
        if is_shark: beta_signals += 1  # OMEGA v15.0: Demoted from alpha (+15%) to beta (+5%)
        if is_storm: beta_signals += 1  # OMEGA v16.0: Demoted from alpha (+15%) to beta (+5%)
        
        # OMEGA v8.9: Strategy 2 - The 'Statcast Anchor Curve' (Market Dampening)
        # Low-power contact offenses (xwOBA < 0.295) get their market signal premiums
        # dynamically dampened to prevent bet-volume spikes (traps) from overtaking physical capability.
        anchor_ratio = 1.0
        if team_xwoba < 0.295:
            anchor_ratio = max(0.75, (team_xwoba / 0.295) ** 2.0)

        # Multiplier Calculation: Alpha (+15%), Beta (+5%)
        # OMEGA v8.7.7: 'Balanced Sharp Premium' (+7.5% for Smart Money)
        market_premium = (alpha_signals * 0.15) + (beta_signals * 0.05)
        if is_sharp:
            market_premium += 0.025 # Add 2.5% specifically for Sharp (Total 7.5% boost)
            
        # Apply the Statcast Anchor dampener to the market premium!
        dampened_market_premium = market_premium * anchor_ratio
        multiplier = 1.0 + dampened_market_premium
        
        # OMEGA v6.7: The 'Detmers Patch' (Stopper Penalty Refined)
        if opp_pitcher_physics > 85 or (is_storm and opp_pitcher_physics > 70):
            multiplier -= 0.10 
        
        # Dynamic Divergence Multiplier: Capped at 10%
        div_premium = min(0.10, (max(0, divergence) / 150.0))
        dampened_div_premium = div_premium * anchor_ratio
        div_multiplier = 1.0 + dampened_div_premium
        
        # OMEGA v9.8: Matchup Magnetism with cap and talent dampening
        # If opposing pitcher physics is extremely low (below 20.0), we apply a matchup boost.
        # We cap the raw boost at 1.30 (max 30% boost) and scale it by the team's anchor_ratio 
        # to ensure weak offenses don't over-inflate.
        magnetism_boost = 1.0
        if opp_pitcher_physics < 20.0:
            vulnerability_gap = (20.0 - opp_pitcher_physics) / 10.0
            fatigue_boost = 1.0 + (bullpen_fatigue / 100.0) * 0.30
            raw_magnetism = 1.0 + 0.20 + (vulnerability_gap ** 1.0) * 0.50 * fatigue_boost
            raw_magnetism_capped = min(1.30, raw_magnetism)
            magnetism_boost = 1.0 + (raw_magnetism_capped - 1.0) * anchor_ratio

        # OMEGA v9.8: Bullpen Skill Grades (Overhauled)
        bullpen_skill_mult = dyn_mult

        pre_trap_combined = (
            multiplier * div_multiplier * convergence_boost * magnetism_boost * bullpen_skill_mult
        )
        pre_trap_combined = min(pre_trap_combined, 1.35)
        pre_trap_score = score * pre_trap_combined
        physics_display = physics_raw * 0.40

        chalk_trap = self._stack_chalk_trap(
            physics_raw=physics_raw,
            team_xwoba=team_xwoba,
            physics_display=physics_display,
            ml_move=ml_move,
            divergence=divergence,
            is_steam=is_steam,
            is_shark=is_shark,
            pre_trap_score=pre_trap_score,
        )
        trap_multiplier = 0.90 if chalk_trap else 1.0

        combined = min(pre_trap_combined * trap_multiplier, 1.35)
        final_omega = score * combined

        # OMEGA v15.2: Gassed Bullpen Attack Premium (Optimized)
        # If opponent bullpen is tired (>= 75), starter is on a short leash (<= 15.5 outs),
        # and attacking team has solid offensive baseline (xwOBA >= 0.315).
        is_gassed_attack = (bullpen_fatigue >= 75) and (pitcher_outs <= 15.5) and (team_xwoba >= 0.315)
        if is_gassed_attack:
            final_omega += 8.0  # OMEGA v15.0: Increased from +5.0 to +8.0 (r=+0.1270 strongest positive predictor)

        # Inject GPP Decision Intelligence bonuses directly to OMEGA master score
        if is_anti_chalk_smash:
            final_omega += 10.0  # OMEGA v15.0: Increased from +5.0 to +10.0 (highest regression weight binary: +3.139 expected runs)
        if is_pitch_alignment:
            final_omega += 4.0

        # Walks Stack Boost (+8.0 points)
        walks_boost = 0.0
        if opp_walks_line is not None:
            is_high_walks = False
            try:
                wf = float(opp_walks_line)
                if wf >= 2.5:
                    is_high_walks = True
                elif wf >= 1.5 and opp_walks_odds is not None:
                    wo = float(opp_walks_odds)
                    if wo < 0:
                        is_high_walks = True
            except:
                pass
            if is_high_walks:
                walks_boost = 8.0

        # Earned Runs Stack Boost (+8.0 points)
        er_boost = 0.0
        if opp_er_line is not None:
            is_high_er = False
            try:
                ef = float(opp_er_line)
                if ef >= 3.5:
                    is_high_er = True
                elif ef >= 2.5 and opp_er_odds is not None:
                    eo = float(opp_er_odds)
                    if eo < 0:
                        is_high_er = True
            except:
                pass
            if is_high_er:
                er_boost = 8.0

        # True Talent Opp Pitcher Stack Boost (+2.0 points)
        true_talent_boost = 0.0
        if opp_pitcher_name:
            try:
                from utils.normalization import normalize_player_name
                import json
                import os
                cache_path = os.path.join(config.DATA_DIR, "statcast_cache.json")
                if os.path.exists(cache_path):
                    with open(cache_path, 'r') as f:
                        cache = json.load(f)
                    p_norm = normalize_player_name(opp_pitcher_name)
                    p_profile = cache.get(p_norm, {})
                    if p_profile and p_profile.get("type") == "pitcher":
                        ip = float(p_profile.get("ip", 0.0))
                        bb = float(p_profile.get("bb", 0.0))
                        k = float(p_profile.get("k", 0.0))
                        hr = float(p_profile.get("hr", 0.0))
                        
                        bf = ip * 2.9 + k + bb
                        k_bb_pct = (k - bb) / bf if bf > 0 else 0.12
                        hr_9 = (hr / ip * 9) if ip > 5.0 else 1.0
                        
                        if k_bb_pct < 0.14 and hr_9 > 1.4:
                            true_talent_boost = 2.0
            except:
                pass

        final_omega += walks_boost + er_boost + true_talent_boost

        if team_xwoba < 0.295 and dampened_market_premium > 0.10:
            final_omega = min(final_omega, score * (1.0 + min(0.22, dampened_market_premium)))
        
        # OMEGA v7.3: ITT Sanity Gate (Refined to trust sharp leverage)
        # If Vegas says it's a low total, but sharps disagree (WHALE/STORM), we trust the sharps.
        # We only apply the penalty if there is no major sharp divergence backing them.
        is_sharp_backed = is_whale or is_storm or (divergence > 15)
        
        if eff_itt < 4.0 and final_omega > 90.0 and not is_sharp_backed:
            final_omega *= 0.85  
        elif eff_itt > 5.5 and final_omega < 70.0:
            final_omega *= 1.10  
        
        if confidence == 'low':
            final_omega = min(80.0, final_omega)
        
        # OMEGA v16.0 Consolidated Scoring Post-Processing:
        sentiment_mod = (umpire_factor or 1.0)
        env_synergy = 1.0 + (weather_boost / 100.0)
        
        dominance_penalty = 0.0
        if opp_pitcher_alpha > SP_DOMINANCE_THRESHOLD:
            dominance_penalty = (opp_pitcher_alpha - SP_DOMINANCE_THRESHOLD) * SP_DOMINANCE_FACTOR
            
        final_omega = (final_omega - dominance_penalty) * sentiment_mod * env_synergy
        
        if is_opp_debut:
            final_omega *= 1.10
            
        ud_penalty = 0.0
        od_boost = 0.0
        if under_divergence >= UNDER_DIVERGENCE_HIGH:
            ud_penalty = 0.15
        elif under_divergence >= UNDER_DIVERGENCE_LOW:
            ud_penalty = 0.05
            
        if over_divergence >= OVER_DIVERGENCE_HIGH:
            od_boost = 8.0
        elif over_divergence >= OVER_DIVERGENCE_LOW:
            od_boost = 5.0
            
        final_omega = max(0.0, (final_omega + od_boost) * (1.0 - ud_penalty))
        
        if is_sneaky:
            final_omega += SNEAKY_STACK_PREMIUM
            
        # Apply Pinnacle Offense Premium and moneyline velocity boosts
        # OMEGA v11.0
        from config import config
        sharp_boost = 0.0
        if is_pinnacle_offense_boost:
            sharp_boost += getattr(config, 'PINNACLE_OFFENSE_BOOST', 2.0)
        if is_velocity_boost:
            sharp_boost += getattr(config, 'VELOCITY_BOOST', 3.0)
        final_omega += sharp_boost

        final_omega_capped = min(150.0, final_omega)

        # OMEGA v9.9: GPP Leverage Fade Risk
        # If a team has a high implied total (>= 5.0) and negative divergence (< -10),
        # they represent public chalk being faded by sharps (high-ownership fade risk).
        is_fade_risk = (eff_itt >= 5.0) and (divergence < -10)
        
        return {
            "final": round(final_omega_capped, 1),
            "final_raw": round(final_omega, 1),
            "physics": round(physics_raw * 0.40, 1),
            "physics_raw": round(physics_raw, 1),
            "market": round(market_raw * 0.20, 1),
            "market_raw": round(market_raw, 1),
            "team_xwoba": round(team_xwoba, 3),
            "power_concentration": round(power_concentration, 3),
            "vulnerability": round(vulnerability_mod, 1),
            "bullpen_boost": round(bullpen_boost, 1),
            "volatility_hit": False,
            "convergence_boost": convergence_boost > 1.0,
            "confidence": confidence,
            "is_trap": chalk_trap,
            "is_stack_chalk": chalk_trap,
            "is_fade_risk": is_fade_risk,
            "bullpen_grade": dyn_grade,
            "walks_boost": walks_boost > 0,
            "er_boost": er_boost > 0,
            "true_talent_boost": true_talent_boost > 0,
            "is_pinnacle_offense_boost": is_pinnacle_offense_boost,
            "is_velocity_boost": is_velocity_boost
        }

    @staticmethod
    def _stack_chalk_trap(
        physics_raw,
        team_xwoba,
        physics_display,
        ml_move,
        divergence,
        is_steam,
        is_shark,
        pre_trap_score,
    ):
        """
        Package A: chalk-only stack warning — not sharp dog steam, not elite stacks.
        """
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


    def calculate_individual_hitter_score(self, player_name, team_score, matchup_xwoba, ahr_price, park_factor=1.0, is_target=False, is_speed_target=False, is_hot=False, protection_boost=1.0, vision_boost=1.0, opp_csw=0.0, matchup_radar_boost=1.0, pitch_hand=None, hitter_splits=None, smash_factor=False, pitcher_name=None, matchup_radar=None, walks_line=None, walks_price=None, strikeouts_line=None, strikeouts_price=None, runs_g_rbi_line=None, runs_g_rbi_price=None, hard_hit_pct=0.0, barrel_pct=0.0, hits_line=None, hits_price=None, form_boost=0.0):
        """
        OMEGA v6.22: Individual Hitter Alpha HARDENED.
        Combines Statcast xwOBA (Physics), AHR Pricing (Market), Team Context,
        and new Synergy Logic (Protection + Vision + MatchupRadar).
        OMEGA v9.5 splits update: Blends player vs LHP/RHP split ratios dynamically.
        """
        # Defensive Input Normalization
        team_score = float(team_score) if team_score is not None else 50.0
        matchup_xwoba = float(matchup_xwoba) if matchup_xwoba is not None else 0.310
        ahr_price = float(ahr_price) if ahr_price is not None else 450.0
        park_factor = float(park_factor) if park_factor is not None else 1.0
        protection_boost = float(protection_boost) if protection_boost is not None else 1.0
        vision_boost = float(vision_boost) if vision_boost is not None else 1.0
        opp_csw = float(opp_csw) if opp_csw is not None else 0.25
        matchup_radar_boost = float(matchup_radar_boost) if matchup_radar_boost is not None else 1.0
        hard_hit_pct = float(hard_hit_pct) if hard_hit_pct is not None else 0.0
        barrel_pct = float(barrel_pct) if barrel_pct is not None else 0.0

        platoon_multiplier = 1.0
        platoon_label = "Neutral"
        
        # Platoon Splits walk/strikeout rate adjustment (Package 3)
        bb_k_split_multiplier = 1.0
        if pitch_hand and hitter_splits:
            from utils.platoon_math import compute_platoon_multiplier
            from utils.xwoba_estimates import cap_matchup_xwoba

            opp_label = "LHP" if str(pitch_hand).upper() == "L" else "RHP"
            platoon_multiplier = compute_platoon_multiplier(
                hitter_splits, pitch_hand,
                hitter_name=player_name, pitcher_name=pitcher_name,
                matchup_radar=matchup_radar
            )
            platoon_percent = round((platoon_multiplier - 1.0) * 100)
            if abs(platoon_percent) >= 3:
                platoon_label = f"Blended vs {opp_label} ({'+' if platoon_percent >= 0 else ''}{platoon_percent}%)"
            else:
                platoon_label = f"Neutral vs {opp_label}"
                
            side = "left" if str(pitch_hand).upper() == "L" else "right"
            bb = float(hitter_splits.get(f"vs_{side}_bb", 0.0) or 0.0)
            k = float(hitter_splits.get(f"vs_{side}_k", 0.0) or 0.0)
            pa = float(hitter_splits.get(f"vs_{side}_pa", 0.0) or 0.0)
            
            if pa < 40.0:
                bb += float(hitter_splits.get(f"vs_{side}_bb_2025", 0.0) or 0.0)
                k += float(hitter_splits.get(f"vs_{side}_k_2025", 0.0) or 0.0)
                pa += float(hitter_splits.get(f"vs_{side}_pa_2025", 0.0) or 0.0)
                
            if pa > 10.0:
                bb_pct = bb / pa
                k_pct = k / pa
                if bb_pct >= 0.12:
                    bb_k_split_multiplier += 0.05
                if k_pct >= 0.28:
                    bb_k_split_multiplier -= 0.05
                    
            matchup_xwoba = matchup_xwoba * bb_k_split_multiplier

        # 1. Physics Pillar (xwOBA based: Scale 0.280 to 0.420 -> 0 to 50 pts)
        p_comp = max(0, min(50, ((matchup_xwoba - 0.280) / (0.420 - 0.280)) * 50))
        
        # 2. Market Pillar (AHR Price based: Scale 700 to 200 -> 0 to 50 pts)
        m_cap = 40 if ahr_price < -300 else 50
        m_comp = max(0, min(m_cap, ((700 - min(700, ahr_price)) / 500) * 50))
        
        # OMEGA v7.5 (Post-Mortem 5/6): The Abrams Patch (AHR Manipulation Floor)
        if p_comp >= 35.0: # Elite physics (xwOBA > ~0.380)
            m_comp = max(m_comp, 20.0)
        elif p_comp >= 25.0: # Strong physics (xwOBA > ~0.350)
            m_comp = max(m_comp, 10.0)
        
        # 3. Boost Coefficient (Targets, Momentum, and Vision)
        boost = 1.0
        if is_target: boost += 0.10
        if is_speed_target: boost += 0.05
        if is_hot: boost += 0.07
        if smash_factor:
            boost += 0.05
        
        # OMEGA v6.22: Vision Boost (K-rate discipline)
        boost *= vision_boost
        
        # Aggregated Individual Score (props + xwOBA + matchup; no team stack pull)
        individual_core = (p_comp + m_comp) * boost * matchup_radar_boost
        
        # OMEGA v7.3 (Post-Mortem 4/28): Opposing Pitcher CSW Gate
        if opp_csw > 0.32:
            individual_core *= 0.85  
        elif opp_csw > 0.28:
            individual_core *= 0.92  
        
        solo_score = max(0.0, individual_core * park_factor)

        # 4. Ingest new prop modifiers directly into solo_score (Package 1)
        walks_boost = 0.0
        if walks_line != '-' and walks_line is not None:
            try:
                wf = float(walks_line)
                wp = float(walks_price) if walks_price is not None else 0.0
                if wf >= 0.5 and (wp < 0 or wp >= 100): # Favored over
                    walks_boost = 3.0
            except:
                pass

        so_penalty = 0.0
        if strikeouts_line != '-' and strikeouts_line is not None:
            try:
                sf = float(strikeouts_line)
                sp = float(strikeouts_price) if strikeouts_price is not None else 0.0
                # Strikeout line >= 1.5 is high variance, or heavily juiced Over 0.5
                if sf >= 1.5 or (sf >= 0.5 and sp < -130):
                    so_penalty = -3.0
            except:
                pass

        rr_boost = 1.0
        if runs_g_rbi_line != '-' and runs_g_rbi_line is not None:
            try:
                rf = float(runs_g_rbi_line)
                rp = float(runs_g_rbi_price) if runs_g_rbi_price is not None else 0.0
                if rf >= 1.5 and rp < 0:
                    rr_boost = 1.05 # +5% boost for elite runs+RBIs prop
                elif rf >= 1.5:
                    rr_boost = 1.02 # +2% boost
            except:
                pass

        solo_score = (solo_score + walks_boost + so_penalty) * rr_boost
        
        # Stack-adjusted score (team tab / legacy); hitter matrix uses solo_score only
        individual_stacked = individual_core * protection_boost
        final_alpha = (individual_stacked * 0.65) + (team_score * 0.35)
        final_alpha *= park_factor
        final_alpha = (final_alpha + walks_boost + so_penalty) * rr_boost
        
        # OMEGA v13.9 / v16.0: Apply batted ball profile and market suppression boosts/penalties inside the engine
        if hard_hit_pct >= 45.0:
            final_alpha *= 1.03
            solo_score *= 1.03
        if barrel_pct >= 12.0:
            final_alpha *= 1.02
            solo_score *= 1.02

        if hits_line is not None and hits_price is not None:
            try:
                hl = float(hits_line)
                hp = float(hits_price)
                if hl <= 0.5 and hp > 0:
                    final_alpha *= 0.80
                    solo_score *= 0.80
            except:
                pass
        
        # Apply recent form boost/penalty from StatsAPI L7 game logs
        final_alpha += form_boost
        solo_score += form_boost

        return {
            "final": round(max(0, final_alpha), 1),
            "solo_score": round(max(0, solo_score), 1),
            "physics": round(p_comp, 1),
            "physics_component": round(p_comp, 1),
            "market": round(m_comp, 1),
            "matchup_xwoba": round(matchup_xwoba, 3),
            "matchup_boost": round(matchup_radar_boost, 2),
            "platoon_multiplier": round(platoon_multiplier, 2),
            "platoon_label": platoon_label,
            "walks_boost": walks_boost > 0,
            "strikeouts_penalty": so_penalty < 0
        }
