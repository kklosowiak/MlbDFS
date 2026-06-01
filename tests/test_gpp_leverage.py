"""
Unit tests for refined GPP Leverage Index labeling logic.
Verifies selective pivot caps, confidence floors, and corrected chalk logic.
"""

from __future__ import annotations
from utils.gpp_leverage import compute_gpp_leverage

def test_selective_pivots_on_small_slate():
    # 6-team slate: max(1, round(6 * 0.20)) = 1 pivot
    teams = [
        {"team": f"Team {i}", "implied_total": 4.5, "team_xwoba": 0.320}
        for i in range(6)
    ]
    # Set one team to have higher confidence via a mock override and conviction signals
    teams[0]["is_physics_override"] = True  # Boosts confidence -> higher GLI
    teams[0]["dqi_status"] = "TRUST"
    teams[0]["is_anti_chalk_smash"] = True
    
    compute_gpp_leverage(teams, [])
    
    pivots = [t for t in teams if t.get("leverage_label") == "LEVERAGE PIVOT"]
    assert len(pivots) == 1
    assert pivots[0]["team"] == "Team 0"
    
    # Other candidates must be neutral because of the slate size cap
    neutrals = [t for t in teams if t.get("leverage_label") == "NEUTRAL"]
    assert len(neutrals) == 5

def test_pivot_requires_minimum_confidence():
    # Team has low ownership (high GLI candidate) but confidence < 50
    # Team 0: ITT 3.0 (low total) -> low confidence (~30) but low ownership
    teams = [
        {"team": "Team A", "implied_total": 3.0, "team_xwoba": 0.270},
        {"team": "Team B", "implied_total": 5.0, "team_xwoba": 0.340},
    ]
    
    compute_gpp_leverage(teams, [])
    
    # Team A should not be a pivot because conf < 50
    team_a = next(t for t in teams if t["team"] == "Team A")
    assert team_a["gpp_leverage_index"] >= 1.5
    assert team_a["leverage_label"] == "NEUTRAL"

def test_pivot_excludes_high_ownership():
    # Team has high confidence but is highly owned
    teams = [
        {"team": "Chalk Team", "implied_total": 6.5, "team_xwoba": 0.360, "is_sharp": True},
        {"team": "Neutral Team", "implied_total": 4.5, "team_xwoba": 0.320},
    ]
    
    compute_gpp_leverage(teams, [])
    
    chalk_team = next(t for t in teams if t["team"] == "Chalk Team")
    # Chalk team should not be pivot even if GLI/confidence is high because ownership is too high
    assert chalk_team["leverage_label"] != "LEVERAGE PIVOT"

def test_crowded_chalk_corrected_for_unpopular_teams():
    # Team A: Very low confidence, but also very low ownership
    # Team B: Very low confidence, but high ownership (chalk)
    teams = [
        {"team": "Unpopular Team", "implied_total": 3.0, "team_xwoba": 0.250},
        {"team": "Chalky Bad Team", "implied_total": 5.5, "team_xwoba": 0.250, "is_trap": True},
        {"team": "Normal Team", "implied_total": 4.8, "team_xwoba": 0.320},
    ]
    
    compute_gpp_leverage(teams, [])
    
    unpopular = next(t for t in teams if t["team"] == "Unpopular Team")
    chalky_bad = next(t for t in teams if t["team"] == "Chalky Bad Team")
    
    # Unpopular team has low confidence, so low GLI, but it's under-owned, so it's NEUTRAL (not CROWDED CHALK)
    assert unpopular["leverage_label"] == "NEUTRAL"
    
    # Chalky bad team has low confidence and is over-owned (above avg), so it's OVEROWNED
    assert chalky_bad["leverage_label"] == "OVEROWNED"
