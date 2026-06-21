import os
import json
import pytest
from utils.attack_confidence import score_stack_confidence
from engine.sharps_weighting import SharpsWeighting

def test_slate_size_dampening_confidence():
    # Test that confidence penalty is scaled down for smaller slates
    team_trap = {
        "team": "Kansas City Royals",
        "team_xwoba": 0.350,
        "implied_total": 4.0,
        "is_trap": True
    }
    
    # 1. Main Slate (15 games = 30 pitchers)
    p_reports_main = [{"pitcher": f"P{i}", "team": "T"} for i in range(30)]
    conf_main, reasons_main = score_stack_confidence(team_trap, p_reports_main)
    
    # 2. Small Slate (4 games = 8 pitchers)
    p_reports_small = [{"pitcher": f"P{i}", "team": "T"} for i in range(8)]
    conf_small, reasons_small = score_stack_confidence(team_trap, p_reports_small)
    
    print(f"Conf Main: {conf_main} | Conf Small: {conf_small}")
    # The small slate confidence should be higher because the trap penalty is dampened
    assert conf_small > conf_main
    # The trap penalty on 15 games is -24.0, on 4 games it is max(8.0, 24 * 4/15) = max(8.0, 6.4) = 8.0.
    # So main slate conf should be 50 (start) + 18 (xwoba) - 24 (trap) = 44.
    # Small slate conf should be 50 + 18 - 8 = 60.
    assert conf_main == 44.0
    assert conf_small == 60.0

def test_sharps_weighting_dampening():
    sw = SharpsWeighting()
    # Test stack score with 15 games vs 4 games when it's a chalk trap
    # We call calculate_stack_score with a low xwOBA and high divergence to trigger _stack_chalk_trap
    # physics_raw = 30.0, team_xwoba = 0.280, ml_move = 0.0, divergence = -15.0
    res_main = sw.calculate_stack_score(
        team="Chicago Cubs",
        ml_move=0.0,
        tt_move=0.0,
        curr_itt=5.0,
        team_xwoba=0.280,
        power_concentration=0.330,
        divergence=-15.0,
        num_games=15,
        opp_pitcher_physics=50.0
    )
    
    res_small = sw.calculate_stack_score(
        team="Chicago Cubs",
        ml_move=0.0,
        tt_move=0.0,
        curr_itt=5.0,
        team_xwoba=0.280,
        power_concentration=0.330,
        divergence=-15.0,
        num_games=4,
        opp_pitcher_physics=50.0
    )
    
    # Small slate stack score should be higher because the chalk trap penalty is scaled down
    assert res_small["is_trap"] is True
    assert res_main["is_trap"] is True
    assert res_small["final"] > res_main["final"]
