from utils.attack_confidence import score_pitcher_confidence

def test_pitcher_calibration_no_penalties():
    # A clean baseline pitcher with low ERA, low walks, and siera close to L3/L5 ERA
    p = {
        "pitcher": "Clean Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 2.0,
        "recent_era_5g": 2.2,
        "recent_bb9": 2.0,
        "siera": 2.5,
        "physics_score": 15,
        "is_trap": False,
        "is_sharp": False,
        "is_shark": False
    }
    t_reports = [
        {"team": "Team B", "team_xwoba": 0.310, "implied_total": 4.0}
    ]
    conf, reasons = score_pitcher_confidence(p, t_reports)
    # With a neutral profile, baseline conf should be decent, and no penalties in reasons
    assert conf >= 50
    assert not any("Elevated L5 ERA" in r for r in reasons)
    assert not any("Elevated L3 ERA" in r for r in reasons)
    assert not any("significantly exceeds SIERA" in r for r in reasons)
    assert not any("Control crisis" in r for r in reasons)

def test_pitcher_calibration_l5_era_penalty():
    # Pitcher has L5 ERA >= 4.25 but L3 is clean, siera is clean
    p = {
        "pitcher": "L5 Decline Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 2.5,
        "recent_era_5g": 4.5,
        "recent_bb9": 2.0,
        "siera": 4.0,
        "physics_score": 15,
        "is_trap": False,
        "is_sharp": False,
        "is_shark": False
    }
    t_reports = [
        {"team": "Team B", "team_xwoba": 0.310, "implied_total": 4.0}
    ]
    conf, reasons = score_pitcher_confidence(p, t_reports)
    assert any("Elevated L5 ERA (4.50)" in r for r in reasons)
    assert not any("Elevated L3 ERA" in r for r in reasons)

def test_pitcher_calibration_l3_era_penalty():
    # Pitcher has L3 ERA >= 4.50
    p = {
        "pitcher": "L3 Decline Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 4.8,
        "recent_era_5g": 3.5,
        "recent_bb9": 2.0,
        "siera": 4.5,
        "physics_score": 15,
        "is_trap": False,
        "is_sharp": False,
        "is_shark": False
    }
    t_reports = [
        {"team": "Team B", "team_xwoba": 0.310, "implied_total": 4.0}
    ]
    conf, reasons = score_pitcher_confidence(p, t_reports)
    assert any("Elevated L3 ERA (4.80)" in r for r in reasons)
    assert not any("Elevated L5 ERA" in r for r in reasons)

def test_pitcher_calibration_siera_divergence_penalty():
    # Pitcher L5 ERA exceeds SIERA by >= 1.50
    p = {
        "pitcher": "Divergence Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 3.0,
        "recent_era_5g": 4.6,
        "recent_bb9": 2.0,
        "siera": 2.8,
        "physics_score": 15,
        "is_trap": False,
        "is_sharp": False,
        "is_shark": False
    }
    t_reports = [
        {"team": "Team B", "team_xwoba": 0.310, "implied_total": 4.0}
    ]
    conf, reasons = score_pitcher_confidence(p, t_reports)
    # L5 ERA = 4.6 >= 4.25 (penalty -6)
    # L5 ERA - siera = 4.6 - 2.8 = 1.8 >= 1.50 (penalty -4)
    # Total penalty = -10
    assert any("Elevated L5 ERA (4.60)" in r for r in reasons)
    assert any("L5 ERA (4.60) significantly exceeds SIERA (2.80)" in r for r in reasons)

def test_pitcher_calibration_walk_crisis_penalty():
    # Pitcher has BB/9 >= 4.5
    p = {
        "pitcher": "Wild Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 2.0,
        "recent_era_5g": 2.0,
        "recent_bb9": 5.0,
        "siera": 3.0,
        "physics_score": 15,
        "is_trap": False,
        "is_sharp": False,
        "is_shark": False
    }
    t_reports = [
        {"team": "Team B", "team_xwoba": 0.310, "implied_total": 4.0}
    ]
    conf, reasons = score_pitcher_confidence(p, t_reports)
    assert any("Control crisis: elevated L3 BB/9 (5.00)" in r for r in reasons)
