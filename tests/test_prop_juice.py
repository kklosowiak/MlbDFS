from utils.prop_juice import (
    american_juice_gap,
    evaluate_hitter_prop_juice,
    evaluate_pitcher_k_juice,
    scan_prop_pairs,
    apply_hitter_target_caps,
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


def test_apply_hitter_target_caps_respects_caps():
    # Enforce team and slate caps
    hitters = [
        {"name": "Hitter 1", "team": "Team A", "is_juiced_target": True, "_juice_gap": 30, "matchup_xwoba": 0.380},
        {"name": "Hitter 2", "team": "Team A", "is_juiced_target": True, "_juice_gap": 28, "matchup_xwoba": 0.370},
        {"name": "Hitter 3", "team": "Team A", "is_juiced_target": True, "_juice_gap": 26, "matchup_xwoba": 0.360},
        {"name": "Hitter 4", "team": "Team A", "is_juiced_target": True, "_juice_gap": 24, "matchup_xwoba": 0.355}, # Should get capped by team cap (max 3)
        {"name": "Hitter 5", "team": "Team B", "is_juiced_target": True, "_juice_gap": 40, "matchup_xwoba": 0.390},
        {"name": "Hitter 6", "team": "Team B", "is_juiced_target": True, "_juice_gap": 35, "matchup_xwoba": 0.385},
    ]

    capped = apply_hitter_target_caps(hitters, max_targets=4, max_per_team=3)
    
    # Team A should only have at most 3 targets (Hitter 4 should definitely be False)
    team_a_targets = [h for h in capped if h["team"] == "Team A" and h["is_juiced_target"]]
    assert len(team_a_targets) <= 3
    assert not any(h["name"] == "Hitter 4" for h in team_a_targets)

    # Slate-wide total targets should be at most 4
    total_targets = [h for h in capped if h["is_juiced_target"]]
    assert len(total_targets) <= 4

