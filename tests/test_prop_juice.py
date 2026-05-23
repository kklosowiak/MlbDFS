from utils.prop_juice import (
    american_juice_gap,
    evaluate_hitter_prop_juice,
    evaluate_pitcher_k_juice,
    scan_prop_pairs,
)


def test_american_juice_gap_over_favored():
    assert american_juice_gap(-130, -110) >= 20


def test_pitcher_strict_target_requires_physics_and_k():
    rows = [
        {"player_name": "Test Pitcher", "side": "Over", "bookmaker": "dk", "point": 5.5, "price": -140},
        {"player_name": "Test Pitcher", "side": "Under", "bookmaker": "dk", "point": 5.5, "price": -110},
    ]
    tgt, juice, gap = evaluate_pitcher_k_juice(rows, "Test Pitcher", k_line=5.5, physics_talent=60)
    assert juice is True
    assert tgt is True
    assert gap >= 20

    tgt2, juice2, _ = evaluate_pitcher_k_juice(rows, "Test Pitcher", k_line=4.5, physics_talent=60)
    assert juice2 is True
    assert tgt2 is False


def test_hitter_target_needs_xwoba():
    tgt, juice, gap = evaluate_hitter_prop_juice(-150, -110, matchup_xwoba=0.355)
    assert juice and tgt and gap >= 15
    tgt2, juice2, _ = evaluate_hitter_prop_juice(-150, -110, matchup_xwoba=0.310)
    assert juice2
    assert tgt2 is False
