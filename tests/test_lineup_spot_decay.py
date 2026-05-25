import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_lineup_spot_decay_math():
    # Batting order weights
    BATTING_ORDER_WEIGHTS = [1.22, 1.16, 1.10, 1.04, 0.98, 0.92, 0.86, 0.80, 0.72]
    sum_weights = sum(BATTING_ORDER_WEIGHTS)
    assert abs(sum_weights - 8.80) < 1e-5

    # Case A: Top-heavy lineup (elite hitters 1-4 bat at the top)
    # 4 elite hitters (0.380) at the top, 5 weaker hitters (0.280) at the bottom
    top_heavy_xwobas = [0.380, 0.380, 0.380, 0.380, 0.280, 0.280, 0.280, 0.280, 0.280]
    
    # Simple average
    simple_avg_top_heavy = sum(top_heavy_xwobas) / len(top_heavy_xwobas) # ~0.3244
    
    # Batting-order weighted average
    weighted_sum_top_heavy = sum(xw * w for xw, w in zip(top_heavy_xwobas, BATTING_ORDER_WEIGHTS))
    weighted_avg_top_heavy = weighted_sum_top_heavy / sum_weights # ~0.3314
    
    # The top-heavy lineup true offense is elevated because the elite hitters capture more plate appearances
    assert weighted_avg_top_heavy > simple_avg_top_heavy
    assert abs(weighted_avg_top_heavy - 0.33136) < 1e-4

    # Case B: Bottom-heavy lineup (elite hitters placed at the bottom, weak hitters at the top)
    # 4 weaker hitters (0.280) at the top, 5 elite hitters (0.380) at the bottom
    bottom_heavy_xwobas = [0.280, 0.280, 0.280, 0.280, 0.380, 0.380, 0.380, 0.380, 0.380]
    
    # Simple average
    simple_avg_bottom_heavy = sum(bottom_heavy_xwobas) / len(bottom_heavy_xwobas) # ~0.3356
    
    # Batting-order weighted average
    weighted_sum_bottom_heavy = sum(xw * w for xw, w in zip(bottom_heavy_xwobas, BATTING_ORDER_WEIGHTS))
    weighted_avg_bottom_heavy = weighted_sum_bottom_heavy / sum_weights # ~0.3286
    
    # The bottom-heavy lineup true offense is depressed because the elite hitters get fewer plate appearances
    assert weighted_avg_bottom_heavy < simple_avg_bottom_heavy
    assert abs(weighted_avg_bottom_heavy - 0.32863) < 1e-4

if __name__ == "__main__":
    test_lineup_spot_decay_math()
    print("Lineup spot decay tests: OK")
