"""
Unit tests for OMEGA signal exclusion logic.
Ensures that mutually exclusive GPP signals (Trap, Fade Risk) clear positive indicators.
OMEGA v19.3: is_sneaky removed from all test cases (field retired; no longer written to entities).
"""

from utils.team_signals import apply_signal_exclusions


def test_trap_excludes_positive_gpp_signals():
    # If a team is flagged as a public chalk trap, it must disable buy signals.
    team = {
        "team": "Test Stacks",
        "is_trap": True,
        "is_fade_risk": False,
        "is_physics_override": True,
        "is_anti_chalk_smash": True
    }

    cleaned = apply_signal_exclusions(team)
    assert cleaned["is_trap"] is True
    assert cleaned["is_physics_override"] is False
    assert cleaned["is_anti_chalk_smash"] is False


def test_fade_risk_excludes_positive_gpp():
    # If a team is flagged as a fade risk, it must deactivate buy indicators.
    team = {
        "team": "Test Stacks",
        "is_trap": False,
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
        "is_fade_risk": False,
        "is_physics_override": True,
        "is_anti_chalk_smash": True
    }

    cleaned = apply_signal_exclusions(team)
    assert cleaned["is_physics_override"] is True
    assert cleaned["is_anti_chalk_smash"] is True
