from utils.team_signals import apply_team_blind_spot, team_blind_spot_gap, BLIND_SPOT_MIN_GAP


def test_blind_spot_gap_uses_display_scores():
    assert team_blind_spot_gap(89.2, 58.1) == 31.1
    assert team_blind_spot_gap(82.5, 59.8) == 22.7


def test_apply_team_blind_spot_threshold():
    t = {"physics_score": 89.2, "market_score": 58.1}
    apply_team_blind_spot(t)
    assert t["blind_spot_gap"] == 31.1
    assert t["is_blind_spot"] is False

    t2 = {"physics_score": 100, "market_score": 10.4}
    apply_team_blind_spot(t2)
    assert t2["blind_spot_gap"] == 89.6
    assert t2["is_blind_spot"] is True


def test_blind_spot_min_gap_constant():
    assert BLIND_SPOT_MIN_GAP == 55.0
