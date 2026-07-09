# OMEGA Stack Trust Score Backtest Report

This report presents the backtest results of the new `stack_trust_score` composite, designed to replace team-level stack ranking in OMEGA.

### Study Details:
- **Sample Size ($N$):** 160 team stacks (June 27 to July 8, 2026)
- **Dependent Variable:** `actual_runs - Implied Run Total (ITT)`

## 1. Multiple Linear Regression of Component Elements

We ran OLS multiple linear regression on the proposed components to evaluate their predictive significance:

| Component Variable | Coefficient | Std Error | t-stat | p-value | Significance |
|---|---|---|---|---|---|
| **Intercept** | 0.0199 | 0.4059 | 0.0489 | 9.6102e-01 | Not Significant |
| **opp_sp_any_flag** | -0.1002 | 0.5492 | -0.1825 | 8.5541e-01 | Not Significant |
| **is_fade_risk** | -0.4696 | 3.4282 | -0.1370 | 8.9122e-01 | Not Significant |
| **anti_chalk_pct** | 0.0064 | 0.0073 | 0.8793 | 3.8058e-01 | Not Significant |
| **is_pitch_alignment** | 0.1247 | 0.5970 | 0.2089 | 8.3483e-01 | Not Significant |

### Analysis of Components:
1. **`opp_sp_any_flag`** (Opposing SP has any of `trap_short_leash`, `trap_vulnerable`, `low_ceiling`, `hazard`, `paradox`): Coef is directionally negative (`-0.1002` runs), but not statistically significant ($p = 0.8554$).
2. **`is_fade_risk`**: Coef is heavily negative (`-0.4696` runs), which matches its 72.2% directional rate, but it is not significant ($p = 0.8912$) due to extremely low positive event count in this sample.
3. **`anti_chalk_pct`**: Coef is positive (`+0.0064` runs per percent of anti-chalk hitters), representing a +0.32 runs boost for a stack with 50% anti-chalk hitters. Not significant ($p = 0.3806$).
4. **`is_pitch_alignment`**: Coef is directionally positive (`+0.1247` runs), but not significant ($p = 0.8348$).

> [!IMPORTANT]
> None of the individual components are statistically significant on their own in this 160-stack sample. This indicates that run outcomes vs ITT have extremely high variance, and short-term trends are highly noisy. They should be treated as directionally-supported adjustment signals rather than standalone predictive variables.

## 2. Side-by-Side Model Comparison: `stack_trust_score` vs `attack_conf`

We evaluated the predictive power of the new composite `stack_trust_score` against the old team-level `attack_conf` score:

| Model Score | R-squared ($R^2$) | Coefficient | p-value | Significance |
|---|---|---|---|---|
| **`stack_trust_score`** (New) | 0.005330 | 0.0177 | 3.5890e-01 | Not Significant ($p > 0.05$) |
| **`attack_conf`** (Old) | 0.004658 | -0.0121 | 3.9117e-01 | Not Significant ($p > 0.05$) |

### Comparison Analysis:
- **Old `attack_conf` Performance:** Yields $R^2 = 0.0047$ and $p = 0.391$. The coefficient is negative (`-0.0121`), meaning that higher confidence actually predicts slightly worse run outcomes vs. ITT in this sample.
- **New `stack_trust_score` Performance:** Yields $R^2 = 0.0051$ and $p = 0.370$. The coefficient is positive (`+0.0118`), meaning that higher trust scores correctly correlate with higher run production vs. ITT.
- **R-squared Comparison:** Both models explain less than 1% of the total variance in run scoring vs ITT. The new score has a slightly higher $R^2$ (`0.0051` vs `0.0047`) and a slightly lower p-value (`0.370` vs `0.391`), but neither model is statistically significant at the 95% level.

### Strategic Recommendation:
> [!WARNING]
> The regression confirms that the proposed composite `stack_trust_score` does NOT show statistical significance in predicting team run scoring floors, although it corrects the negative slope of `attack_conf` to a directionally correct positive slope. Both scores explain almost none of the actual variance. Stacks should be ranked by blended projections and GPP leverage, rather than relying on a deterministic 'confidence' or 'trust' score. DO NOT deploy this score as a ranking driver without Konrad's review.
