"""
Unit tests for future OMEGA signal exclusion logic.
Ensures that mutually exclusive GPP signals (Sneaky vs Trap, Fade Risk vs Positive GPP)
are cleaned up correctly to avoid contradictory coaching tips.
"""

from utils.team_signals import apply_signal_exclusions


def test_trap_excludes_sneaky():
    # If a team is flagged as sneaky, but also as a public chalk trap, trap must win and disable sneaky.
    team = {
        "team": "Test Stacks",
        "is_trap": True,
        "is_sneaky": True,
        "is_fade_risk": False,
        "is_physics_override": False,
        "is_anti_chalk_smash": False
    }
    
    cleaned = apply_signal_exclusions(team)
    assert cleaned["is_trap"] is True
    assert cleaned["is_sneaky"] is False


def test_fade_risk_excludes_positive_gpp():
    # If a team is flagged as a fade risk, it must deactivate buy indicators.
    team = {
        "team": "Test Stacks",
        "is_trap": False,
        "is_sneaky": False,
        "is_fade_risk": True,
        "is_physics_override": True,
        "is_anti_chalk_smash": True
    }
    
    cleaned = apply_signal_exclusions(team)
    assert cleaned["is_fade_risk"] is True
    assert cleaned["is_physics_override"] is False
    assert cleaned["is_anti_chalk_smash"] is False


def test_normal_signals_preserved():
    # Verify that if no conflicts exist, the flags are left untouched.
    team = {
        "team": "Test Stacks",
        "is_trap": False,
        "is_sneaky": True,
        "is_fade_risk": False,
        "is_physics_override": True,
        "is_anti_chalk_smash": True
    }
    
    cleaned = apply_signal_exclusions(team)
    assert cleaned["is_sneaky"] is True
    assert cleaned["is_physics_override"] is True
    assert cleaned["is_anti_chalk_smash"] is True
