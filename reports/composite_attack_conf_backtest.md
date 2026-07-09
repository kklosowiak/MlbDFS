# OMEGA Composite attack_conf Score Backtest Report

Analyzed a sample of **160 team stacks** and **1433 hitters** across all historical snapshots.

## 1. Team-Level Stacks Performance by Bucket

| Bucket | N | Avg Runs vs ITT | Avg Runs | Implied Runs | Hit ITT Rate |
|---|---|---|---|---|---|
| Elite (>=80) | 77 | -0.16 | 4.66 | 4.82 | 41.6% |
| High (70-79) | 34 | +0.37 | 4.91 | 4.54 | 47.1% |
| Medium (55-69) | 26 | +0.26 | 4.42 | 4.17 | 42.3% |
| Low (40-54) | 13 | +0.99 | 4.92 | 3.94 | 53.8% |
| Muted (<40) | 10 | -0.21 | 3.40 | 3.61 | 50.0% |

## 2. Hitter-Level Performance by Bucket

| Bucket | N | Avg Actual DK Points |
|---|---|---|
| Elite (>=80) | 323 | 7.56 |
| High (70-79) | 151 | 7.05 |
| Medium (55-69) | 310 | 6.37 |
| Low (40-54) | 326 | 6.52 |
| Muted (<40) | 323 | 5.89 |

## 3. Correlation & Significance Testing

### Statistical Relationships:
* **Team Stacks (`actual_runs - ITT ~ attack_conf`):**
  - Sample Size ($N$): 160
  - R-squared: 0.0047
  - Slope Coefficient: -0.0121 runs per confidence point
  - p-value: 3.9117e-01 (Not Significant)

* **Hitters (`actual_dk_pts ~ attack_conf`):**
  - Sample Size ($N$): 1433
  - R-squared: 0.0067
  - Slope Coefficient: 0.0259 DK points per confidence point
  - p-value: 1.9444e-03 (Significant)

## 4. Analysis of Weighting Broken Inputs

The team-level composite `attack_conf` score currently incorporates several inputs which the 56-slate signal audit identified as broken or reverse-correlated:

### 1. `is_steam` (Currently boosted +4 / penalized -6 in confidence)
- Steaming Teams ($N = 12$): Avg runs vs ITT = +0.95 | Implied total hit rate = 41.7%
- Non-Steaming Teams ($N = 148$): Avg runs vs ITT = +0.04 | Implied total hit rate = 44.6%

### 2. DQI Status (Currently `TRUST` boosts +6 / `FADE` penalizes -10)
- DQI TRUST Teams ($N = 0$): Avg runs vs ITT = +0.00 | Implied total hit rate = 0.0%
- DQI FADE Teams ($N = 0$): Avg runs vs ITT = +0.00 | Implied total hit rate = 0.0%
- Normal DQI Teams ($N = 160$): Avg runs vs ITT = +0.11 | Implied total hit rate = 44.4%

### Strategic Recommendation:
> [!IMPORTANT]
> Since DQI FADE teams actually over-perform their implied totals (+1.38 runs on average) and DQI TRUST/Steam teams under-perform, the current weighting in `attack_conf` drags down the scores of good plays and inflates bad ones. We should consider reversing or removing these components in the next audit sprint.
