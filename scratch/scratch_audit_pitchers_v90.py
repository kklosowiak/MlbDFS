import sys
import os
import json

# Adjust path to import our active project modules using absolute workspace path
sys.path.append(r'c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS')

from engine.sharps_weighting import SharpsWeighting

def run_pitcher_v90_audit():
    archive_path = r'c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\archive\results_2026-05-17.json'
    
    if not os.path.exists(archive_path):
        print(f"Error: Archive file not found at {archive_path}")
        return
        
    with open(archive_path, 'r') as f:
        data = json.load(f)
        
    # Map teams to get their Vegas implied total
    teams_itt = {t['team']: t.get('implied_total', 4.5) for t in data.get('teams', [])}
    pitchers_list = data.get('pitchers', [])
    
    recalculated_pitchers = []
    
    for p in pitchers_list:
        name = p['pitcher']
        opp_team = p['opponent']
        opp_itt = teams_itt.get(opp_team, 4.5)
        
        # OMEGA v9.0 Pitcher Market Hybrid Pillar
        # Perfection scale: 3.0 ITT = 100 points, 5.5 ITT = 0 points
        absolute_market_score = max(0, min(100, ((5.5 - opp_itt) / 2.5) * 100))
        
        ml_move = p.get('ml_move', 0.0)
        tt_move = p.get('tt_move', 0.0)
        
        ml_score = max(0, min(100, (abs(ml_move) / 20.0) * 100)) if ml_move < 0 else 0
        tt_score = max(0, min(100, (abs(tt_move) / 0.7) * 100))
        delta_score = (ml_score + tt_score) / 2
        
        # 50/50 Golden Ratio Blend for Pitchers
        market_raw = (absolute_market_score * 0.50) + (delta_score * 0.50)
        
        # Raw physics
        siera = p.get('siera', 4.10)
        csw = p.get('csw', 0.25)
        s_score = max(0, min(100, (6.0 - siera) * 20))
        c_score = max(0, min(100, (csw / 0.35) * 100))
        physics_raw_base = (s_score + c_score) / 2
        
        gate_active = physics_raw_base < 55.0
        
        k_mod = p.get('opponent_k_boost', 5.0) if abs(p.get('opponent_k_boost', 5.0)) > 3.0 else 0.0
        env_mod = (100.0 - p.get('park_factor', 100.0) + k_mod) / 100.0
        physics_raw = physics_raw_base * (1.0 + env_mod)
        
        # Base score
        score = 45.0 + (physics_raw * 0.45) + (market_raw * 0.20)
        if physics_raw_base >= 70.0:
            score += 15.0
            
        # Multipliers
        alpha_signals = 0
        beta_signals = 0
        
        if p.get('is_juiced_target', False) and not gate_active:
            alpha_signals += 1
            
        # Whale/Shark
        is_whale = p.get('divergence', 0) >= 15
        is_shark = p.get('is_shark', False)
        if (is_whale or is_shark) and not gate_active:
            alpha_signals += 1
            
        k_line = p.get('k_line', 4.5)
        if k_line and float(k_line) >= 6.5:
            beta_signals += 1
        if abs(tt_move) >= 0.5:
            beta_signals += 1
        if p.get('divergence', 0) >= 10:
            beta_signals += 1
            
        multiplier = 1.0 + (alpha_signals * 0.15) + (beta_signals * 0.05)
        if p.get('park_factor', 100.0) >= 114:
            multiplier -= 0.20
            
        div_boost = 1.0 + min(0.10, (max(0, p.get('divergence', 0)) / 150.0))
        volume_factor = min(1.0, float(p.get('outs_line', 15.5)) / 18.0)
        
        is_trap = p.get('is_trap', False)
        trap_multiplier = 0.85 if is_trap else 1.0
        
        # OMEGA v9.0: The Elite Ace Shield
        # Shield aces (physics >= 28.0) from institutional market anchors (negative divergence)
        market_anchor = 1.0
        divergence = p.get('divergence', 0)
        if divergence < -10 and physics_raw_base > 60:
            if p.get('physics_score', 25.0) >= 28.0:
                market_anchor = 1.0  # Ace Shield Activated!
            else:
                market_anchor = 0.90 # Penalty applies to non-aces
                
        final_alpha = score * multiplier * div_boost * volume_factor * trap_multiplier * market_anchor
        
        if p.get('is_low_ceiling', False) and not p.get('is_juiced_target', False):
            final_alpha *= 0.90
            
        recalculated_pitchers.append({
            'pitcher': name,
            'team': p['team'],
            'opp': opp_team,
            'opp_itt': opp_itt,
            'old': p['alpha_score'],
            'new': round(final_alpha, 1),
            'shift': round(final_alpha - p['alpha_score'], 1),
            'shield_activated': (divergence < -10 and physics_raw_base > 60 and p.get('physics_score', 25.0) >= 28.0)
        })
        
    # Sort by new score
    old_sorted = sorted(recalculated_pitchers, key=lambda x: x['old'], reverse=True)
    new_sorted = sorted(recalculated_pitchers, key=lambda x: x['new'], reverse=True)
    
    old_ranks = {item['pitcher']: rank + 1 for rank, item in enumerate(old_sorted)}
    new_ranks = {item['pitcher']: rank + 1 for rank, item in enumerate(new_sorted)}
    
    print("==========================================================================================")
    print("                     OMEGA v9.0 Pitcher 'Cy Young' Re-Ranking")
    print("==========================================================================================")
    print(f"{'Pitcher':<20} | {'Old Score (Rank)':<18} | {'v9.0 Score (Rank)':<18} | {'Shift':<20} | {'Opp ITT':<8}")
    print("-" * 92)
    
    for item in new_sorted:
        p_name = item['pitcher']
        old_rank = old_ranks[p_name]
        new_rank = new_ranks[p_name]
        
        old_str = f"{item['old']:.1f} (#{old_rank})"
        new_str = f"{item['new']:.1f} (#{new_rank})"
        
        rank_change_str = ""
        if old_rank > new_rank:
            rank_change_str = f"+{old_rank - new_rank} ranks"
        elif old_rank < new_rank:
            rank_change_str = f"-{new_rank - old_rank} ranks"
        else:
            rank_change_str = "no change"
            
        shield_note = " [Ace Shield]" if item['shield_activated'] else ""
        shift_str = f"{item['shift']:+5.1f} ({rank_change_str}){shield_note}"
        
        print(f"{p_name:<20} | {old_str:<18} | {new_str:<18} | {shift_str:<20} | {item['opp_itt']:<8.2f}")
    print("==========================================================================================")

if __name__ == "__main__":
    run_pitcher_v90_audit()
