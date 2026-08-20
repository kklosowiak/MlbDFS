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
| 2026-08-05 | Sean Burke | Chicago White Sox | 74% | 1.42 | 1.03 | 3.133 | N/A | 4.1 IP / 2 ER / 4 K / 2 BB | 9.6 |
| 2026-08-06 | Michael Wacha | Kansas City Royals | 79% | 1.93 | 3.38 | 3.7136666666666667 | 2.45 | 5.2 IP / 1 ER / 1 K / 3 BB | 9.2 |
| 2026-08-07 | Robbie Ray | San Diego Padres | 75% | 1.12 | 2.0 | 3.8949312602291326 | N/A | 5.0 IP / 4 ER / 2 K / 5 BB | 0.1 |
| 2026-08-08 | Chase Burns | Cincinnati Reds | 72% | 1.12 | 2.33 | 3.041522842639594 | N/A | 5.1 IP / 5 ER / 6 K / 3 BB | 8.6 |
| 2026-08-08 | Peter Lambert | Houston Astros | 73% | 3.24 | 2.51 | 3.402053604436229 | N/A | 5.0 IP / 2 ER / 3 K / 3 BB | 8.4 |
| 2026-08-08 | Robert Gasser | Milwaukee Brewers | 89% | 2.25 | 4.39 | 4.224864734299517 | N/A | 4.2 IP / 3 ER / 3 K / 2 BB | 3.9 |
| 2026-08-10 | Trevor Rogers | Baltimore Orioles | 71% | 3.79 | 2.87 | 3.7656319444444444 | 3.63 | 4.0 IP / 2 ER / 4 K / 2 BB | 8.2 |
| 2026-08-11 | Hunter Brown | Houston Astros | 84% | 2.41 | 3.68 | 3.9020549828178694 | N/A | 5.0 IP / 3 ER / 4 K / 3 BB | 8.4 |
| 2026-08-11 | Tanner Bibee | Cleveland Guardians | 75% | 3.21 | 3.46 | 4.076556434219986 | N/A | 6.1 IP / 5 ER / 4 K / 2 BB | 7.5 |
| 2026-08-13 | Roki Sasaki | Los Angeles Dodgers | 87% | 2.45 | 2.4 | 4.566904761904762 | N/A | 6.0 IP / 2 ER / 2 K / 5 BB | 8.1 |
| 2026-08-14 | Tbd | Athletics | 71% | 0.0 | N/A | 4.1 | N/A | 5.1 IP / 3 ER / 1 K / 4 BB | 3.8 |
| 2026-08-17 | Shane Mcclanahan | Tampa Bay Rays | 84% | 2.45 | 3.22 | 3.2807450980392154 | N/A | 3.1 IP / 3 ER / 3 K / 0 BB | 5.1 |
| 2026-08-17 | Michael Wacha | Kansas City Royals | 80% | 2.45 | 2.3 | 3.7124540612516648 | 2.45 | 5.0 IP / 4 ER / 3 K / 0 BB | 9.7 |
| 2026-08-17 | Andre Pallante | St. Louis Cardinals | 84% | 1.53 | 1.8 | 3.598846153846154 | 2.08 | 6.0 IP / 4 ER / 5 K / 1 BB | 8.9 |
| 2026-08-17 | Brandon Young | Baltimore Orioles | 71% | 2.84 | 3.28 | 3.744172413793103 | N/A | 4.0 IP / 4 ER / 3 K / 1 BB | 1.6 |
| 2026-08-17 | Mitch Bratt | Arizona Diamondbacks | 77% | 1.5 | 3.25 | 4.62133734939759 | N/A | 3.0 IP / 3 ER / 0 K / 3 BB | -3.5 |
| 2026-08-18 | Keider Montero | Detroit Tigers | 71% | 2.45 | 3.21 | 3.462613104524181 | N/A | 5.0 IP / 3 ER / 3 K / 1 BB | 8.2 |
| 2026-08-18 | Nick Martinez | Tampa Bay Rays | 90% | 2.35 | 3.29 | 3.439973950795948 | N/A | 3.2 IP / 6 ER / 5 K / 2 BB | -0.3 |
| 2026-08-19 | Drew Rasmussen | Tampa Bay Rays | 86% | 1.42 | 0.7 | 2.7837425057647964 | 1.35 | 5.0 IP / 5 ER / 5 K / 2 BB | 9.8 |
| 2026-08-19 | Dustin May | Milwaukee Brewers | 73% | 1.5 | 2.79 | 3.576295081967213 | N/A | 2.0 IP / 7 ER / 1 K / 2 BB | -13.5 |
