from utils.matchup_physics import pitcher_physics_0_100
from utils.platoon_math import compute_platoon_multiplier


def test_pitcher_physics_scales_display_slice():
    assert pitcher_physics_0_100(physics_score=45.0) == 100.0
    assert pitcher_physics_0_100(physics_score=22.5) == 50.0


def test_trap_caps_matchup_physics():
    rep = {"physics_score": 45.0, "is_trap": True}
    assert pitcher_physics_0_100(rep) == 65.0


def test_platoon_multiplier_neutral_without_splits():
    assert compute_platoon_multiplier({}, "R") == 1.0
