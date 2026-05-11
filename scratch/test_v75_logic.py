from engine.sharps_weighting import SharpsWeighting

sw = SharpsWeighting()

# 1. Test Pitcher Volume Penalty (Burch Smith Case)
# Tonight's Smith: 100.0 OMEGA, 14.5 outs
score_full = sw.calculate_pitcher_score("Burch Smith", -11.0, -0.5, 5, 4.5, siera=3.80, csw=0.28, projected_outs=18.0)
score_limited = sw.calculate_pitcher_score("Burch Smith", -11.0, -0.5, 5, 4.5, siera=3.80, csw=0.28, projected_outs=14.5)

print(f"Pitcher Volume Test (Burch Smith):")
print(f"  Full Volume (18 outs): {score_full['final']}")
print(f"  Limited Volume (14.5 outs): {score_limited['final']}")
print(f"  Suppression Ratio: {score_limited['final']/score_full['final']:.2f}")

# 2. Test Hitter Chalk Suppression (Aaron Judge Case)
# Judge was -309. Before: no cap. After: 40pt cap.
judge_score_no_cap = sw.calculate_individual_hitter_score("Aaron Judge", 81.9, 0.412, -250)
judge_score_capped = sw.calculate_individual_hitter_score("Aaron Judge", 81.9, 0.412, -310)

print(f"\nHitter Chalk Test (Aaron Judge):")
print(f"  Price -250 (No Cap): {judge_score_no_cap['final']}")
print(f"  Price -310 (Capped): {judge_score_capped['final']}")
