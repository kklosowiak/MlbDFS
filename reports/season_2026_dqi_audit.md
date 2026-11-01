# OMEGA 2026 DQI Audit (recomputed at lock with production `calculate_dqi`)

Teams: 1446 team-games on 84 regular-season dates. Mean runs 4.46, mean ITT 4.32, hit-ITT baseline 45.9%.

Recompute vs stored `stack_trust_score` (gated rows, n=153): Pearson 0.260, exact-int match 0.0%. (Statuses below use CURRENT scoring code applied to the lock-time inputs; the live status shown on the day may differ if the code changed.)


## Status vs the rest of the league

Each row = flagged teams minus all other team-games (incl. gated-out). Positive runs-ITT means beat Vegas. 95% date-clustered bootstrap CIs.

| status | n | days | mean_runs | hit_ITT% | runs_ITT | hit_ITT_diff | p5_diff | p7_diff |
|---|---|---|---|---|---|---|---|---|
| OVERPRICED | 18 | 13 | 5.78 | 61.1 | +0.84 [-0.78, +2.77] | +15.38 [-1.63, +33.41] | +18.18 [+1.25, +35.35] | +11.27 [-8.14, +34.85] |
| CAUTION | 108 | 55 | 4.12 | 45.4 | -0.30 [-0.84, +0.22] | -0.59 [-9.83, +8.80] | -2.61 [-11.89, +7.27] | -4.98 [-13.12, +2.90] |
| LEVERAGE | 38 | 26 | 3.66 | 34.2 | -0.34 [-1.18, +0.56] | -12.03 [-25.75, +1.48] | -11.89 [-24.27, +1.62] | -3.88 [-15.40, +8.70] |
| GATED_OUT | 1282 | 84 | 4.49 | 46.1 | +0.19 [-0.21, +0.61] | +1.59 [-5.24, +8.64] | +2.59 [-5.40, +10.18] | +3.03 [-2.89, +8.99] |


## Continuous DQI score (gated teams only)

| dqi_score | n | mean_ITT | mean_runs | runs_minus_ITT | hit_ITT% | p7% |
|---|---|---|---|---|---|---|
| 0-30 | 2.0 | 3.90 | 1.00 | -2.90 | 0.0 | 0.0 |
| 31-49 | 36.0 | 3.85 | 3.81 | -0.05 | 36.1 | 19.4 |
| 50-64 | 50.0 | 4.09 | 4.02 | -0.07 | 52.0 | 12.0 |
| 65-81 | 50.0 | 4.32 | 4.10 | -0.22 | 38.0 | 20.0 |
| 82+ | 26.0 | 4.86 | 5.50 | +0.64 | 57.7 | 34.6 |


Pooled Spearman (gated teams, n=164): DQI vs runs-ITT +0.031; DQI vs actual runs +0.153. Note DQI includes implied total as an input, so its relation to raw runs is partly Vegas.


## Does DQI add anything on top of implied total? (gated teams, OLS: runs ~ ITT + DQI)

runs = -0.87 + 0.963*ITT + 0.0157*DQI  (SE ITT 0.544, SE DQI 0.0182; t(DQI)=0.86). Naive SEs, rows within a day are correlated, so treat as indicative.
