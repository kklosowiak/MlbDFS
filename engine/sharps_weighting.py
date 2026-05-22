from datetime import datetime
from config import config

class SharpsWeighting:
    def __init__(self):
        # User defined thresholds
        self.ML_MOVE_MIN = 10  # 10 cents
        self.TT_MOVE_MIN = 0.3 # 0.3 runs
        self.PUBLIC_BET_MAX = 50 # 50%
        
    def calculate_pitcher_score(self, name, ml_move, tt_move, money_gap, k_prop, siera=4.10, csw=0.25, is_target=False, park_factor=0, divergence=0, is_shark=False, is_whale=False, opponent_k_boost=0, is_low_ceiling=False, projected_outs=18.0, is_trap=False, is_sharp=False, curr_ml=-110):
        """
        OMEGA v10.0 SE: Tiered Alpha/Beta Pitcher Scoring (Win Prob Base Market).
        """
        s_score = max(0, min(100, (6.0 - siera) * 20))
        c_score = max(0, min(100, (csw / 0.35) * 100))
        physics_raw_base = (s_score + c_score) / 2
        
        # OMEGA v6.2.5: The Pure Talent Gate
        gate_active = physics_raw_base < 55.0
        
        # OMEGA v7.6: The 'Neutral K-Zone'
        k_mod = opponent_k_boost if abs(opponent_k_boost) > 3.0 else 0.0
        env_mod = (100.0 - park_factor + k_mod) / 100.0
        physics_raw = physics_raw_base * (1.0 + env_mod)
        
        # OMEGA v10.0: Market Win Probability Base
        def _ml_to_prob(ml):
            if ml == 0: return 0.5
            if ml < 0: return abs(ml) / (abs(ml) + 100)
            return 100 / (ml + 100)
            
        win_prob = _ml_to_prob(curr_ml)
        # Scale probability from 40% to 70% -> 0 to 100
        base_market_score = max(0, min(100, ((win_prob - 0.40) / 0.30) * 100))
        
        ml_score = max(0, min(100, (abs(ml_move) / 20.0) * 100)) if ml_move < 0 else 0
        tt_score = max(0, min(100, (abs(tt_move) / 0.7) * 100))
        
        market_raw = base_market_score + (ml_score * 0.20) + (tt_score * 0.20)
        market_raw = max(0, min(100, market_raw))
        
        # OMEGA v6.8.6: Talent-First Weighting
        score = 45.0 + (physics_raw * 0.45) + (market_raw * 0.20)
        
        if physics_raw_base >= 70.0:
            score += 15.0
        
        # OMEGA v6.1: Tiered Multipliers (Flattened v8.0)
        alpha_signals = 0
        beta_signals = 0
        
        if is_target and not gate_active: alpha_signals += 1
        
        # Group market signals to prevent double-counting
        if (is_whale or is_shark) and not gate_active:
            alpha_signals += 1
        
        if k_prop and float(k_prop) >= 6.5: beta_signals += 1
        if abs(tt_move) >= 0.5: beta_signals += 1
        if divergence >= 10: beta_signals += 1
        
        multiplier = 1.0 + (alpha_signals * 0.15) + (beta_signals * 0.05)
            
        if park_factor >= 114:
            multiplier -= 0.20
            
        # Cap div boost at 10%
        div_boost = 1.0 + min(0.10, (max(0, divergence) / 150.0))
        
        volume_factor = min(1.0, projected_outs / 18.0)
        
        # OMEGA v7.8: Prop Trap Penalty (-15%)
        trap_multiplier = 0.85 if is_trap else 1.0

        # OMEGA v8.5: The 'Institutional Anchor' (Market Fade)
        # If divergence is negative (market fading) and it's a high-alpha target,
        # apply a multiplicative penalty to simulate institutional skepticism.
        market_anchor = 1.0
        if divergence < -10 and physics_raw_base > 60 and is_trap:
            market_anchor = 0.90 # -10% institutional anchor
            
        # OMEGA v8.7.7: Pitcher Sharp Premium (+7.5%)
        sharp_multiplier = 1.075 if is_sharp else 1.0
            
        final_alpha = score * multiplier * div_boost * volume_factor * trap_multiplier * market_anchor * sharp_multiplier
        
        if is_low_ceiling and not is_target:
            final_alpha *= 0.90
            
        return {
            "final": round(final_alpha, 1),
            "physics": round(physics_raw * 0.45, 1),
            "market": round(market_raw * 0.20, 1),
            "is_coors": park_factor >= 114,
            "is_trap": is_trap
        }

    def calculate_stack_score(self, team, ml_move, tt_move, curr_itt=4.5, team_xwoba=0.330, power_concentration=0.330, park_factor=1.0, bullpen_fatigue=0, divergence=0, is_whale=False, is_sharp=False, is_storm=False, is_shark=False, is_steam=False, opp_pitcher_physics=0, confidence='high', pitcher_outs=18.0, implied_total=None, is_burst=False, opponent=None):
        """OMEGA v9.8: Tiered Alpha/Beta Stack Scoring (Physics 2.0 Hardened)."""
        # OMEGA v7.7: Physics Hardening (Hybrid Statcast + Market ITT)
        # OMEGA v7.0: Power Concentration (Burst Potential)
        effective_physics = (team_xwoba * 0.4) + (power_concentration * 0.6)
        physics_raw = (effective_physics - 0.260) / (0.400 - 0.260) * 100
        physics_raw = max(0, min(100, physics_raw))
        # PARK_FACTORS are run multipliers (~0.92–1.15), not percentage points
        pf = float(park_factor or 1.0)
        if pf > 3.0:
            pf = 1.0 + (pf / 100.0)
        physics_raw = min(100.0, physics_raw * pf)

        # OMEGA v8.7: Linear Fatigue Pressure (Sliding Scale v1.0)
        # Pressure starts building at 65% instead of a hard cliff at 80%
        fatigue_floor = 65.0
        bullpen_boost = max(0, (bullpen_fatigue - fatigue_floor) / 3.5)
        
        # Short-Leash Multiplier: If starter < 15.5 outs, pressure on the tired bullpen is 1.5x
        if pitcher_outs < 15.5:
            bullpen_boost *= 1.5
        
        bullpen_boost = min(15.0, bullpen_boost) # Cap total pressure at 15 pts

        # OMEGA v8.9: Absolute-Delta Hybrid Market Pillar
        # Incorporate absolute Vegas ITT (scale 3.0 to 5.5 -> 0 to 100 pts) so flat high-total stacks are rewarded
        eff_itt = implied_total if implied_total is not None else curr_itt
        base_market_score = max(0, min(100, ((eff_itt - 3.0) / 2.5) * 100))
        
        # Calculate delta-based movement scores
        ml_score = max(0, min(100, (abs(ml_move) / 20.0) * 100)) if ml_move < 0 else 0
        tt_score = max(0, min(100, (tt_move / 0.5) * 100)) if tt_move > 0 else 0
        
        # OMEGA v10.0: Base + Bonus Model
        # Base is the implied total. Movement acts as an additive bonus rather than averaging out.
        market_raw = base_market_score + (ml_score * 0.25) + (tt_score * 0.25)
        market_raw = max(0, min(100, market_raw))

        # OMEGA v6.9: Pitcher Vulnerability
        vulnerability_mod = (100.0 - opp_pitcher_physics) / 5.0 

        # OMEGA v7.7.1: REVERTED WEIGHTS (Baseline Restored, Filters Kept)
        # Physics 40% | Market 20% | Baseline 40.0
        score = 40.0 + (physics_raw * 0.40) + (market_raw * 0.20) + vulnerability_mod + bullpen_boost
        
        alpha_signals = 0
        beta_signals = 0
        
        # Alpha (Market Convergence Grouping to prevent exponential stacking)
        market_alphas = 0
        if is_storm: market_alphas += 1
        if is_whale: market_alphas += 1
        if is_shark: market_alphas += 1
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

        # OMEGA v9.8: Bullpen Skill Grades
        bullpen_skill_mult = 1.0
        if opponent:
            opp_name = str(opponent).strip()
            elite_pens = {
                'Cleveland Guardians', 'Milwaukee Brewers', 'New York Yankees', 
                'Atlanta Braves', 'Los Angeles Dodgers', 'Seattle Mariners', 
                'San Diego Padres', 'Philadelphia Phillies'
            }
            weak_pens = {
                'Colorado Rockies', 'Chicago White Sox', 'Miami Marlins', 
                'Oakland Athletics', 'Athletics', 'Washington Nationals', 
                'Detroit Tigers', 'Los Angeles Angels', 'Toronto Blue Jays'
            }
            if opp_name in elite_pens:
                bullpen_skill_mult = 0.95
            elif opp_name in weak_pens:
                bullpen_skill_mult = 1.10

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

        if team_xwoba < 0.295 and dampened_market_premium > 0.10:
            final_omega = min(final_omega, score * (1.0 + min(0.22, dampened_market_premium)))
        
        # OMEGA v7.3: ITT Sanity Gate (Refined to trust sharp leverage)
        eff_itt = implied_total if implied_total is not None else curr_itt
        
        # If Vegas says it's a low total, but sharps disagree (WHALE/STORM), we trust the sharps.
        # We only apply the penalty if there is no major sharp divergence backing them.
        is_sharp_backed = is_whale or is_storm or (divergence > 15)
        
        if eff_itt < 4.0 and final_omega > 90.0 and not is_sharp_backed:
            final_omega *= 0.85  
        elif eff_itt > 5.5 and final_omega < 70.0:
            final_omega *= 1.10  
        
        if confidence == 'low':
            final_omega = min(80.0, final_omega)
        
        return {
            "final": round(final_omega, 1),
            "physics": round(physics_raw * 0.40, 1),
            "physics_raw": round(physics_raw, 1),
            "market": round(market_raw * 0.20, 1),
            "market_raw": round(market_raw, 1),
            "team_xwoba": round(team_xwoba, 3),
            "vulnerability": round(vulnerability_mod, 1),
            "volatility_hit": False,
            "convergence_boost": convergence_boost > 1.0,
            "confidence": confidence,
            "is_trap": chalk_trap,
            "is_stack_chalk": chalk_trap,
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
        public_pressure = ml_move >= 5 or (divergence > 12 and not sharp_in_favor)
        return public_pressure

    def calculate_individual_hitter_score(self, player_name, team_score, matchup_xwoba, ahr_price, park_factor=1.0, is_target=False, is_speed_target=False, is_hot=False, protection_boost=1.0, vision_boost=1.0, opp_csw=0.0, matchup_radar_boost=1.0, pitch_hand=None, hitter_splits=None, smash_factor=False):
        """
        OMEGA v6.22: Individual Hitter Alpha HARDENED.
        Combines Statcast xwOBA (Physics), AHR Pricing (Market), Team Context,
        and new Synergy Logic (Protection + Vision + MatchupRadar).
        OMEGA v9.5 splits update: Blends player vs LHP/RHP split ratios dynamically.
        """
        platoon_multiplier = 1.0
        platoon_label = "Neutral"
        
        if pitch_hand and hitter_splits:
            opp_hand = str(pitch_hand).upper()  # "L" or "R"
            overall_ops = float(hitter_splits.get("ops", 0.720) or 0.720)
            if overall_ops <= 0.200: overall_ops = 0.720
            
            if opp_hand == "L":
                split_ops = float(hitter_splits.get("vs_left_ops", 0.0) or 0.0)
                split_pa = int(hitter_splits.get("vs_left_pa", 0) or 0)
                split_ops_2025 = float(hitter_splits.get("vs_left_ops_2025", 0.0) or 0.0)
                split_pa_2025 = int(hitter_splits.get("vs_left_pa_2025", 0) or 0)
                split_ops_other_2025 = float(hitter_splits.get("vs_right_ops_2025", 0.0) or 0.0)
                split_pa_other_2025 = int(hitter_splits.get("vs_right_pa_2025", 0) or 0)
                opp_label = "LHP"
            else:
                split_ops = float(hitter_splits.get("vs_right_ops", 0.0) or 0.0)
                split_pa = int(hitter_splits.get("vs_right_pa", 0) or 0)
                split_ops_2025 = float(hitter_splits.get("vs_right_ops_2025", 0.0) or 0.0)
                split_pa_2025 = int(hitter_splits.get("vs_right_pa_2025", 0) or 0)
                split_ops_other_2025 = float(hitter_splits.get("vs_left_ops_2025", 0.0) or 0.0)
                split_pa_other_2025 = int(hitter_splits.get("vs_left_pa_2025", 0) or 0)
                opp_label = "RHP"
            
            # Compute 2026 Ratio
            ratio_2026 = 1.0
            if overall_ops > 0 and split_ops > 0:
                ratio_2026 = split_ops / overall_ops

            # Compute 2025 Ratio
            ratio_2025 = 1.0
            has_2025 = False
            if (split_pa_2025 + split_pa_other_2025) >= 40 and split_ops_2025 > 0:
                total_pa_2025 = split_pa_2025 + split_pa_other_2025
                overall_ops_2025 = ((split_ops_2025 * split_pa_2025) + (split_ops_other_2025 * split_pa_other_2025)) / total_pa_2025
                if overall_ops_2025 > 0.200:
                    ratio_2025 = split_ops_2025 / overall_ops_2025
                    has_2025 = True

            # OMEGA v9.7: Bayesian Platoon Stabilization (Sample-Size Weighted Blend)
            # Linearly transition from prior year to current year as 2026 sample grows to 100 PA.
            # If split_pa is small, prior-year (2025) data acts as the anchor.
            weight_2026 = min(1.0, split_pa / 100.0)
            
            if has_2025:
                # Blend 2026 and 2025 ratios
                platoon_multiplier = (weight_2026 * ratio_2026) + ((1.0 - weight_2026) * ratio_2025)
                platoon_percent = round((platoon_multiplier - 1.0) * 100)
                platoon_label = f"Blended vs {opp_label} ({'+' if platoon_percent >= 0 else ''}{platoon_percent}%)"
            elif split_pa >= 20:
                # Blend 2026 with neutral (1.0) if no 2025 data exists
                platoon_multiplier = (weight_2026 * ratio_2026) + ((1.0 - weight_2026) * 1.0)
                platoon_percent = round((platoon_multiplier - 1.0) * 100)
                platoon_label = f"Blended vs {opp_label} ({'+' if platoon_percent >= 0 else ''}{platoon_percent}%)"
            else:
                platoon_multiplier = 1.0
                platoon_label = f"Neutral vs {opp_label}"

            # Bound split-scaling to stay within realistic sabermetric bounds [0.70, 1.30]
            platoon_multiplier = max(0.70, min(1.30, platoon_multiplier))
            matchup_xwoba = matchup_xwoba * platoon_multiplier

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
        
        # Aggregated Individual Score
        individual_final = (p_comp + m_comp) * boost * matchup_radar_boost
        
        # OMEGA v7.3 (Post-Mortem 4/28): Opposing Pitcher CSW Gate
        if opp_csw > 0.32:
            individual_final *= 0.85  
        elif opp_csw > 0.28:
            individual_final *= 0.92  
        
        # OMEGA v6.22: Lineup Protection Synergy
        individual_final *= protection_boost
        
        # 4. Integrate Team Context (The 65/35 Master Rule)
        final_alpha = (individual_final * 0.65) + (team_score * 0.35)
        
        # Apply Park Factor Modifier
        final_alpha *= park_factor
        
        return {
            "final": round(max(0, final_alpha), 1),
            "physics": round(p_comp, 1),
            "market": round(m_comp, 1),
            "matchup_boost": round(matchup_radar_boost, 2),
            "platoon_multiplier": round(platoon_multiplier, 2),
            "platoon_label": platoon_label
        }
