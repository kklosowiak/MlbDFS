from utils.team_signals import evaluate_sneaky_stack, apply_sneaky_stack

def test_sneaky_stack_elite_physics():
    # Implied total <= 4.1, team_xwoba >= 0.350 (Elite Exception)
    res = evaluate_sneaky_stack(
        implied_total=3.8,
        team_xwoba=0.350,
        opp_pitcher_outs=18.0,
        is_opp_debut=False,
        opp_bullpen_score=30.0
    )
    assert res is True

    # Under 0.350 with no structural triggers should fail
    res_fail = evaluate_sneaky_stack(
        implied_total=3.8,
        team_xwoba=0.345,
        opp_pitcher_outs=18.0,
        is_opp_debut=False,
        opp_bullpen_score=30.0
    )
    assert res_fail is False

def test_sneaky_stack_opener():
    # Implied total <= 4.1, opp_pitcher_outs <= 13.5 (Trigger 2)
    res = evaluate_sneaky_stack(
        implied_total=3.5,
        team_xwoba=0.310,
        opp_pitcher_outs=13.0,
        is_opp_debut=False,
        opp_bullpen_score=20.0
    )
    assert res is True

def test_sneaky_stack_debut():
    # Implied total <= 4.1, is_opp_debut is True (Trigger 3)
    res = evaluate_sneaky_stack(
        implied_total=3.9,
        team_xwoba=0.320,
        opp_pitcher_outs=16.5,
        is_opp_debut=True,
        opp_bullpen_score=10.0
    )
    assert res is True

def test_sneaky_stack_short_leash_fatigued_pen():
    # Implied total <= 4.1, opp_pitcher_outs <= 14.5 AND bullpen fatigue >= 55 (Trigger 4)
    res = evaluate_sneaky_stack(
        implied_total=4.0,
        team_xwoba=0.320,
        opp_pitcher_outs=14.0,
        is_opp_debut=False,
        opp_bullpen_score=65.0
    )
    assert res is True

def test_sneaky_stack_not_sneaky_high_implied():
    # Implied total > 4.1 should never trigger
    res = evaluate_sneaky_stack(
        implied_total=4.2,
        team_xwoba=0.360,
        opp_pitcher_outs=14.0,
        is_opp_debut=True,
        opp_bullpen_score=80.0
    )
    assert res is False

def test_sneaky_stack_not_sneaky_no_triggers():
    # Implied <= 4.1 but no volatility triggers met
    res = evaluate_sneaky_stack(
        implied_total=3.9,
        team_xwoba=0.320,
        opp_pitcher_outs=17.0,
        is_opp_debut=False,
        opp_bullpen_score=40.0
    )
    assert res is False

def test_apply_sneaky_stack_mutates_dict():
    team = {
        "implied_total": 3.7,
        "team_xwoba": 0.350,
        "bullpen_fatigue": 20.0,
        "is_gassed": False,
        "is_fatigued": False
    }
    apply_sneaky_stack(team, opp_pitcher_outs=18.0, is_opp_debut=False)
    assert team["is_sneaky"] is True
