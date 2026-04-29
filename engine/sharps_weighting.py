from datetime import datetime
from config import config

class SharpsWeighting:
    def __init__(self):
        # User defined thresholds
        self.ML_MOVE_MIN = 10  # 10 cents
        self.TT_MOVE_MIN = 0.3 # 0.3 runs
        self.PUBLIC_BET_MAX = 50 # 50%
        
    def calculate_pitcher_score(self, name, ml_move, tt_move, money_gap, k_prop, siera=4.10, csw=0.25, is_target=False, park_factor=0, divergence=0, is_shark=False, is_whale=False, opponent_k_boost=0, is_low_ceiling=False):
        """
        OMEGA v6.0 SE: Tiered Alpha/Beta Pitcher Scoring.
        """
        s_score = max(0, min(100, (6.0 - siera) * 20))
        c_score = max(0, min(100, (csw / 0.35) * 100))
        physics_raw_base = (s_score + c_score) / 2
        
        # OMEGA v6.2.5: The Pure Talent Gate
        # We check the gate BEFORE park factors and opponent boosts.
        # This ensures the pitcher is fundamentally good enough to trust.
        gate_active = physics_raw_base < 55.0
        
        # OMEGA v6.8.6: Corrected Environmental Directionality
        # High park_factor (hitter friendly) now PENALIZES the physics score.
        # Opponent K Boost still adds value.
        env_mod = (100.0 - park_factor + opponent_k_boost) / 100.0
        physics_raw = physics_raw_base * (1.0 + env_mod)
        
        ml_score = max(0, min(100, (abs(ml_move) / 20.0) * 100)) if ml_move < 0 else 0
        tt_score = max(0, min(100, (abs(tt_move) / 0.7) * 100))
        market_raw = (ml_score + tt_score) / 2
        
        # OMEGA v6.8.6: Talent-First Weighting (45% Physics / 20% Market)
        # Shifted 10% from Market to Physics to address 'Elite Arm Suppression'
        score = 45.0 + (physics_raw * 0.45) + (market_raw * 0.20)
        
        # OMEGA v6.8.6: Elite Talent Floor
        # If a pitcher is truly elite (70+ Raw), they get a 'Quality Start' baseline boost.
        if physics_raw_base >= 70.0:
            score += 15.0
        
        # OMEGA v6.1: Tiered Multipliers
        alpha_signals = 0
        beta_signals = 0
        
        if is_target and not gate_active: alpha_signals += 1
        if is_whale and not gate_active: alpha_signals += 1
        if is_shark and not gate_active: alpha_signals += 1
        
        # Beta Signals (Always active as baseline flex)
        if k_prop and float(k_prop) >= 6.5: beta_signals += 1
        if abs(tt_move) >= 0.5: beta_signals += 1
        if divergence >= 10: beta_signals += 1
        
        # Base Multiplier: Alpha (+15%), Beta (+5%)
        multiplier = 1.0 + (alpha_signals * 0.15) + (beta_signals * 0.05)
        
        # 1. SHARP CONVICTION (+20%): Gated by Physics
        if (is_whale or is_shark) and not gate_active:
            multiplier += 0.20
            
        # OMEGA v6.8.5: The 'Coors Altitude Damper'
        # If park_factor >= 114 (Coors threshold), apply mandatory -20% penalty
        if park_factor >= 114:
            multiplier -= 0.20
            
        # Dynamic Divergence Boost: +0.66% per 1% divergence (Capped at 15%)
        div_boost = 1.0 + min(0.15, (max(0, divergence) / 150.0))
        
        final_alpha = score * multiplier * div_boost
        
        # OMEGA v7.0: The Ceiling Gate
        # REFINEMENT (v7.1): Bypass penalty if the market is heavily juicing the over (The Foster Griffin Rule).
        if is_low_ceiling and not is_target:
            final_alpha *= 0.90
            
        return {
            "final": round(final_alpha, 1),
            "physics": round(physics_raw * 0.45, 1),
            "market": round(market_raw * 0.20, 1),
            "is_coors": park_factor >= 114
        }

    def calculate_stack_score(self, team, ml_move, tt_move, curr_itt=4.5, team_xwoba=0.330, power_concentration=0.330, park_factor=1.0, bullpen_fatigue=0, divergence=0, is_whale=False, is_sharp=False, is_storm=False, is_shark=False, is_steam=False, opp_pitcher_physics=0, confidence='high', pitcher_outs=18.0, implied_total=None):
        """OMEGA v7.0: Tiered Alpha/Beta Stack Scoring with Burst Potential."""
        # OMEGA v6.8: Physics Hardening (Hybrid Statcast + Market ITT)
        # OMEGA v7.0: Power Concentration (Burst Potential)
        # We shift weighting to high-concentration xwOBA to catch "Top-Heavy" offenses.
        effective_physics = (team_xwoba * 0.4) + (power_concentration * 0.6)
        physics_raw = (effective_physics - 0.260) / (0.400 - 0.260) * 100
        physics_raw = max(0, min(100, physics_raw))
        physics_raw *= (1 + (park_factor / 100.0))

        # OMEGA v7.0: Bullpen Delta Decay
        # If the starter is expected to go short (< 5.1 IP) AND the bullpen is fatigued,
        # we add an "Early Explosion" boost of +10.
        bullpen_boost = 0
        if bullpen_fatigue >= 80:
            bullpen_boost = 5.0
            if pitcher_outs < 15.5:
                bullpen_boost = 12.0 # Significant upgrade for short leashes
        if bullpen_fatigue >= 100:
            bullpen_boost += 5.0

        # OMEGA v6.8: Market Pillar (Delta-Based)
        # ml_move < 0 is GOOD for the team. tt_move > 0 is GOOD for the team.
        ml_score = max(0, min(100, (abs(ml_move) / 20.0) * 100)) if ml_move < 0 else 0
        tt_score = max(0, min(100, (tt_move / 0.5) * 100)) if tt_move > 0 else 0
        market_raw = (ml_score + tt_score) / 2

        # OMEGA v6.9: Pitcher Vulnerability
        # High physics arm = Low vulnerability. 0-100 scale.
        vulnerability_mod = (100.0 - opp_pitcher_physics) / 5.0 # Max +20 pts for garbage arms

        # Talent-aware base score + Bullpen + Pitcher Vulnerability
        # OMEGA v7.0: Prioritize raw talent (40%) over market sentiment (20%)
        score = 40.0 + (physics_raw * 0.40) + (market_raw * 0.20) + vulnerability_mod + bullpen_boost
        
        alpha_signals = 0
        beta_signals = 0
        
        # Alpha
        if is_storm: alpha_signals += 1
        if is_whale: alpha_signals += 1
        if is_shark: alpha_signals += 1
        if is_steam: alpha_signals += 1
        
        # OMEGA v7.2: Soft Market Boost Cap for Weak Hitters
        # If the underlying team xwOBA is below average (< 0.315), cap alpha signals at 2.
        if team_xwoba < 0.315:
            alpha_signals = min(2, alpha_signals)
        
        # Beta
        if is_sharp: beta_signals += 1
        if tt_move > 0.5: beta_signals += 1
        if bullpen_fatigue >= 80: beta_signals += 1 # Consolidation: Any Pen Alert is a Beta signal
        
        # Multiplier Calculation: Alpha (+15%), Beta (+5%)
        multiplier = 1.0 + (alpha_signals * 0.15) + (beta_signals * 0.05)
        
        # OMEGA v6.7: The 'Detmers Patch' (Stopper Penalty Refined)
        # We only dampen the stack if the OPPOSING PITCHER is elite (30%+ CSW).
        # opp_pitcher_physics > 85 correlates to elite swing-and-miss profiles.
        if opp_pitcher_physics > 85 or (is_storm and opp_pitcher_physics > 70):
            multiplier -= 0.10 # -10% if facing an elite arm
        
        # Dynamic Divergence Multiplier: +0.66% per 1% divergence (Capped at 15%)
        div_multiplier = 1.0 + min(0.15, (max(0, divergence) / 150.0))
        
        final_omega = score * multiplier * div_multiplier
        
        # OMEGA v7.3 (Post-Mortem 4/28): ITT Sanity Gate
        # No stack should rank elite when Vegas says they score < 4 runs.
        # Conversely, boost undervalued stacks when ITT > 5.5.
        eff_itt = implied_total if implied_total is not None else curr_itt
        if eff_itt < 4.0 and final_omega > 90.0:
            final_omega *= 0.85  # -15% hard damper
        elif eff_itt > 5.5 and final_omega < 70.0:
            final_omega *= 1.10  # +10% underdog boost
        
        # OMEGA v6.9.0: Confidence Gate
        # Prevent "Phantom Whales" against unknown/fallback pitchers.
        if confidence == 'low':
            final_omega = min(80.0, final_omega)
        
        return {
            "final": round(final_omega, 1),
            "physics": round(physics_raw * 0.40, 1),
            "market": round(market_raw * 0.20, 1),
            "team_xwoba": round(team_xwoba, 3),
            "vulnerability": round(vulnerability_mod, 1),
            "bullpen_boost": round(bullpen_boost, 1),
            "confidence": confidence
        }

    def calculate_individual_hitter_score(self, player_name, team_score, matchup_xwoba, ahr_price, park_factor=1.0, is_target=False, is_speed_target=False, is_hot=False, protection_boost=1.0, vision_boost=1.0, opp_csw=0.0):
        """
        OMEGA v6.22: Individual Hitter Alpha HARDENED.
        Combines Statcast xwOBA (Physics), AHR Pricing (Market), Team Context,
        and new Synergy Logic (Protection + Vision).
        """
        # 1. Physics Pillar (xwOBA based: Scale 0.280 to 0.420 -> 0 to 50 pts)
        p_comp = max(0, min(50, ((matchup_xwoba - 0.280) / (0.420 - 0.280)) * 50))
        
        # 2. Market Pillar (AHR Price based: Scale 700 to 200 -> 0 to 50 pts)
        # OMEGA v7.3 (Post-Mortem 4/28): Cap at 40 pts for extreme juice (< -500)
        # Prevents "everyone has him" chalk traps (e.g., Ben Rice -474, Drake Baldwin -850)
        m_cap = 40 if ahr_price < -500 else 50
        m_comp = max(0, min(m_cap, ((700 - min(700, ahr_price)) / 500) * 50))
        
        # 3. Boost Coefficient (Targets, Momentum, and Vision)
        boost = 1.0
        if is_target: boost += 0.10
        if is_speed_target: boost += 0.05
        # OMEGA v7.3 (Post-Mortem 4/28): Reduced from 0.15 -> 0.07
        # Data shows only ~12% of "hot" hitters cash on any given night.
        if is_hot: boost += 0.07
        
        # OMEGA v6.22: Vision Boost (K-rate discipline)
        boost *= vision_boost
        
        # Aggregated Individual Score
        individual_final = (p_comp + m_comp) * boost
        
        # OMEGA v7.3 (Post-Mortem 4/28): Opposing Pitcher CSW Gate
        # If the opposing pitcher has elite swing-and-miss stuff (CSW > 0.28),
        # dampen the hitter score. This would have correctly reduced
        # Ben Rice (vs deGrom CSW .360) and James Wood (vs Holmes).
        if opp_csw > 0.32:
            individual_final *= 0.85  # -15% for elite CSW arms
        elif opp_csw > 0.28:
            individual_final *= 0.92  # -8% for above-average CSW arms
        
        # OMEGA v6.22: Lineup Protection Synergy
        individual_final *= protection_boost
        
        # 4. Integrate Team Context (The 65/35 Master Rule)
        # USER TWEAK (v6.1.1): Lower synergy gate to 75
        final_alpha = (individual_final * 0.65) + (team_score * 0.35)
        
        # Apply Park Factor Modifier
        final_alpha *= park_factor
        
        return {
            "final": round(max(0, final_alpha), 1),
            "physics": round(p_comp, 1),
            "market": round(m_comp, 1)
        }
