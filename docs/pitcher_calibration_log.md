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
| 2026-07-24 | Bryce Miller | Seattle Mariners | 73% | 3.06 | 3.18 | 2.823619651347068 | 2.04 | 5.1 IP / 5 ER / 0 K / 1 BB | -2.2 |
| 2026-07-25 | Eury Pérez | Miami Marlins | 79% | 2.37 | 1.72 | 3.670507128309572 | N/A | 7.0 IP / 3 ER / 2 K / 1 BB | 8.3 |
| 2026-07-27 | Keider Montero | Detroit Tigers | 91% | 1.23 | 1.61 | 3.3578899167437557 | N/A | 4.1 IP / 4 ER / 1 K / 1 BB | -2.9 |
| 2026-07-29 | Casey Legumina | Tampa Bay Rays | 80% | 0.0 | N/A | 3.811222222222222 | N/A | 1.2 IP / 0 ER / 0 K / 0 BB | 3.1 |
| 2026-07-31 | Foster Griffin | Washington Nationals | 85% | 2.18 | 1.65 | 3.339548387096774 | N/A | 5.1 IP / 6 ER / 3 K / 2 BB | -0.6 |
| 2026-07-31 | Nick Martinez | Tampa Bay Rays | 73% | 1.38 | 1.9 | 3.3266960203217613 | N/A | 6.0 IP / 6 ER / 2 K / 0 BB | 1.3 |
| 2026-08-02 | Taj Bradley | Minnesota Twins | 73% | 2.84 | 3.77 | 3.8142725832012676 | N/A | 6.0 IP / 3 ER / 2 K / 4 BB | 4.9 |
| 2026-08-03 | Justin Wrobleski | Los Angeles Dodgers | 84% | 3.26 | 3.24 | 3.2515347593582886 | N/A | 4.1 IP / 7 ER / 4 K / 3 BB | -2.2 |
| 2026-08-04 | Jared Jones | Pittsburgh Pirates | 71% | 2.65 | 2.0 | 3.5223076923076926 | N/A | 4.0 IP / 3 ER / 4 K / 1 BB | 5.6 |
