from engine.sharps_weighting import SharpsWeighting

def test_pitcher_score_robustness():
    engine = SharpsWeighting()
    # Ensure raw None parameters do not crash the pitcher scoring engine
    res = engine.calculate_pitcher_score(
        name="None SP", ml_move=None, tt_move=None, money_gap=None, k_prop=None,
        siera=None, csw=None, is_target=False, park_factor=None, divergence=None,
        is_shark=False, is_whale=False, opponent_k_boost=None, is_low_ceiling=False,
        projected_outs=None, is_trap=False, is_sharp=False, curr_ml=None
    )
    assert res['final'] is not None
    assert res['physics_talent'] is not None
    assert res['market'] is not None

def test_stack_score_robustness():
    engine = SharpsWeighting()
    # Ensure raw None parameters do not crash the stack scoring engine
    res = engine.calculate_stack_score(
        team="None Stack", ml_move=None, tt_move=None, curr_itt=None,
        team_xwoba=None, power_concentration=None, park_factor=None,
        bullpen_fatigue=None, divergence=None, is_whale=False, is_sharp=False,
        is_storm=False, is_shark=False, is_steam=False, opp_pitcher_physics=None,
        confidence='high', pitcher_outs=None, opponent="OPP", is_opp_debut=False
    )
    assert res['final'] is not None
    assert res['physics'] is not None
    assert res['market'] is not None

def test_hitter_score_robustness():
    engine = SharpsWeighting()
    # Ensure raw None parameters do not crash the hitter scoring engine
    res = engine.calculate_individual_hitter_score(
        player_name="None Hitter", team_score=None, matchup_xwoba=None, ahr_price=None,
        park_factor=None, is_target=False, is_speed_target=False, is_hot=False
    )
    assert res['final'] is not None
    assert res['solo_score'] is not None
    assert res['physics_component'] is not None
