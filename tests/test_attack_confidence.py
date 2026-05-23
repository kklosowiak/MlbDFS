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
        "dqi_status": "FADE",
        "dqi_score": 42,
        "bullpen_fatigue": 50,
    }
    conf, reasons = score_stack_confidence(t, [])
    assert conf < 70
    assert any("CHALK" in r or "DQI FADE" in r for r in reasons)


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
    }
    opp_p = {
        "pitcher": "Tarik Skubal",
        "physics_score": 25.0,
        "is_trap": False,
    }
    conf, reasons = score_stack_confidence(t_gassed, [opp_p])
    # Base 50 + 14 (xwOBA) + 10 (gassed BP) - 9 (tough SP penalty cut in half) = 65
    assert conf == 65
    assert any("bullpen is gassed" in r.lower() or "bullpen is exhausted" in r.lower() for r in reasons)
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

