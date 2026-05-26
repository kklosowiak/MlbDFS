"""Smoke tests for DQI and market utils."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.dqi import calculate_dqi
from utils.market_utils import calculate_ml_move


def test_dqi_gated_below_6():
    score, status, pos, warn = calculate_dqi({"divergence": 5.9})
    assert score is None
    assert status is None


def test_dqi_fires_with_divergence():
    team = {
        "divergence": 15,
        "opp_pitcher_physics": 18,
        "bullpen_fatigue": 80,
        "tt_move": 0.4,
        "ml_move": -12,
        "team_xwoba": 0.340,
        "power_concentration": 0.360,
        "implied_total": 5.0,
        "trend": "SURGING",
        "is_storm": True,
    }
    score, status, pos, warn = calculate_dqi(team)
    assert score is not None
    assert score >= 50
    assert status in ("TRUST", "CAUTION", "FADE")
    assert len(pos) > 0


def test_dqi_trap_from_pitcher():
    team = {
        "divergence": 12,
        "opp_pitcher": "Test Pitcher",
        "is_trap": False,
    }
    pitchers = [{"pitcher": "Test Pitcher", "is_trap": True}]
    score, status, pos, warn = calculate_dqi(team, pitchers=pitchers)
    assert any("Opposing SP Trap" in p for p in pos)
    assert not any("Opposing SP Trap" in w for w in warn)


def test_ml_move():
    assert calculate_ml_move(-110, -125) == -15
