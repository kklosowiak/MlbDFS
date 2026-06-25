"""
GPP Leverage Index (GLI) and labeling calculations for Team Stacks.
Calibrates pivot selectivity based on slate size and corrects crowded chalk false positives.
"""

from __future__ import annotations
from utils.normalization import normalize_player_name
from utils.attack_confidence import score_stack_confidence

def compute_gpp_leverage(team_reports: list[dict], p_reports: list[dict]) -> None:
    """
    Computes projected ownership proxy, scales it to 200.0%, calculates GPP Leverage
    Index (GLI), and labels each team as LEVERAGE PIVOT, CROWDED CHALK, or NEUTRAL.
    
    Pivot labels are capped based on slate size (max 20% of teams, min 1) to remain
    highly selective, and require a confidence score >= 50.0.
    
    Chalk labels require the team's ownership to be at least average to avoid false
    positives on low-owned, low-confidence stacks.
    """
    if not team_reports:
        return
        
    pitchers_dict = {normalize_player_name(p['pitcher']): p for p in p_reports}
    
    # Calculate raw ownership proxy for each team
    raw_owns = []
    for t in team_reports:
        implied_total = float(t.get('implied_total', 4.5) or 4.5)
        # Public ownership is highly exponential relative to implied runs
        proj_own = implied_total ** 3.5
        
        # Apply public chasing multipliers
        if t.get('is_sharp'):
            proj_own *= 0.80
            
        # Stacking against trap SPs
        opp_sp_name = t.get('opp_pitcher')
        if opp_sp_name:
            opp_sp_norm = normalize_player_name(opp_sp_name)
            opp_sp = pitchers_dict.get(opp_sp_norm)
            if opp_sp:
                if opp_sp.get('is_trap'):
                    proj_own *= 1.30
                
                # Pitcher talent discount (public avoids aces)
                opp_sp_score = opp_sp.get('alpha_score')
                if isinstance(opp_sp_score, dict):
                    opp_sp_val = opp_sp_score.get('final', 80)
                else:
                    opp_sp_val = float(opp_sp_score or 80)
                if opp_sp_val >= 100:
                    proj_own *= 0.60
        
        t['_raw_own'] = proj_own
        raw_owns.append(proj_own)
        
    # Normalize ownership to sum to 200.0% (representing 2 stacks per entry)
    sum_raw_owns = sum(raw_owns)
    n_teams = len(team_reports)
    if sum_raw_owns > 0 and n_teams > 0:
        avg_own = 200.0 / n_teams
        
        # First pass: calculate ownership, confidence, and GLI
        for t in team_reports:
            scaled_own = (t['_raw_own'] / sum_raw_owns) * 200.0
            conf, _ = score_stack_confidence(t, p_reports)
            
            # Leverage index = (CONF / 50) / (ownership / average_ownership)
            gli = (conf / 50.0) / max(0.1, (scaled_own / avg_own))
            
            t['projected_ownership'] = round(scaled_own, 1)
            t['gpp_leverage_index'] = round(gli, 2)
            t['_conf'] = conf
            
            # Clean up raw temp variable
            t.pop('_raw_own', None)

        # Second pass: Determine leverage labels
        # Identify pivot candidates
        candidates = []
        for t in team_reports:
            conf = t['_conf']
            gli = t['gpp_leverage_index']
            scaled_own = t['projected_ownership']
            
            is_candidate = (
                conf >= 50.0 and
                gli >= 1.5 and
                not t.get('is_trap', False) and
                not t.get('is_fade_risk', False) and
                scaled_own < 1.1 * avg_own
            )
            if is_candidate:
                candidates.append(t)

        # Sort candidates by GLI descending, then by confidence descending
        candidates.sort(key=lambda x: (x['gpp_leverage_index'], x['_conf']), reverse=True)
        
        # Limit pivots based on slate size: at most 20% of the slate (minimum 1 if candidates exist)
        pivot_limit = max(1, int(round(n_teams * 0.20)))
        pivots_to_label = candidates[:pivot_limit]
        pivot_teams = {t['team'] for t in pivots_to_label}

        # Apply labels
        for t in team_reports:
            gli = t['gpp_leverage_index']
            scaled_own = t['projected_ownership']
            
            if t['team'] in pivot_teams:
                t['leverage_label'] = 'LEVERAGE PIVOT'
                t['leverage_color'] = 'green'
            elif gli < 0.6 and scaled_own >= avg_own:
                t['leverage_label'] = 'OVEROWNED'
                t['leverage_color'] = 'red'
            else:
                t['leverage_label'] = 'NEUTRAL'
                t['leverage_color'] = 'gray'
                
            # Clean up temporary conf variable
            t.pop('_conf', None)
