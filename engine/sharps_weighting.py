import pandas as pd
from datetime import datetime
import os
from config import config

class SharpsWeighting:
    def __init__(self):
        # User defined thresholds
        self.ML_MOVE_MIN = 10  # 10 cents
        self.TT_MOVE_MIN = 0.3 # 0.3 runs
        self.PUBLIC_BET_MAX = 50 # 50%
        
    def calculate_pitcher_score(self, name, ml_move, tt_move, money_gap, k_prop, siera=4.10, csw=0.25, is_target=False, park_factor=0, divergence=0, is_shark=False, is_whale=False, opponent_k_boost=0):
        """
        OMEGA v6.0 SE: Tiered Alpha/Beta Pitcher Scoring.
        """
        s_score = max(0, min(100, (6.0 - siera) * 20))
        c_score = max(0, min(100, (csw / 0.35) * 100))
        physics_raw = (s_score + c_score) / 2
        physics_raw *= (1 + ((park_factor + opponent_k_boost) / 100.0))
        
        ml_score = max(0, min(100, (abs(ml_move) / 20.0) * 100))
        tt_score = max(0, min(100, (abs(tt_move) / 0.7) * 100))
        market_raw = (ml_score + tt_score) / 2
        
        # OMEGA v6.1: Sharp-Centric Weighting (Whales > Physics)
        score = 40.0 + (physics_raw * 0.20) + (market_raw * 0.45)
        
        # OMEGA v6.1: Tiered Multipliers
        alpha_signals = 0
        beta_signals = 0
        
        if is_target: alpha_signals += 1
        if is_whale: alpha_signals += 1
        if is_shark: alpha_signals += 1
        
        # Beta Signals
        if k_prop and float(k_prop) >= 6.5: beta_signals += 1
        if abs(tt_move) >= 0.5: beta_signals += 1
        if divergence >= 10: beta_signals += 1
        
        # Base Multiplier: Alpha (+15%), Beta (+5%)
        multiplier = 1.0 + (alpha_signals * 0.15) + (beta_signals * 0.05)
        
        # 1. SHARP CONVICTION (+20%): Significant whale/shark backing (Priority Highlight)
        if is_whale or is_shark:
            multiplier += 0.20
        
        # Dynamic Divergence Boost: +0.66% per 1% divergence (Capped at 15%)
        div_boost = 1.0 + min(0.15, (max(0, divergence) / 150.0))
        
        final_alpha = score * multiplier * div_boost
        
        return {
            "final": round(final_alpha, 1),
            "physics": round(physics_raw * 0.25, 1),
            "market": round(market_raw * 0.35, 1)
        }

    def calculate_individual_hitter_score(self, name, team_omega, matchup_xwoba, ahr_price, park_factor=1.0, is_target=False, is_speed_target=False, is_hot=False):
        """OMEGA v6.0 SE: Tiered Alpha/Beta Hitter Scoring."""
        physics_raw = max(0, min(100, (matchup_xwoba / 0.400) * 100))
        physics_raw *= park_factor
        market_raw = max(0, min(100, team_omega))
        score = 40.0 + (physics_raw * 0.25) + (market_raw * 0.35)
        
        alpha_signals = 0
        beta_signals = 0
        
        # Alpha
        if is_target: alpha_signals += 1
        
        # Beta
        if matchup_xwoba > 0.360: beta_signals += 1
        if is_speed_target: beta_signals += 1
        if is_hot: beta_signals += 1
        if ahr_price and ahr_price < 400: beta_signals += 1
        
        multiplier = 1.0 + (alpha_signals * 0.15) + (beta_signals * 0.05)
        
        final_score = score * multiplier
        return {
            "final": round(final_score, 1),
            "physics": round(physics_raw * 0.25, 1),
            "market": round(market_raw * 0.35, 1)
        }

    def calculate_stack_score(self, team, ml_move, tt_move, curr_itt=4.5, park_factor=1.0, bullpen_fatigue=0, divergence=0, is_whale=False, is_sharp=False, is_storm=False, is_shark=False, opp_pitcher_physics=0):
        """OMEGA v6.7 SE: Tiered Alpha/Beta Stack Scoring with 30% CSW Stopper Logic."""
        physics_raw = max(0, min(100, (curr_itt / 6.0) * 100))
        physics_raw *= (1 + (park_factor / 100.0))
        
        ml_score = max(0, min(100, (abs(ml_move) / 20.0) * 100))
        tt_score = max(0, min(100, (abs(tt_move) / 0.7) * 100))
        market_raw = (ml_score + tt_score) / 2
        
        score = 40.0 + (physics_raw * 0.25) + (market_raw * 0.35)
        
        alpha_signals = 0
        beta_signals = 0
        
        # Alpha
        if is_storm: alpha_signals += 1
        if is_whale: alpha_signals += 1
        if is_shark: alpha_signals += 1
        
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
        return {
            "final": round(final_omega, 1),
            "physics": round(physics_raw * 0.25, 1),
            "market": round(market_raw * 0.35, 1)
        }

    def calculate_individual_hitter_score(self, player_name, team_score, matchup_xwoba, ahr_price, park_factor=1.0, is_target=False, is_speed_target=False, is_hot=False, protection_boost=1.0, vision_boost=1.0):
        """
        OMEGA v6.22: Individual Hitter Alpha HARDENED.
        Combines Statcast xwOBA (Physics), AHR Pricing (Market), Team Context,
        and new Synergy Logic (Protection + Vision).
        """
        # 1. Physics Pillar (xwOBA based: Scale 0.280 to 0.420 -> 0 to 50 pts)
        p_comp = max(0, min(50, ((matchup_xwoba - 0.280) / (0.420 - 0.280)) * 50))
        
        # 2. Market Pillar (AHR Price based: Scale 700 to 200 -> 0 to 50 pts)
        m_comp = max(0, min(50, ((700 - min(700, ahr_price)) / 500) * 50))
        
        # 3. Boost Coefficient (Targets, Momentum, and Vision)
        boost = 1.0
        if is_target: boost += 0.10
        if is_speed_target: boost += 0.05
        if is_hot: boost += 0.15
        
        # OMEGA v6.22: Vision Boost (K-rate discipline)
        boost *= vision_boost
        
        # Aggregated Individual Score
        individual_final = (p_comp + m_comp) * boost
        
        # OMEGA v6.22: Lineup Protection Synergy
        individual_final *= protection_boost
        
        # 4. Integrate Team Context (The 70/30 Master Rule)
        final_alpha = (individual_final * 0.7) + (team_score * 0.3)
        
        # Apply Park Factor Modifier
        final_alpha *= (1.0 + (park_factor - 1.0))
        
        return {
            "final": round(max(0, final_alpha), 1),
            "physics": round(p_comp, 1),
            "market": round(m_comp, 1)
        }
