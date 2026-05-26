"""Package A: stack chalk trap gate (Talent Floor Gate v2)."""
import unittest

from engine.sharps_weighting import SharpsWeighting


class TestStackChalkTrap(unittest.TestCase):
    def test_sharp_steam_exempt(self):
        self.assertFalse(
            SharpsWeighting._stack_chalk_trap(
                physics_raw=30.0,
                team_xwoba=0.283,
                physics_display=12.0,
                ml_move=-36,
                divergence=13,
                is_steam=True,
                is_shark=True,
                pre_trap_score=90.0,
            )
        )

    def test_elite_stack_exempt(self):
        self.assertFalse(
            SharpsWeighting._stack_chalk_trap(
                physics_raw=50.0,
                team_xwoba=0.320,
                physics_display=20.0,
                ml_move=15,
                divergence=20,
                is_steam=False,
                is_shark=False,
                pre_trap_score=118.0,
            )
        )

    def test_chalk_weak_offense_public_ml(self):
        self.assertTrue(
            SharpsWeighting._stack_chalk_trap(
                physics_raw=30.0,
                team_xwoba=0.283,
                physics_display=12.0,
                ml_move=14,
                divergence=5,
                is_steam=False,
                is_shark=False,
                pre_trap_score=85.0,
            )
        )

    def test_strong_offense_no_chalk(self):
        self.assertFalse(
            SharpsWeighting._stack_chalk_trap(
                physics_raw=60.0,
                team_xwoba=0.350,
                physics_display=28.0,
                ml_move=10,
                divergence=15,
                is_steam=False,
                is_shark=False,
                pre_trap_score=85.0,
            )
        )


if __name__ == "__main__":
    unittest.main()
