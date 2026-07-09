# OMEGA Pitcher Calibration Bust Log

Tracks recommended starting pitchers (`attack_conf >= 70`) who scored `actual_dk_pts <= 10.0` points.

| Date | Pitcher | Team | Conf | L3 ERA | L5 ERA | SIERA | L3 BB/9 | Result | Actual DK Pts |
|---|---|---|---|---|---|---|---|---|---|
| 2026-07-08 | Davis Martin | Chicago White Sox | 80% | 1.84 | N/A | 3.1769562955254944 | N/A | 4.0 IP / 5 ER / 2 K / 2 BB | -1.8 |
| 2026-07-07 | Trevor Mcdonald | San Francisco Giants | 76% | 3.77 | N/A | 3.7179473684210524 | N/A | 2.1 IP / 8 ER / 0 K / 1 BB | -17.9 |

## Statistical Validation Study

Conducted multiple linear regression on starting pitcher starts ($N = 153$) to validate rolling form and control indicators.

**Regression Model:** `actual_dk_pts ~ intercept + recent_era_5g + siera_div + recent_bb9`

- **R-squared:** 0.0501
- **Adjusted R-squared:** 0.0309

| Variable | Coefficient | Std Error | t-statistic | p-value | Significant (95%) |
|---|---|---|---|---|---|
| `Intercept` | 17.5744 | 3.0576 | 5.7478 | 4.9366e-08 | Yes |
| `recent_era_5g` | -0.9553 | 0.6313 | -1.5133 | 1.3233e-01 | No |
| `siera_div` | -0.3514 | 0.5632 | -0.6239 | 5.3366e-01 | No |
| `recent_bb9` | 0.0933 | 0.6583 | 0.1417 | 8.8753e-01 | No |


## Statistical Validation Study

Conducted multiple linear regression on starting pitcher starts ($N = 140$) to validate rolling form and control indicators.

**Regression Model:** `actual_dk_pts ~ intercept + recent_era_5g + siera_div + recent_bb9`

- **R-squared:** 0.0443
- **Adjusted R-squared:** 0.0232

| Variable | Coefficient | Std Error | t-statistic | p-value | Significant (95%) |
|---|---|---|---|---|---|
| `Intercept` | 17.3104 | 3.2342 | 5.3522 | 3.5927e-07 | Yes |
| `recent_era_5g` | -1.2995 | 0.6575 | -1.9763 | 5.0142e-02 | No |
| `siera_div` | 0.0742 | 0.5838 | 0.1271 | 8.9906e-01 | No |
| `recent_bb9` | 0.7179 | 0.7187 | 0.9990 | 3.1959e-01 | No |

