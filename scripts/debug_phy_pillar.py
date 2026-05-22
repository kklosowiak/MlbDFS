"""One-off: show why team PHY pillars cluster at 99."""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.sharps_weighting import SharpsWeighting

sw = SharpsWeighting()

cases = [
    ("Arizona Diamondbacks", 0.405, 0.410, 1.0, 18.6, 92, 6.01),
    ("New York Yankees", 0.385, 0.395, 1.02, 33.1, 88, 4.69),
    ("Los Angeles Angels", 0.378, 0.388, 0.99, 25.5, 78, 4.72),
    ("Athletics", 0.365, 0.375, 1.0, 34.1, 75, 4.15),
    ("Toronto Blue Jays", 0.340, 0.350, 1.01, 25.6, 70, 3.12),
    ("Colorado Rockies", 0.355, 0.365, 1.15, 27.4, 65, 3.88),
]

print("team                  | xwOBA | conc  | phys_raw | vuln | pen  | PHY_col | MKT_col")
print("-" * 88)
for team, xw, conc, park, opp_p, bp_fat, itt in cases:
    r = sw.calculate_stack_score(
        team,
        ml_move=0,
        tt_move=0,
        curr_itt=itt,
        team_xwoba=xw,
        power_concentration=conc,
        park_factor=park,
        bullpen_fatigue=bp_fat,
        opp_pitcher_physics=opp_p,
        implied_total=itt,
    )
    print(
        f"{team:22}| {xw:.3f} | {conc:.3f} | {r['physics_raw']:8.1f} | "
        f"{r['vulnerability']:4.1f} | {r['bullpen_boost']:4.1f} | {r['physics_pillar']:7.1f} | {r['market_pillar']:7.1f}"
    )

print("\nSensitivity: same avg SP + pen, only xwOBA changes")
for xw in [0.330, 0.350, 0.370, 0.390, 0.410]:
    eff = xw * 0.4 + (xw + 0.01) * 0.6
    pr = min(100.0, max(0.0, (eff - 0.260) / 0.140 * 100))
    vuln = (100.0 - 25.0) / 5.0
    pen = 8.0
    pillar = min(99.0, pr + vuln * 0.65 + pen * 0.5)
    print(f"  xwOBA {xw:.3f} -> physics_raw {pr:5.1f} -> PHY pillar {pillar:5.1f}")
