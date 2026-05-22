import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.xwoba_estimates import ops_to_xwoba, xwoba_to_phy_score, cap_matchup_xwoba, platoon_advantage_label


def test_ops_to_xwoba_realistic_range():
    assert ops_to_xwoba(0.650) < 0.340
    assert ops_to_xwoba(0.720) < 0.360
    assert ops_to_xwoba(0.950) <= 0.420
    assert ops_to_xwoba(0.950) >= 0.380
    assert ops_to_xwoba(1.050) == 0.420


def test_no_phantom_450s():
    assert cap_matchup_xwoba(0.48) == 0.420
    assert cap_matchup_xwoba(0.42 * 1.30) == 0.420


def test_phy_score_spread():
    weak = xwoba_to_phy_score(0.300)
    avg = xwoba_to_phy_score(0.340)
    elite = xwoba_to_phy_score(0.400)
    assert weak < avg < elite
    assert elite == 100.0
    assert weak < 25.0


def test_platoon_edge_tiers():
    assert platoon_advantage_label(0.375) == "ELITE PLATOON"
    assert platoon_advantage_label(0.350) == "STRONG EDGE"
    assert platoon_advantage_label(0.325) == "NEUTRAL"
    assert platoon_advantage_label(0.305) == "SLIGHT FADE"
    assert platoon_advantage_label(0.290) == "PLATOON TRAP"


if __name__ == "__main__":
    test_ops_to_xwoba_realistic_range()
    test_no_phantom_450s()
    test_phy_score_spread()
    test_platoon_edge_tiers()
    print("ok", ops_to_xwoba(0.71), ops_to_xwoba(0.85), ops_to_xwoba(0.95))
