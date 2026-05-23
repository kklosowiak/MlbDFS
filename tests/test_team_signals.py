from utils.team_signals import (
    apply_team_blind_spot,
    apply_team_burst,
    evaluate_burst_signal,
    team_blind_spot_gap,
    BLIND_SPOT_MIN_GAP,
)


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
    assert BLIND_SPOT_MIN_GAP == 50.0


def test_burst_old_pen_only_path_no_longer_fires():
    # v8: gassed pen + short leash alone triggered BURST
    is_burst, _ = evaluate_burst_signal(0.340, 0.335, 90, 14.0, 70.0)
    assert is_burst is False


def test_burst_star_power_and_targetable_sp():
    is_burst, gap = evaluate_burst_signal(0.380, 0.350, 50, 18.0, 40.0)
    assert gap == 0.03
    assert is_burst is True


def test_burst_star_power_and_pen_script():
    is_burst, _ = evaluate_burst_signal(0.372, 0.348, 88, 14.5, 75.0)
    assert is_burst is True


def test_apply_team_burst_on_api_shape():
    t = {
        "power_concentration": 0.340,
        "team_xwoba": 0.335,
        "bullpen_fatigue": 90,
        "opp_pitcher_outs": 14.0,
        "opp_pitcher_physics": 70.0,
        "is_burst": True,
    }
    apply_team_burst(t)
    assert t["is_burst"] is False
