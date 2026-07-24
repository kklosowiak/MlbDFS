# OMEGA Pitcher Calibration Bust Log

Tracks recommended starting pitchers (`attack_conf >= 70`) who scored `actual_dk_pts <= 10.0` points.

| Date | Pitcher | Team | Conf | L3 ERA | L5 ERA | SIERA | L3 BB/9 | Result | Actual DK Pts |
|---|---|---|---|---|---|---|---|---|---|
| 2026-07-08 | Davis Martin | Chicago White Sox | 80% | 1.84 | N/A | 3.1769562955254944 | N/A | 4.0 IP / 5 ER / 2 K / 2 BB | -1.8 |
| 2026-07-07 | Trevor Mcdonald | San Francisco Giants | 76% | 3.77 | N/A | 3.7179473684210524 | N/A | 2.1 IP / 8 ER / 0 K / 1 BB | -17.9 |

## Statistical Validation Study

Conducted multiple linear regression on starting pitcher starts ($N = 167$) to validate rolling form and control indicators.

**Regression Model:** `actual_dk_pts ~ intercept + recent_era_5g + siera_div + recent_bb9`

- **R-squared:** 0.0490
- **Adjusted R-squared:** 0.0315

| Variable | Coefficient | Std Error | t-statistic | p-value | Significant (95%) |
|---|---|---|---|---|---|
| `Intercept` | 18.6622 | 2.9310 | 6.3672 | 1.8774e-09 | Yes |
| `recent_era_5g` | -1.3059 | 0.6079 | -2.1483 | 3.3171e-02 | Yes |
| `siera_div` | 0.0378 | 0.5271 | 0.0717 | 9.4293e-01 | No |
| `recent_bb9` | 0.2178 | 0.6318 | 0.3447 | 7.3076e-01 | No |




| 2026-07-18 | Max Meyer | Miami Marlins | 75% | 3.21 | 2.42 | 3.1711081081081085 | N/A | 3.0 IP / 2 ER / 5 K / 3 BB | 9.2 |
| 2026-07-22 | Sandy Alcantara | Miami Marlins | 79% | 2.14 | 2.97 | 3.7640146842878126 | N/A | 7.0 IP / 5 ER / 3 K / 1 BB | 5.8 |
| 2026-07-23 | Michael Mcgreevy | St. Louis Cardinals | 71% | 2.84 | 2.32 | 3.7349114811568795 | N/A | 6.1 IP / 4 ER / 3 K / 3 BB | 6.2 |
