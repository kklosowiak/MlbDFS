from utils.attack_confidence import score_stack_confidence, score_pitcher_confidence
from utils.team_prop_pressure import (
    attach_team_prop_pressure,
    compute_team_prop_pressure,
    LABEL_COLD,
    LABEL_HOT,
    LABEL_NEUTRAL,
    LABEL_WARM,
)


def test_prop_pressure_hot_requires_strict_targets_and_stack_depth():
    hitters = [
        {"name": "A", "team": "Boston Red Sox", "is_juiced_target": True, "matchup_xwoba": 0.360},
        {"name": "B", "team": "Boston Red Sox", "is_juiced_target": True, "runs_target": True, "matchup_xwoba": 0.350},
        {"name": "C", "team": "Boston Red Sox", "is_juiced_target": True, "rbis_target": True, "matchup_xwoba": 0.345},
    ]
    teams = [{"team": "Boston Red Sox"}, {"team": "Kansas City Royals"}]
    attach_team_prop_pressure(teams, hitters)
    bos = next(t for t in teams if "Boston" in t["team"])
    assert bos["prop_target_count"] >= 3
    assert bos["prop_stack_target_count"] >= 1
    assert bos["prop_pressure_raw"] >= 22
    assert bos["prop_pressure_label"] == LABEL_HOT
    assert bos["prop_pressure_elite"] is True


def test_two_targets_without_stack_targets_not_hot():
    hitters = [
        {"name": "A", "team": "Team X", "is_juiced_target": True, "matchup_xwoba": 0.36},
        {"name": "B", "team": "Team X", "is_juiced_target": True, "matchup_xwoba": 0.35},
        {"name": "C", "team": "Team X", "is_prop_juice": True, "runs_juice": True, "matchup_xwoba": 0.34},
        {"name": "D", "team": "Team X", "is_prop_juice": True, "rbis_juice": True, "matchup_xwoba": 0.33},
    ]
    teams = [{"team": "Team X"}, {"team": "Team Y"}]
    attach_team_prop_pressure(teams, hitters)
    assert teams[0]["prop_target_count"] == 2
    assert teams[0]["prop_stack_target_count"] == 0
    assert teams[0]["prop_pressure_label"] != LABEL_HOT


def test_multiple_teams_can_be_hot_without_slate_cap():
    hitters = []
    for team in ("Team A", "Team B", "Team C", "Team D", "Team E"):
        hitters.extend([
            {
                "name": f"{team}-T{i}",
                "team": team,
                "is_juiced_target": True,
                "runs_target": True,
                "matchup_xwoba": 0.35,
            }
            for i in range(3)
        ])
    teams = [{"team": t} for t in ("Team A", "Team B", "Team C", "Team D", "Team E")]
    attach_team_prop_pressure(teams, hitters)
    hot_count = sum(1 for t in teams if t["prop_pressure_label"] == LABEL_HOT)
    assert hot_count == 5


def test_soft_juice_alone_not_hot():
    hitters = [
        {"name": f"H{i}", "team": "Team A", "is_prop_juice": True, "matchup_xwoba": 0.33}
        for i in range(6)
    ]
    m = compute_team_prop_pressure("Team A", hitters)
    assert m["prop_target_count"] == 0
    assert m["prop_pressure_raw"] == 0

    teams = [{"team": "Team A"}, {"team": "Team B"}]
    attach_team_prop_pressure(teams, hitters)
    assert teams[0]["prop_pressure_label"] not in (LABEL_HOT, LABEL_WARM)


def test_warm_is_moderate_not_every_team():
    hitters = [
        {"name": "A", "team": "Team Z", "is_juiced_target": True, "matchup_xwoba": 0.35},
        {"name": "B", "team": "Team Z", "is_juiced_target": True, "matchup_xwoba": 0.34},
    ]
    teams = [{"team": "Team Z"}, {"team": "Team W"}]
    attach_team_prop_pressure(teams, hitters)
    assert teams[0]["prop_pressure_label"] == LABEL_NEUTRAL


def test_stack_conf_penalizes_chalk_and_cold_props():
    t = {
        "team": "Miami Marlins",
        "team_xwoba": 0.345,
        "is_trap": True,
        "prop_pressure_label": LABEL_COLD,
        "lineup_status": "CONFIRMED",
        "divergence": 18,
        "dqi_status": "LEVERAGE",
        "dqi_score": 42,
        "bullpen_fatigue": 50,
    }
    conf, reasons = score_stack_confidence(t, [])
    assert conf < 70
    assert any("CHALK" in r or "DQI LEVERAGE" in r for r in reasons)


def test_stack_conf_boosts_leverage():
    t_base = {
        "team": "Miami Marlins",
        "team_xwoba": 0.300,
        "implied_total": 4.5,
        "lineup_status": "CONFIRMED",
    }
    t_leverage = {
        **t_base,
        "dqi_status": "LEVERAGE",
        "dqi_score": 42,
    }
    conf_base, _ = score_stack_confidence(t_base, [])
    conf_leverage, reasons_leverage = score_stack_confidence(t_leverage, [])
    # LEVERAGE should add exactly +8.0 confidence points
    assert conf_leverage - conf_base == 8.0
    assert any("DQI LEVERAGE" in r for r in reasons_leverage)


def test_pitcher_prop_penalty_only_elite_board():
    p = {
        "pitcher": "Test SP",
        "opponent": "COL",
        "physics_score": 18,
        "form_status": None,
        "is_trap": False,
        "sharp_fade": False,
        "is_juiced_target": True,
        "divergence": 5,
    }
    opp_neutral = {
        "team": "COL",
        "team_xwoba": 0.355,
        "prop_pressure_label": LABEL_NEUTRAL,
        "prop_pressure_elite": False,
        "prop_target_count": 2,
        "prop_stack_target_count": 0,
    }
    conf_n, reasons_n = score_pitcher_confidence(p, [opp_neutral])
    assert not any("prop board" in r.lower() for r in reasons_n)

    opp_hot = {
        **opp_neutral,
        "prop_pressure_label": LABEL_HOT,
        "prop_pressure_elite": True,
        "prop_target_count": 3,
        "prop_stack_target_count": 2,
    }
    conf_h, reasons_h = score_pitcher_confidence(p, [opp_hot])
    assert any("elite prop board" in r for r in reasons_h)


def test_anti_chalk_smash_and_pitch_alignment_overrides():
    # Test Anti-Chalk Smash (+8 Stack CONF)
    t_anti = {
        "team": "Los Angeles Angels",
        "opp_pitcher": "Gerrit Cole",
        "is_anti_chalk_smash": True,
        "team_xwoba": 0.320,
    }
    conf_anti, reasons_anti = score_stack_confidence(t_anti, [])
    assert conf_anti >= 58  # Base 50 + 8
    assert any("ANTI-CHALK SMASH" in r for r in reasons_anti)

    # Test Pitch Alignment (+8 Stack CONF)
    t_align = {
        "team": "Seattle Mariners",
        "opp_pitcher": "Kevin Gausman",
        "is_pitch_alignment": True,
        "team_xwoba": 0.320,
    }
    conf_align, reasons_align = score_stack_confidence(t_align, [])
    assert conf_align >= 58  # Base 50 + 8
    assert any("PITCH ALIGNMENT" in r for r in reasons_align)


def test_bullpen_exhausted_dampens_tough_sp_penalty():
    t_gassed = {
        "team": "Detroit Tigers",
        "opp_pitcher": "Tarik Skubal",
        "bullpen_fatigue": 95,
        "is_gassed": True,
        "team_xwoba": 0.320,
        "implied_total": 4.0,
    }
    opp_p = {
        "pitcher": "Tarik Skubal",
        "physics_score": 55.0,
        "is_trap": False,
        "confidence": "high",
        "market_score": 10.0,
    }
    conf, reasons = score_stack_confidence(t_gassed, [opp_p])
    # Base 50 + 12 (xwOBA) + 14 (gassed BP) - 20.4 (tough SP penalty cut by 15%) = 55.6 -> 56
    assert conf == 56
    assert any("opposing pen exhausted" in r.lower() or "opponent bullpen is exhausted" in r.lower() for r in reasons)
    assert any("but opponent bullpen is exhausted" in r for r in reasons)


def test_pitcher_pitch_alignment_penalty():
    p = {
        "pitcher": "Kevin Gausman",
        "opponent": "SEA",
        "physics_score": 20,
        "is_juiced_target": False,
        "divergence": 0,
    }
    opp_t = {
        "team": "SEA",
        "is_pitch_alignment": True,
    }
    conf, reasons = score_pitcher_confidence(p, [opp_t])
    assert any("Tough matchup: Opposing lineup has elite pitch-type alignment" in r for r in reasons)


def test_asymptotic_compression_retains_hierarchy():
    # If raw score is very high (e.g. 120 vs 98), compression should distinguish them
    t_120 = {
        "team": "Braves",
        "team_xwoba": 0.360,
        "implied_total": 5.2,
        "is_gassed": True,
        "opp_pitcher_outs": 14.0,  # 2 signals: gassed + outs -> Gassed Bullpen Attack
        "dqi_status": "TRUST",
        "lineup_status": "CONFIRMED",
        "is_sharp": True,
    }
    # Reds: slightly weaker but still elite
    t_110 = {
        "team": "Reds",
        "team_xwoba": 0.320,
        "implied_total": 4.8,
        "is_gassed": True,
        "opp_pitcher_outs": 14.0,
        "dqi_status": "TRUST",
        "lineup_status": "CONFIRMED",
    }
    
    conf_120, _ = score_stack_confidence(t_120, [])
    conf_110, _ = score_stack_confidence(t_110, [])
    
    assert conf_120 > conf_110
    assert conf_120 < 100
    assert conf_110 < 100


def test_implied_total_brackets():
    # Elite stack with 5.2 implied total
    t_high = {
        "team": "A",
        "team_xwoba": 0.320,
        "implied_total": 5.2,
    }
    # Solid stack with 4.6 implied total
    t_mid = {
        "team": "B",
        "team_xwoba": 0.320,
        "implied_total": 4.6,
    }
    # Neutral stack with 4.1 implied total
    t_neu = {
        "team": "C",
        "team_xwoba": 0.320,
        "implied_total": 4.1,
    }
    # Caution stack with 3.6 implied total
    t_low = {
        "team": "D",
        "team_xwoba": 0.320,
        "implied_total": 3.6,
    }
    
    c_high, _ = score_stack_confidence(t_high, [])
    c_mid, _ = score_stack_confidence(t_mid, [])
    c_neu, _ = score_stack_confidence(t_neu, [])
    c_low, _ = score_stack_confidence(t_low, [])
    
    assert c_high > c_mid
    assert c_mid > c_neu
    assert c_neu > c_low


def test_weather_and_umpire_calibrations():
    # Stack with Orange weather (delay) and wind blowing in
    t_weather_bad = {
        "team": "A",
        "team_xwoba": 0.320,
        "weather_label": "🟠 52° / In 12mph",
    }
    # Stack with Red weather (postponement)
    t_weather_worst = {
        "team": "B",
        "team_xwoba": 0.320,
        "weather_label": "🔴 52° / Neutral 5mph",
    }
    # Stack with warm temp, wind out, and hitter-friendly umpire
    t_weather_good = {
        "team": "C",
        "team_xwoba": 0.320,
        "weather_label": "🟢 82° / Out 12mph",
        "umpire_factor": 1.05,
    }
    
    c_bad, r_bad = score_stack_confidence(t_weather_bad, [])
    c_worst, r_worst = score_stack_confidence(t_weather_worst, [])
    c_good, r_good = score_stack_confidence(t_weather_good, [])
    
    assert c_good > c_bad
    assert c_bad > c_worst
    assert any("WEATHER DELAY RISK" in r for r in r_bad)
    assert any("WEATHER POSTPONEMENT RISK" in r for r in r_worst)
    assert any("High temperature boost" in r for r in r_good)
    assert any("Hitter-friendly wind blowing out" in r for r in r_good)
    assert any("Hitter-friendly umpire assigned" in r for r in r_good)


def test_matchup_boost_caps():
    # SP with trap + cold + sharp fade (raw 14 + 12 + 6 = 32, should cap at 20)
    t = {
        "team": "A",
        "team_xwoba": 0.320,
        "opp_pitcher": "Test SP",
    }
    opp_p = {
        "pitcher": "Test SP",
        "is_trap": True,
        "form_status": "COLD",
        "sharp_fade": True,
        "physics_score": 15,
    }
    
    c, reasons = score_stack_confidence(t, [opp_p])
    assert any("SP Matchup Boost capped at +20" in r for r in reasons)


def test_unanchored_chalk_stack_capping():
    # High raw confidence stack but 0 conviction signals -> should soft-cap at 84
    t_unanchored = {
        "team": "A",
        "team_xwoba": 0.345,
        "implied_total": 5.2,
        "lineup_status": "CONFIRMED",
        "weather_label": "🟢 82° / Out 12mph",
        "dqi_status": "CAUTION",
        "divergence": 0,
        "bullpen_fatigue": 50,
        "prop_pressure_elite": False,
        "prop_pressure_label": LABEL_NEUTRAL,
        "is_anti_chalk_smash": False,
        "is_pitch_alignment": False,
        "is_gassed": False,
    }
    conf, reasons = score_stack_confidence(t_unanchored, [])
    assert conf == 81
    assert any("Soft-capped above 75" in r for r in reasons)

    # Adding 2 conviction signals -> should remain uncapped (94)
    t_anchored = {
        **t_unanchored,
        "divergence": 0,
        "is_pitch_alignment": True,  # signal 1
        "is_anti_chalk_smash": True,  # signal 2
        "weather_label": "🟢 82° / Neutral 5mph", # drop wind boost to keep raw score at 108
    }
    conf_anchored, reasons_anchored = score_stack_confidence(t_anchored, [])
    assert conf_anchored == 94
    assert not any("Soft-capped above 75" in r for r in reasons_anchored)


def test_tiered_volatile_sp_modifier():
    # Base team stack config
    t = {
        "team": "Team A",
        "team_xwoba": 0.330,
        "implied_total": 4.5,
        "lineup_status": "CONFIRMED",
        "divergence": 0,
        "bullpen_fatigue": 50,
        "opp_pitcher": "Tough SP",
    }

    # Case 1: Low-sample SP (confidence is low) -> 100% Dampening (0.0 multiplier, no penalty)
    opp_p_low_ip = {
        "pitcher": "Tough SP",
        "physics_score": 55.0,  # tough SP physics
        "confidence": "low",
        "market_score": 10.0,
    }
    conf_low_ip, reasons_low_ip = score_stack_confidence(t, [opp_p_low_ip])

    # Case 2: Standard tough SP -> Full penalty (-24.0)
    opp_p_standard = {
        "pitcher": "Tough SP",
        "physics_score": 55.0,
        "confidence": "high",
        "market_score": 10.0,
    }
    conf_standard, reasons_standard = score_stack_confidence(t, [opp_p_standard])
    
    # Check that low IP did not receive the penalty, so its confidence is 24 points higher than standard
    assert conf_low_ip - conf_standard == 24
    assert any("Tough but volatile (low-sample SP)" in r for r in reasons_low_ip)
    assert any("Tough solid-tier SP" in r or "Tough ace-tier SP" in r for r in reasons_standard)

    # Case 3: Market underdogs (market_score == 0.0) -> 50% Dampening (0.5 multiplier, penalty reduced by 12)
    opp_p_market_0 = {
        "pitcher": "Tough SP",
        "physics_score": 55.0,
        "confidence": "high",
        "market_score": 0.0,
    }
    conf_market_0, reasons_market_0 = score_stack_confidence(t, [opp_p_market_0])
    
    # Check that market 0 penalty is dampened by 50% (difference of 12 points compared to standard)
    assert conf_market_0 - conf_standard == 12
    assert any("Tough but volatile (unanchored market SP)" in r for r in reasons_market_0)


def test_msmi_calibrations():
    # Base team stack config with neutral xwOBA (0.300) to keep scores in the linear range (below 75)
    t_neutral = {
        "team": "Team A",
        "team_xwoba": 0.300,
        "implied_total": 4.5,
        "lineup_status": "CONFIRMED",
    }
    
    t_slump = {
        **t_neutral,
        "is_cold_streak": True
    }
    
    t_surge = {
        **t_neutral,
        "is_hot_run": True
    }
    
    conf_neu, _ = score_stack_confidence(t_neutral, [])
    conf_slump, reasons_slump = score_stack_confidence(t_slump, [])
    conf_surge, reasons_surge = score_stack_confidence(t_surge, [])
    
    # Slump penalty is -24.0
    assert conf_neu - conf_slump == 24
    assert any("Team Slate Slump (MSMI)" in r for r in reasons_slump)
    
    # Surge boost is +12.0
    assert conf_surge - conf_neu == 12
    assert any("Team Hot Run (MSMI)" in r for r in reasons_surge)


def test_divergence_calibrations_v16_1():
    # 1. Base control team stack (no divergence, no DQI)
    # Using team_xwoba=0.280 to keep scores in the linear range (below 75) to test exact deltas
    t_base = {
        "team": "A",
        "team_xwoba": 0.280,
        "implied_total": 4.5,
        "lineup_status": "CONFIRMED",
        "divergence": 0,
        "dqi_status": "CAUTION"
    }
    
    # 2. Test negative divergence GPP leverage boost (div <= -12% -> +6.0 CONF)
    t_neg_12 = {
        **t_base,
        "divergence": -15
    }
    conf_base, _ = score_stack_confidence(t_base, [])
    conf_neg_12, reasons_neg_12 = score_stack_confidence(t_neg_12, [])
    
    assert conf_neg_12 - conf_base == 6
    assert any("Under-the-radar GPP leverage" in r for r in reasons_neg_12)
    
    # 3. Test elite negative divergence GPP leverage boost (div <= -20% -> +10.0 CONF)
    t_neg_20 = {
        **t_base,
        "divergence": -22
    }
    conf_neg_20, reasons_neg_20 = score_stack_confidence(t_neg_20, [])
    assert conf_neg_20 - conf_base == 10
    assert any("Institutional GPP leverage" in r for r in reasons_neg_20)

    # 4. Test positive divergence steam trap penalty (div >= 10% and < 20% -> -8.0 CONF)
    t_pos_15 = {
        **t_base,
        "divergence": 15
    }
    conf_pos_15, reasons_pos_15 = score_stack_confidence(t_pos_15, [])
    assert conf_base - conf_pos_15 == 8
    assert any("Public/ML steam trap" in r for r in reasons_pos_15)

    # 5. Test DQI TRUST override retired (divergence >= 12%, dqi_status = TRUST -> no boost, steam penalty applied)
    t_trust = {
        **t_base,
        "divergence": 15,
        "dqi_status": "TRUST",
        "dqi_score": 80,
        "bullpen_fatigue": 70  # to pass DQI TRUST gates
    }
    conf_trust, reasons_trust = score_stack_confidence(t_trust, [])
    # TRUST boost is retired (+0), steam penalty of -8.0 is applied
    assert conf_trust - conf_base == -8.0
    assert any("DQI TRUST" in r for r in reasons_trust)
    assert any("Public/ML steam trap" in r for r in reasons_trust)


def test_bullpen_fatigue_scaled_by_quality():
    # Base control team stack (no divergence, no DQI)
    # Using team_xwoba=0.280 to keep scores in the linear range (below 75) to test exact deltas
    t_base = {
        "team": "Tigers",
        "team_xwoba": 0.280,
        "implied_total": 4.5,
        "lineup_status": "CONFIRMED",
        "divergence": 0,
        "dqi_status": "CAUTION"
    }

    # 1. Opponent with Elite Pen: Atlanta Braves (ERA 2.87 < 3.50) -> +8.0 CONF
    t_elite = {
        **t_base,
        "opponent": "Atlanta Braves",
        "bullpen_fatigue": 90
    }
    # 2. Opponent with Poor Pen: Colorado Rockies (ERA 5.80 > 4.20) -> +19.0 CONF
    t_poor = {
        **t_base,
        "opponent": "Colorado Rockies",
        "bullpen_fatigue": 90
    }
    # 3. Opponent with Average Pen: Cleveland Guardians (ERA 3.76) -> +14.0 CONF
    t_avg = {
        **t_base,
        "opponent": "Cleveland Guardians",
        "bullpen_fatigue": 90
    }

    c_base, _ = score_stack_confidence(t_base, [])
    c_elite, r_elite = score_stack_confidence(t_elite, [])
    c_poor, r_poor = score_stack_confidence(t_poor, [])
    c_avg, r_avg = score_stack_confidence(t_avg, [])

    assert c_elite - c_base == 8
    assert any("Opposing elite pen fatigued" in r for r in r_elite)

    assert c_poor - c_base == 19
    assert any("Opposing poor pen fatigued" in r for r in r_poor)

    assert c_avg - c_base == 14
    assert any("Opposing pen exhausted" in r for r in r_avg)


def test_pitcher_weather_temperature_penalty():
    # Pitcher with warm weather (80F) outdoor
    p_warm = {
        "pitcher": "Test SP",
        "opponent": "COL",
        "physics_score": 15,
        "form_status": None,
        "is_trap": False,
        "sharp_fade": False,
        "is_juiced_target": False,
        "divergence": 0,
    }
    opp_t = {
        "team": "COL",
        "weather_label": "🟢 82° / Out 10mph",
    }
    
    # Control pitcher with normal weather (70F)
    p_normal = {
        **p_warm,
        "opponent": "LAD"
    }
    opp_normal = {
        "team": "LAD",
        "weather_label": "🟢 70° / Neutral 5mph",
    }

    c_normal, _ = score_pitcher_confidence(p_normal, [opp_normal])
    c_warm, r_warm = score_pitcher_confidence(p_warm, [opp_t])
    
    # Warm weather penalty of -7.0 instead of -5.0. 
    # Also wind blowing out 10mph subtracts 6.0 in both versions, so the difference is exactly 7.0.
    # Control has no weather penalty or wind penalty.
    # Normal score: base 50 - 14 (physics < 10) = 36
    # Warm score: base 50 - 14 (physics < 10) - 7 (weather temp) - 6 (wind out) = 23
    assert c_normal - c_warm == 13 # 7.0 temp penalty + 6.0 wind penalty
    assert any("Weather temperature drag (82°F)" in r for r in r_warm)


def test_hitter_batting_order_confidence_adjustments():
    from utils.hitter_confidence import score_hitter_confidence
    
    # Neutral base hitter
    h_base = {
        "name": "Base Hitter",
        "matchup_xwoba": 0.330,
    }

    # Leadoff hitter (+5)
    h_1 = {**h_base, "batting_order": 1}
    # Clean-up hitter (+2)
    h_4 = {**h_base, "batting_order": 4}
    # 7-hole hitter (-4)
    h_7 = {**h_base, "batting_order": 7}
    # 8-hole hitter (-8)
    h_8 = {**h_base, "batting_order": 8}
    # 9-hole hitter (-12)
    h_9 = {**h_base, "batting_order": 9}

    c_base, _ = score_hitter_confidence(h_base)
    c_1, r_1 = score_hitter_confidence(h_1)
    c_4, r_4 = score_hitter_confidence(h_4)
    c_7, r_7 = score_hitter_confidence(h_7)
    c_8, r_8 = score_hitter_confidence(h_8)
    c_9, r_9 = score_hitter_confidence(h_9)

    assert c_1 - c_base == 5
    assert any("Order Spot 1-2 boost" in r for r in r_1)

    assert c_4 - c_base == 2
    assert any("Order Spot 3-4 boost" in r for r in r_4)

    assert c_base - c_7 == 5
    assert any("Order Spot 7 penalty" in r for r in r_7)

    assert c_base - c_8 == 5
    assert any("Order Spot 8 penalty" in r for r in r_8)

    assert c_base - c_9 == 12
    assert any("Order Spot 9 penalty" in r for r in r_9)


def test_early_innings_volatility_pitcher_penalty():
    from utils.attack_confidence import score_pitcher_confidence
    p_normal = {
        "pitcher": "Normal SP",
        "team": "Braves",
        "opponent": "Brewers",
        "physics_score": 10.0,
    }
    p_short = {
        **p_normal,
        "early_innings_volatility": True
    }
    opp_t = {
        "team": "Brewers",
        "implied_total": 4.5,
    }
    c_normal, _ = score_pitcher_confidence(p_normal, [opp_t])
    c_short, r_short = score_pitcher_confidence(p_short, [opp_t])
    assert c_normal - c_short == 10
    assert any("Early-innings volatility (IP/start < 4.5) — low QS ceiling." in r for r in r_short)


def test_prop_pressure_labels_retired_from_scoring():
    t_base = {
        "team": "Brewers",
        "team_xwoba": 0.320,
        "implied_total": 4.5,
        "lineup_status": "CONFIRMED",
        "prop_pressure_label": "NEUTRAL",
        "prop_pressure_elite": False,
        "prop_target_count": 0,
        "prop_pressure_score": 0,
    }
    t_hot = {
        **t_base,
        "prop_pressure_label": "HOT",
        "prop_pressure_elite": True,
        "prop_target_count": 3,
        "prop_pressure_score": 75,
    }
    t_warm = {
        **t_base,
        "prop_pressure_label": "WARM",
        "prop_target_count": 1,
        "prop_pressure_score": 25,
    }

    conf_base, reasons_base = score_stack_confidence(t_base, [])
    conf_hot, reasons_hot = score_stack_confidence(t_hot, [])
    conf_warm, reasons_warm = score_stack_confidence(t_warm, [])

    # The confidence score should be identical regardless of prop pressure label
    # as the scoring influence has been retired.
    assert conf_base == conf_hot
    assert conf_base == conf_warm
    
    # But the reasons list should still include informational descriptions.
    assert any("Elite prop board" in r for r in reasons_hot)
    assert any("Moderate prop interest" in r for r in reasons_warm)


def test_short_leash_soft_cap():
    t = {
        "team": "Team A",
        "opp_pitcher": "Pitcher A",
        "team_xwoba": 0.345,
        "implied_total": 5.2,
        "lineup_status": "CONFIRMED",
        "dqi_status": "CAUTION",
        "divergence": 0,
        "bullpen_fatigue": 50,
        "is_anti_chalk_smash": False,
        "is_pitch_alignment": True,
        "is_gassed": False,
        "is_steam": False,
    }
    
    opp_p = {
        "pitcher": "Pitcher A",
        "early_innings_volatility": True,
        "k_line": 3.5,
        "is_low_ceiling": True,
    }
    
    conf, reasons = score_stack_confidence(t, [opp_p])
    assert conf == 75
    assert any("Soft-capped above 75 — short-leash SP requires 2+ of STEAM/GASSED-PEN." in r for r in reasons)
    
    t_conviction = {
        **t,
        "is_steam": True,
        "is_gassed": True,
    }
    conf_conv, reasons_conv = score_stack_confidence(t_conviction, [opp_p])
    assert not any("short-leash SP requires 2+" in r for r in reasons_conv)








