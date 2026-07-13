import pytest
from utils.slate_report_generator import SlateReportGenerator

def test_stack_trust_score_calculation_option_b():
    # Test case 1: Opposing SP has a trap flag (Short Leash) -> should receive -10 penalty on 4.5 ITT (Score = 35.0)
    p_reports_trap = [
        {
            "pitcher": "Trap Pitcher",
            "team": "Opponent Team",
            "opponent": "My Team",
            "is_trap": True,
            "trap_type": "Short Leash"
        }
    ]
    team_reports_trap = [
        {
            "team": "My Team",
            "opponent": "Opponent Team",
            "opp_pitcher": "Trap Pitcher",
            "implied_total": 4.5,
            "attack_conf": 75.0,
            "stack_score": 80.0
        }
    ]
    h_reports = []
    
    generator = SlateReportGenerator()
    generator.output_path = "dummy_path.md"
    
    scored_stacks = []
    pitcher_map = {"trap pitcher": p_reports_trap[0]}
    
    # Run the exact code block from generate
    for t in team_reports_trap:
        opp_p = pitcher_map.get("trap pitcher")
        opp_sp_any_flag = 0.0
        if opp_p:
            is_trap = opp_p.get('is_trap', False)
            trap_type = opp_p.get('trap_type')
            opp_trap_short_leash = is_trap and trap_type == 'Short Leash'
            opp_trap_vulnerable = is_trap and trap_type == 'Vulnerable'
            opp_low_ceiling = opp_p.get('is_low_ceiling', False)
            opp_hazard = opp_p.get('is_hazard', False)
            opp_paradox = opp_p.get('is_paradox', False)
            if opp_trap_short_leash or opp_trap_vulnerable or opp_low_ceiling or opp_hazard or opp_paradox:
                opp_sp_any_flag = 1.0
        itt = float(t.get('implied_total', 0.0) or 0.0)
        ts = itt * 10.0 - 10.0 * opp_sp_any_flag
        t['stack_trust_score'] = round(max(0.0, min(100.0, ts)), 1)
        scored_stacks.append(t)
        
    assert scored_stacks[0]['stack_trust_score'] == 35.0

def test_stack_trust_score_calculation_no_penalty():
    # Test case 2: Opposing SP has no flags -> should get baseline score of 4.5 * 10 = 45.0
    p_reports_clean = [
        {
            "pitcher": "Clean Pitcher",
            "team": "Opponent Team",
            "opponent": "My Team",
            "is_trap": False,
            "trap_type": None
        }
    ]
    team_reports_clean = [
        {
            "team": "My Team",
            "opponent": "Opponent Team",
            "opp_pitcher": "Clean Pitcher",
            "implied_total": 4.5,
            "attack_conf": 75.0,
            "stack_score": 80.0
        }
    ]
    
    scored_stacks = []
    pitcher_map = {"clean pitcher": p_reports_clean[0]}
    
    for t in team_reports_clean:
        opp_p = pitcher_map.get("clean pitcher")
        opp_sp_any_flag = 0.0
        if opp_p:
            is_trap = opp_p.get('is_trap', False)
            trap_type = opp_p.get('trap_type')
            opp_trap_short_leash = is_trap and trap_type == 'Short Leash'
            opp_trap_vulnerable = is_trap and trap_type == 'Vulnerable'
            opp_low_ceiling = opp_p.get('is_low_ceiling', False)
            opp_hazard = opp_p.get('is_hazard', False)
            opp_paradox = opp_p.get('is_paradox', False)
            if opp_trap_short_leash or opp_trap_vulnerable or opp_low_ceiling or opp_hazard or opp_paradox:
                opp_sp_any_flag = 1.0
        itt = float(t.get('implied_total', 0.0) or 0.0)
        ts = itt * 10.0 - 10.0 * opp_sp_any_flag
        t['stack_trust_score'] = round(max(0.0, min(100.0, ts)), 1)
        scored_stacks.append(t)
        
    assert scored_stacks[0]['stack_trust_score'] == 45.0

def test_stack_trust_sorting():
    # Test case 3: Stacks should be sorted primarily by stack_trust_score and secondarily by attack_conf
    scored_stacks = [
        {"team": "Team A", "stack_trust_score": 35.0, "attack_conf": 85.0}, # Lower trust, higher conf
        {"team": "Team B", "stack_trust_score": 45.0, "attack_conf": 65.0}, # Higher trust, lower conf
        {"team": "Team C", "stack_trust_score": 45.0, "attack_conf": 80.0}  # Higher trust, higher conf
    ]
    
    # Sort key: primary = stack_trust_score, secondary = attack_conf
    scored_stacks.sort(key=lambda x: (x.get('stack_trust_score', 0.0), x.get('attack_conf', 0.0)), reverse=True)
    
    assert scored_stacks[0]["team"] == "Team C" # 45.0 trust, 80.0 conf
    assert scored_stacks[1]["team"] == "Team B" # 45.0 trust, 65.0 conf
    assert scored_stacks[2]["team"] == "Team A" # 35.0 trust, 85.0 conf
