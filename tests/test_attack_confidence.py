from utils.attack_confidence import score_stack_confidence, score_pitcher_confidence
from utils.team_prop_pressure import compute_team_prop_pressure, LABEL_COLD, LABEL_HOT


def test_prop_pressure_hot_with_targets():
    hitters = [
        {"name": "A", "team": "Boston Red Sox", "is_juiced_target": True, "matchup_xwoba": 0.360, "_juice_gap": 20},
        {"name": "B", "team": "Boston Red Sox", "is_prop_juice": True, "runs_juice": True, "matchup_xwoba": 0.350, "_juice_gap": 10},
        {"name": "C", "team": "Boston Red Sox", "is_prop_juice": True, "rbis_juice": True, "matchup_xwoba": 0.345, "_juice_gap": 8},
    ]
    m = compute_team_prop_pressure("Boston Red Sox", hitters)
    assert m["prop_pressure_label"] in (LABEL_HOT, "WARM")
    assert m["prop_target_count"] >= 1


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


def test_pitcher_conf_uses_xwoba_not_stack_score():
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
    t_reports = [{"team": "COL", "team_xwoba": 0.355, "prop_pressure_label": LABEL_HOT}]
    conf, reasons = score_pitcher_confidence(p, t_reports)
    assert conf < 60
    assert any("HOT prop" in r or "Tough matchup" in r for r in reasons)
