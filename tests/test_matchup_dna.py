import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.platoon_math import compute_platoon_multiplier

class MockMatchupRadar:
    def __init__(self):
        self.data = {
            "pitchers": {
                "test pitcher": {
                    "FF": 60.0,
                    "SL": 40.0
                }
            },
            "hitters": {
                "test hitter": {
                    "FF": 0.400,
                    "SL": 0.300
                },
                "hitter missing pitch data": {
                    "FF": None
                }
            },
            "league_avg": {
                "FF": 0.335,
                "SL": 0.290
            }
        }

def test_matchup_dna_fallback_no_radar():
    # Should fall back to 1.0 (or standard splits if profile provided)
    mult = compute_platoon_multiplier({}, "R")
    assert mult == 1.0

def test_matchup_dna_calculation():
    radar = MockMatchupRadar()
    # Test Pitcher throws: 60% FF, 40% SL
    # Hitter has: 0.400 vs FF, 0.300 vs SL
    # Hitter expected xwOBA: 0.6 * 0.400 + 0.4 * 0.300 = 0.360
    # League expected xwOBA: 0.6 * 0.335 + 0.4 * 0.290 = 0.317
    # Expected multiplier: 0.360 / 0.317 = 1.135646687697
    
    mult = compute_platoon_multiplier(
        hitter_profile={"ops": 0.720},
        pitch_hand="R",
        hitter_name="Test Hitter",
        pitcher_name="Test Pitcher",
        matchup_radar=radar
    )
    
    expected_mult = 0.360 / 0.317
    assert abs(mult - expected_mult) < 1e-4

def test_matchup_dna_missing_hitter_fallback():
    radar = MockMatchupRadar()
    # Hitter not in radar, should fall back to hand-splits (which defaults to 1.0 for empty profiles)
    mult = compute_platoon_multiplier(
        hitter_profile={},
        pitch_hand="R",
        hitter_name="Nonexistent Hitter",
        pitcher_name="Test Pitcher",
        matchup_radar=radar
    )
    assert mult == 1.0

def test_matchup_dna_missing_pitch_fallback():
    radar = MockMatchupRadar()
    # Hitter missing some pitch data, should fall back to league average for that pitch type
    # Hitter: FF = None, SL = None. So it uses league average for all.
    # Expected multiplier: 1.0
    mult = compute_platoon_multiplier(
        hitter_profile={},
        pitch_hand="R",
        hitter_name="Hitter Missing Pitch Data",
        pitcher_name="Test Pitcher",
        matchup_radar=radar
    )
    assert abs(mult - 1.0) < 1e-4

if __name__ == "__main__":
    test_matchup_dna_fallback_no_radar()
    test_matchup_dna_calculation()
    test_matchup_dna_missing_hitter_fallback()
    test_matchup_dna_missing_pitch_fallback()
    print("Matchup DNA tests: OK")
