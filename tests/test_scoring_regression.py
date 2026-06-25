from engine.sharps_weighting import SharpsWeighting

def test_stack_score_consolidation_regression():
    engine = SharpsWeighting()

    # 1. Base control stack score (no debut)
    # Using opp_pitcher_physics=50.0 to avoid magnetism_boost capping the multiplier at 1.35
    base_res = engine.calculate_stack_score(
        team="Boston Red Sox", ml_move=0, tt_move=0, curr_itt=4.5,
        team_xwoba=0.330, power_concentration=0.330, park_factor=1.0,
        bullpen_fatigue=0, divergence=0, is_sharp=False,
        is_shark=False, is_steam=False, opp_pitcher_physics=50.0,
        confidence='high', pitcher_outs=18.0, implied_total=4.5,
        is_burst=False, opponent="NYY", is_anti_chalk_smash=False,
        is_pitch_alignment=False, opp_pitcher_trap=False
    )

    # 2. OMEGA v17.2: sneaky stack score premium removed — parameter no longer accepted
    # (is_sneaky removed from engine signature in v19.3)
    # Base score is the correct comparison point; any caller passing is_sneaky previously got 0.0 delta
    assert round(base_res['final'], 1) > 0.0  # Sanity: score is positive

    # 3. Test debut pitcher boost (1.10x final stack score multiplier)
    debut_res = engine.calculate_stack_score(
        team="Boston Red Sox", ml_move=0, tt_move=0, curr_itt=4.5,
        team_xwoba=0.330, power_concentration=0.330, park_factor=1.0,
        bullpen_fatigue=0, divergence=0, is_sharp=False,
        is_shark=False, is_steam=False, opp_pitcher_physics=50.0,
        confidence='high', pitcher_outs=18.0, implied_total=4.5,
        is_burst=False, opponent="NYY", is_anti_chalk_smash=False,
        is_pitch_alignment=False, opp_pitcher_trap=False,
        is_opp_debut=True
    )
    # The final debut score should be approximately 1.10 times the base score
    assert round(debut_res['final'] / base_res['final'], 2) == 1.10

    # 4. OMEGA v19.3: is_storm scoring REMOVED from engine
    # (storm = divergence>=10 AND tt_move>=0.3; is_sharp/is_steam already claim their beta slots)
    # No storm test case — the parameter no longer exists in calculate_stack_score


def test_pitcher_score_consolidation_regression():
    engine = SharpsWeighting()

    # 1. Base control pitcher score
    base_res = engine.calculate_pitcher_score(
        name="Tanner Bibee", ml_move=0, tt_move=0, money_gap=0, k_prop=6.0,
        siera=3.50, csw=0.28, is_target=False, park_factor=100, divergence=0,
        is_shark=False, opponent_k_boost=0, is_low_ceiling=False,
        projected_outs=18.0, is_trap=False, is_sharp=False, curr_ml=-110
    )

    # 2. Test Pinnacle SP Boost (+5.0 engine score points)
    pin_res = engine.calculate_pitcher_score(
        name="Tanner Bibee", ml_move=0, tt_move=0, money_gap=0, k_prop=6.0,
        siera=3.50, csw=0.28, is_target=False, park_factor=100, divergence=0,
        is_shark=False, opponent_k_boost=0, is_low_ceiling=False,
        projected_outs=18.0, is_trap=False, is_sharp=False, curr_ml=-110,
        pinnacle_boost_active=True
    )
    assert round(pin_res['final'] - base_res['final'], 1) == 5.0

    # 3. Test recent form boost
    form_res = engine.calculate_pitcher_score(
        name="Tanner Bibee", ml_move=0, tt_move=0, money_gap=0, k_prop=6.0,
        siera=3.50, csw=0.28, is_target=False, park_factor=100, divergence=0,
        is_shark=False, opponent_k_boost=0, is_low_ceiling=False,
        projected_outs=18.0, is_trap=False, is_sharp=False, curr_ml=-110,
        form_boost=5.0
    )
    assert round(form_res['final'] - base_res['final'], 1) == 5.0

    # 4. Test death sentence penalty (-15%)
    death_res = engine.calculate_pitcher_score(
        name="Tanner Bibee", ml_move=0, tt_move=0, money_gap=0, k_prop=6.0,
        siera=3.50, csw=0.28, is_target=False, park_factor=100, divergence=0,
        is_shark=False, opponent_k_boost=0, is_low_ceiling=False,
        projected_outs=18.0, is_trap=False, is_sharp=False, curr_ml=-110,
        is_death_sentence=True
    )
    assert round(death_res['final'] / base_res['final'], 2) == 0.85


def test_hitter_score_consolidation_regression():
    engine = SharpsWeighting()
    
    # 1. Base control hitter score
    base_res = engine.calculate_individual_hitter_score(
        player_name="Aaron Judge", team_score=60.0, matchup_xwoba=0.360, ahr_price=350,
        park_factor=1.0, is_target=False, is_speed_target=False, is_hot=False
    )
    
    # 2. Test hard hit / barrel profile boosts
    # hard_hit_pct >= 45.0 (+3%) and barrel_pct >= 12.0 (+2%)
    boosted_res = engine.calculate_individual_hitter_score(
        player_name="Aaron Judge", team_score=60.0, matchup_xwoba=0.360, ahr_price=350,
        park_factor=1.0, is_target=False, is_speed_target=False, is_hot=False,
        hard_hit_pct=46.0, barrel_pct=13.0
    )
    # Boost should be exactly 1.03 * 1.02 = 1.0506 times the base score
    assert round(boosted_res['final'] / base_res['final'], 2) == 1.05

    # 3. Test hits suppression penalty (0.80x multiplier when hits_line <= 0.5 and price > 0)
    suppressed_res = engine.calculate_individual_hitter_score(
        player_name="Aaron Judge", team_score=60.0, matchup_xwoba=0.360, ahr_price=350,
        park_factor=1.0, is_target=False, is_speed_target=False, is_hot=False,
        hits_line=0.5, hits_price=110.0
    )
    assert round(suppressed_res['final'] / base_res['final'], 2) == 0.80
