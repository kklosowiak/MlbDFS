from utils.attack_confidence import score_pitcher_confidence


def test_pitcher_calibration_no_penalties():
    # A clean baseline pitcher with low ERA, low walks, and siera close to L3 ERA
    # recent_era_5g is no longer used by the engine (dead code removed, OMEGA v21.3)
    p = {
        "pitcher": "Clean Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 2.0,
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
    assert conf >= 50
    assert not any("Elevated L5 ERA" in r for r in reasons)
    assert not any("Elevated L3 ERA" in r for r in reasons)
    assert not any("significantly exceeds SIERA" in r for r in reasons)
    assert not any("Control crisis" in r for r in reasons)


def test_pitcher_calibration_l5_era_penalty_is_retired():
    # OMEGA v21.3: recent_era_5g penalty is removed (dead code).
    # A pitcher with only L5 ERA elevated (L3 clean) should NOT receive any ERA penalty.
    p = {
        "pitcher": "L5 Only Elevated",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 2.5,   # clean L3
        "recent_era_5g": 4.5,  # elevated L5 — ignored now
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
    # L5 ERA penalty is dead code — must NOT fire
    assert not any("Elevated L5 ERA" in r for r in reasons)
    # L3 ERA is clean — must NOT fire
    assert not any("Elevated L3 ERA" in r for r in reasons)


def test_pitcher_calibration_l3_era_penalty():
    # Pitcher has L3 ERA >= 4.50 — this penalty still fires at -6
    p = {
        "pitcher": "L3 Decline Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 4.8,
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


def test_pitcher_calibration_siera_divergence_penalty_reduced():
    # OMEGA v21.3: siera_div penalty reduced from -4 to -2.
    # L3 ERA - siera = 4.9 - 3.0 = 1.9 >= 1.50 -> fires at -2 (not -4).
    # L3 ERA >= 4.50 -> also fires at -6. Total = -8.
    p = {
        "pitcher": "Divergence Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 4.9,
        "recent_bb9": 2.0,
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
    # L3 ERA penalty fires
    assert any("Elevated L3 ERA (4.90)" in r for r in reasons)
    # siera_div penalty fires at -2 (not -4)
    assert any("L3 ERA (4.90) significantly exceeds SIERA (3.00) (-2)" in r for r in reasons)
    # L5 ERA penalty must NOT fire (dead code)
    assert not any("Elevated L5 ERA" in r for r in reasons)
    # siera_div must NOT say -4
    assert not any("(-4)" in r for r in reasons)


def test_pitcher_calibration_siera_div_no_l5_fallback():
    # OMEGA v21.3: the L5 siera_div arm is also removed.
    # Pitcher with clean L3 ERA but L5 ERA diverging from SIERA should NOT get a div penalty.
    p = {
        "pitcher": "L5 Div Only Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 3.0,    # clean L3 — no ERA penalty
        "recent_era_5g": 4.6, # L5-SIERA div = 4.6 - 2.8 = 1.8 — ignored (removed)
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
    # L5 ERA penalty must NOT fire
    assert not any("Elevated L5 ERA" in r for r in reasons)
    # L5 SIERA divergence must NOT fire
    assert not any("L5 ERA" in r for r in reasons)
    # L3 ERA is 3.0 (clean) — no L3 penalty either
    assert not any("Elevated L3 ERA" in r for r in reasons)


def test_pitcher_calibration_walk_crisis_penalty():
    # Walk crisis penalty unchanged at -6
    p = {
        "pitcher": "Wild Starter",
        "team": "Team A",
        "opponent": "Team B",
        "recent_era": 2.0,
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
