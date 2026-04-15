import json
import os
from config import config

class HitterAlpha:
    def __init__(self):
        self.ML_MOVE_MIN = 10
        self.TT_BOOST_MIN = 0.3
        self.PUBLIC_BET_MAX = 50
        
    def calculate_stack_score(self, team_name, ml_move, tt_move, public_bets, curr_itt=4.0, hr_alpha=0, weather_boost=0, game_total=0, is_confirmed=True):
        """
        Team Omega v3.2.1.3 Additive Pillar.
        Final = (Physics_50 + Market_50) * (1 + Boost)
        """
        # 1. Physics Component (0-50 pts) - Fallback Default: 25.0
        p_comp = min(50, (curr_itt / 6.0) * 50)
        
        # 2. Market Component (0-50 pts) - Fallback Default: 25.0
        m_move_pts = min(20, (abs(ml_move) / 25) * 20)
        tt_pts = min(20, (max(0, tt_move) / 0.8) * 20)
        p_pts = max(0, 40 - public_bets) * 0.25 # Max 10 pts
        m_comp = m_move_pts + tt_pts + p_pts
        
        # 3. Aggressive Signal Boost (1 + boost)
        signals = 0
        if ml_move >= 15: signals += 1
        if tt_move >= 0.5: signals += 1
        if public_bets < 40: signals += 1
        
        # OMEGA Master Multiplier Rule
        boost = 0.0
        if signals == 3: boost = 0.30
        elif signals == 2: boost = 0.15
        
        # Lineup Confirmation Penalty (as Coefficient)
        conf_coef = 1.0 if is_confirmed else 0.85
        
        # Final Calculation
        final = (p_comp + m_comp) * (1 + boost) * conf_coef + (hr_alpha * 0.5) + weather_boost
        
        # TRACING PROOF
        print(f"TRACING {team_name}: Physics={p_comp:.1f}, Market={m_comp:.1f}, Boost={boost:.2f} -> Omega={final:.1f}")
            
        return round(max(0, min(100, final)), 1)
        
    def calculate_individual_hitter_score(self, player_name, team_score, matchup_xwoba, ahr_price, hit_signals=0):
        """
        Individual Hitter Alpha v3.2.1.3 Additive Pillar.
        Final = (Physics_50 + Market_50) * (1 + Boost)
        Combined with Team Context (30% weight)
        """
        # 1. Physics Pillar (xwOBA based)
        p_comp = max(0, min(50, ((matchup_xwoba - 0.280) / (0.420 - 0.280)) * 50))
        
        # 2. Market Pillar (AHR Price based)
        m_comp = max(0, min(50, ((500 - min(500, ahr_price)) / 250) * 50))
        
        # 3. Boost Coefficient
        boost = 0.05 * hit_signals
        
        # Aggregated Individual Score
        individual_final = (p_comp + m_comp) * (1 + boost)
        
        # 4. Integrate Team Context (The 70/30 Master Rule)
        # We treat team context as an additive blender
        final_alpha = (individual_final * 0.7) + (team_score * 0.3)
        
        # TRACING PROOF
        print(f"TRACING {player_name}: Physics={p_comp:.1f}, Market={m_comp:.1f}, Boost={boost:.2f} -> Alpha={final_alpha:.1f}")
        
        return round(max(0, min(100, final_alpha)), 1)
        





    def get_emoji_status(self, score):
        """Returns the appropriate emoji and status for a score."""
        if score >= 75: return "🧨", "ULTRA ELITE"
        if score >= 60: return "🔥", "ELITE"
        if score >= 45: return "✅", "STRONG"
        if score >= 30: return "📈", "POSITIVE"
        return "⚪", "NEUTRAL"
        
    def get_emoji_key(self):
        """Returns a legend of emojis used in the system."""
        return {
            "🎰": "Sharp Convergence (Money Handle + Reverse Line Movement)",
            "🧨": "Ultra Elite (Rushing Sharp Money + Massive TT Boost)",
            "🔥": "Elite (Confirmed Sharp Support or High Stack Score)",
            "💰": "Sharp Money Influx (Significant Money vs Ticket Gap)",
            "✅": "Strong (Positive Market Sentiment / Line Value)",
            "📈": "Matchup Alpha (Statcast High-Efficiency Matchup)",
            "🎯": "Prop Target (High Confidence Strikeout or Outs Line)"
        }
