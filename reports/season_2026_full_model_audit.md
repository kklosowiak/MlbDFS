# OMEGA 2026 Full-Season & Mid-Season Change Audit Report

**Generated:** 2026-11-01  
**Scope:** End-to-end audit of every model layer, signal, formula, data scraper, and mid-season architectural change across the complete 2026 MLB regular season (**Apr 15 – Sep 27, 2026**).  
**Target Contest Profile:** DraftKings Classic (\$50,000 cap, 2 SP + 8 Hitters), \$121 Single-Entry (~275–400 entrants) + \$5/\$10 GPP ticket (optimizing for top-1 single-lineup ceiling: 15+/20+ DK pt hitters, 5+/7+ run team explosions, and 25+ DK pt SP games).

---

## 1. Full-Season Dataset Coverage (Confirmed via Production Scoring)

By joining both the **Pre-July Archive** (`reports/archive/results_*.json`, Apr 15 – Jul 1) and the **Post-July Passive Tracker** (`scratch/passive_tracker/slates/omega-results_*.json`, Jul 2 – Sep 27) against our complete MLB StatsAPI boxscore backfill (`data/season_2026/actuals/`, 2,198 regular-season games, single-game `dh == 0`), we audited:

| Period | Slate Dates | Team-Game Rows | SP Starts (`started == 1`) | Hitter Games (`played == 1`) |
| :--- | :---: | :---: | :---: | :---: |
| **Pre-July Archive (Apr 15 – Jul 1)** | 47 | 892 | 870 | 7,319 |
| **Post-July Tracker (Jul 2 – Sep 27)** | 84 | 1,446 | 1,613 | 13,237 |
| **Combined 2026 Regular Season** | **131** | **2,338** | **2,483** | **20,556** |

### Pre-July vs. Post-July Model Evolution (Spearman Rank Correlation)
| Layer & Metric | Pre-July (`Apr–Jun`) | Post-July (`Jul–Sep`) | Evolution & Diagnosis |
| :--- | :---: | :---: | :--- |
| **Pitcher `alpha_score` vs. Actual DK Pts** | `+0.2108` ($N=870$) | **`+0.3421`** ($N=1,613$) | **+62% relative improvement.** Mid-season SP additions (`trap_vulnerable`, `is_low_ceiling`, `is_juiced_target`, `is_outlier_driven`, `is_paradox`) substantially improved SP ranking. |
| **Hitter `player_score` vs. Actual DK Pts** | `+0.0894` ($N=7,319$) | **`+0.1245`** ($N=13,237$) | **+39% relative improvement.** Prop juice gates (`is_juiced_target`, `is_speed_target`) and `smash_factor` added real ceiling separation. |
| **Team `stack_score` vs. Actual Runs** | `+0.1075` ($N=892$) | `+0.1244` ($N=1,446$) | **Underperformed raw Vegas `implied_total` in both halves** (`+0.1468` Pre-Jul, `+0.1835` Post-Jul). Non-ITT multipliers and mid-season `stack_trust_score` diluted the Vegas run anchor. |

---

## 2. Audit of Every Major Mid-Season Change (What Helped vs. What Hurt)

### Change A: July 15 DQI Reversal (`DQI_TRUST` -> `OVERPRICED`, `DQI_FADE` -> `LEVERAGE`) — **HURT (Revert for 2027)**
* **What Changed:** On July 15 (`OMEGA_DECISIONS.md`, commits `6a703df`, `5ea9c2c`), based on an early 20-row sample, `DQI >= 82` (`TRUST`, `+10 CONF`) was renamed `OVERPRICED` and given a `-4.0 CONF` penalty (`utils/attack_confidence.py` lines 536–548), while `DQI < 50` (`FADE`, `-8 CONF`) was renamed `LEVERAGE` (`0 CONF`).
* **Full-Season & Post-July Out-of-Sample Result (`reports/season_2026_dqi_audit.md` & `dqi_log.csv`):**
  * In `scratch/passive_tracker/signals/dqi_log.csv` (logged strictly after the July 15 change), **`OVERPRICED` ($\text{DQI} \ge 82$, $N=18$) averaged `5.78` runs vs. `4.81` Vegas ITT (`+0.96` runs over Vegas, `61.1%` beat ITT, `61.1%` scored 5+ runs)**, while **`LEVERAGE` ($\text{DQI} < 50$, $N=38$) averaged `3.55` runs (`-0.34` runs vs. ITT, `34.2%` beat ITT, `31.6%` scored 5+ runs)**.
  * Across all 1,446 Post-July regular-season team-games, `DQI >= 82` ($N=22$) achieved a **59.1% 5+ run rate (+16.1pp over league average, 95% CI `[+1.25pp, +35.35pp]`)** and **+0.68 runs over ITT**.
* **2027 Fix:** Restore `DQI >= 82` as `DQI_TRUST` with `+6.0` to `+8.0` stack bonus, and restore `DQI < 50` as `DQI_FADE` with `-6.0` stack penalty.

### Change B: July 9–13 `stack_trust_score` Deployment in `blended_rating` — **HURT (Critical Bug — Remove for 2027)**
* **What Changed:** `utils/slate_report_generator.py` lines 84–86 defines `stack_trust_score = itt * 10.0 - 10.0 * opp_sp_any_flag`, and `main.py` lines 559–564 sets team `blended_rating = (stack_score + stack_trust_score) / 2`.
* **Why It Backfired:**
  1. `opp_sp_any_flag` is `1.0` whenever the opposing pitcher has `trap_vulnerable`, `trap_short_leash`, `is_low_ceiling`, `is_hazard`, or `is_paradox`.
  2. Thus, **when a team faces a vulnerable/flagged trap pitcher, `stack_trust_score` subtracts `-10.0` points from the offensive stack**!
  3. Even the July 13 backtest (`reports/stack_trust_score_backtest.md`) found $R^2 = 0.0053, p = 0.359$ and explicitly warned: *"DO NOT deploy this score as a ranking driver."*
  4. Across the 84 Post-July regular-season slates ($\ge 8$ teams), replacing the pre-July `legacy_blend = 0.5 * stack_score + 0.5 * attack_conf` with `blended_rating` reduced Top-1 stack scoring from **6.06 runs (40.6% 7+ runs)** down to **5.75 runs (35.9% 7+ runs)** (`stack_trust_score` alone averaged **5.08 runs, 28.1% 7+ runs**).

### Change C: July 3 Pitcher `is_trap` Split (`trap_vulnerable` vs. `trap_short_leash`) — **WORKED (Keep & Separate Stack Impact)**
* **What Changed:** `utils/pitcher_trap.py` split `is_trap` into `Vulnerable` (high Vegas ITT $\ge 4.5$, bad recent ERA $\ge 5.00$, or low physics $< 35$) vs. `Short Leash` (`outs_line <= 15.5`, low pitch count).
* **Confirmed Full-Season Performance (`dataset_pitchers.csv` & passive logs):**
  * **`trap_vulnerable` ($N=214$ starts):** Averaged **9.73 DK pts** vs. 13.15 off (**-3.42 DK pts**, **54.2% bust rate `< 10` DK pts**). Opposing stacks in `trap_vulnerable_log.csv` ($N=216$) averaged **5.11 runs (+1.91 runs over ITT, 46.8% 5+ runs)** while the SP averaged **2.67 ER in 4.39 IP**.
  * **`trap_short_leash` ($N=202$ starts):** Averaged **11.35 DK pts** vs. 12.89 off (**-1.54 DK pts**, **45.0% bust rate**). Opposing stacks averaged **4.67 runs (+0.21 runs over ITT)** while the SP averaged **4.44 IP**.
* **2027 Fix:** Keep both flags as SP avoids (`-24` CONF for `trap_vulnerable`, `-14` CONF for `trap_short_leash`), and give **opposing team stacks a direct bonus when facing `trap_vulnerable` SPs** (instead of the `-10` penalty in `stack_trust_score`).

### Change D: June 28 Game-Level `PARADOX` Resolver & July 8 `is_outlier_driven` — **WORKED (Keep)**
* **Confirmed Performance:**
  * **`is_paradox` ($N=233$ SP starts):** Averaged **10.78 DK pts** vs. 13.02 off (**-2.24 DK pts**, 95% CI `[-3.53, -0.84]`). When a high-rated SP faces an elite offense, fading the SP is profitable.
  * **`is_outlier_driven` ($N=629$ SP starts):** Averaged **11.67 DK pts** vs. 13.35 off (**-1.69 DK pts**, 95% CI `[-2.62, -0.71]`, `+5.3%` bust rate). Stripping a pitcher's single best recent start (`recent_era_ex_best`) successfully exposed mirage form.

### Change E: June 28 Hitter `COLD_HIGH_BR_WARNING` (`is_cold_high_br_warning`) — **BACKFIRED (Retire for 2027)**
* **What Changed:** Added a warning in `utils/slate_report_generator.py` and `run_dk_optimizer.py` (lines 354–356) advising the user to replace high-blended-rating hitters who have `is_cold_streak_msmi == True`.
* **Confirmed Out-of-Sample Result (`cold_high_br_log.csv`, $N=60$):**
  * Across 60 tracked instances, flagged hitters averaged **8.26 DK pts (+0.79 DK pts ABOVE their batting-order baseline)** and hit **15+ DK pts 21.7% of the time** (vs. 13.8% league average)!
  * High-talent hitters in strong lineup spots mean-revert rapidly; fading them for a 7-day K%/OPS dip cost GPP ceiling.

### Change F: OMEGA v17.3 Non-Linear Vegas ITT Compression (`calibrate_vegas_itt`) — **MIXED (Hurts GPP Ceiling above 5.5 ITT)**
* **What Changed:** `utils/market_utils.py` lines 93–110 compresses `implied_total > 5.5` downward by 50% of the excess (`5.5 + (itt - 5.5) * 0.50`) and inflates `implied_total < 3.5` upward by 75% of the deficit (`3.5 - (3.5 - itt) * 0.25`).
* **Confirmed Full-Season Result ($N=2,338$ team-games):**
  * Across all 2,338 team-games, `calibrate_vegas_itt` slightly improved mean-squared error on extreme totals (`RMSE 3.1739` vs. `3.1897` raw; for `ITT > 5.5`, $N=156$, raw mean was `6.166`, calibrated mean was `5.833`, actual mean was `5.776`).
  * **However, for GPP stack ranking**, compressing `ITT > 5.5` by 50% flattened the gap between a 6.5-ITT slate-breaker and a 5.2-ITT secondary stack, allowing noisy multipliers (`is_burst`, `bullpen_boost`) to leapfrog 5.0-ITT teams over 6.2-ITT teams (**59.0% of `ITT > 5.5` teams scored 5+ runs and 37.2% scored 7+ runs!**).

---

## 3. Confirmed Production Bugs & Dead Code Paths Found in Code Inspection

Every item below was verified by executing the actual production code against our 2026 cached data:

1. **CRITICAL BUG — Platoon Math Short-Circuit & Handedness Blindness ([`utils/platoon_math.py`](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/utils/platoon_math.py#L11-L48)):**
   * **Root Cause:** When `compute_platoon_multiplier()` is called from `main.py` (lines 1221 and 1846), `matchup_radar` is always passed. Lines 11–46 check if the hitter and pitcher exist in `data/matchup_data.json`. If they do (~95% of starters), the function **immediately returns `dna_multiplier = h_expected / l_expected` and never executes the LHP/RHP handedness split logic on lines 50–95!**
   * **Why `dna_multiplier` Is Mathematically Broken:**
     1. `data/matchup_data.json` (`data/savant_fetcher.py`) stores pitch-type xwOBA (`FF`, `SI`, `SL`, `CU`, `CH`) **without splitting by pitcher handedness**.
     2. `h_expected / l_expected` divides the hitter's overall pitch-type xwOBA by the **league-average xwOBA** (`~0.310`), NOT by the hitter's own baseline xwOBA! Multiplying `base_xwoba * (h_expected / l_expected)` **squares the hitter's overall talent** while ignoring pitcher handedness.
     3. **Confirmed Proof on Real Cache:** Running `compute_platoon_multiplier` for left-handed platoon bat **Kerry Carpenter** (`0.405` OPS vs LHP, `0.723` OPS vs RHP) gives **`1.106x` (+10.6%) vs. LHP Garrett Crochet** and **`0.988x` vs. RHP Kevin Gausman**! For **Joc Pederson** (`0.616` OPS vs LHP, `0.828` OPS vs RHP), it gives **`1.246x` vs. LHP Garrett Crochet**!
     4. Furthermore, even on lines 77–89 (when `matchup_radar` is `None`), line 77 checks `(split_pa_2025 + split_pa_other_2025) >= 40` instead of `split_pa_2025 >= 40`, causing Joc Pederson's 19-PA fluke vs LHP in 2025 (`1.012` OPS in 19 PAs) to give him a `1.30x` boost vs LHP!
   * **Impact:** Explains why `ELITE PLATOON` ($N=768$, `-0.18` DK pts vs baseline) and `PLATOON TRAP` ($N=3,473$, `+0.28` DK pts vs baseline) had zero predictive edge all season.

2. **CRITICAL BUG — `walks_boost` Fired on 85.1% of Hitters (`12,157 / 14,293`) ([`engine/sharps_weighting.py`](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/engine/sharps_weighting.py#L738-L746)):**
   * **Root Cause:** Line 743 checks `if wf >= 0.5 and (wp < 0 or wp >= 100): walks_boost = 3.0`. In American odds, every underdog price is `>= +100` (`+115`, `+215`, `+320`) and every favorite price is `< 0` (`-110`, `-140`). Thus `(wp < 0 or wp >= 100)` is `True` for **100% of non-zero American odds**, giving `+3.0` points to every hitter who had any walk prop posted (even Over 1.5 walks at `+320`).
   * **Fix:** Require `wf == 0.5 and wp <= -125 and wp < 0` (genuinely juiced Over 0.5 walks).

3. **CRITICAL BUG — Invalid Odds API Market Keys Causing 14x Slow Fetching & Dead Signals ([`data/market_fetcher.py`](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/data/market_fetcher.py#L29-L34)):**
   * **Root Cause:** `self.prop_markets` requests `'batter_runs'` and `'batter_runs_g_rbi'`. In The Odds API v4 MLB schema, the valid market keys are **`'batter_runs_scored'`** and **`'batter_hits_runs_rbis'`**.
   * **Impact:**
     1. Because those 2 keys are invalid, a combined request returned HTTP 422, which previously led to splitting `self.prop_markets` into 14 separate HTTP requests per game (`data/market_fetcher.py` lines 300–307).
     2. `runs_juice`, `runs_target` (`utils/prop_juice.py`), and `rr_boost` (`engine/sharps_weighting.py` line 759) **fired 0 times across all 14,293 hitter rows all season**!
     3. Similarly, `strikeouts_penalty` (`batter_strikeouts`) fired **0 times all season**.

4. **CRITICAL BUG — `barrel_pct` and `hard_hit_pct` Were `0.0` for 100% of Hitters ([`data/statcast_bridge.py`](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/data/statcast_bridge.py#L316-L364)):**
   * **Root Cause:** `refresh_statcast_cache` calls `statcast_batter_expected_stats(yr, minPA=min_pa)` and looks up `row.get("barrel_batted_rate")` and `row.get("hard_hit_percent")`. Those columns do not exist in `statcast_batter_expected_stats`—they live in `pybaseball.statcast_batter_exitvelo_barrels(yr, minBBE=50)`.
   * **Impact:** The `+3%` hard-hit boost (`>= 45%`) and `+2%` barrel boost (`>= 12%`) in `engine/sharps_weighting.py` lines 780–785 were 100% dead code all season.

5. **CRITICAL BUG — Hardcoded Stale `xwoba_registry` Overriding Real Statcast Data ([`data/hitter_prop_analyzer.py`](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/data/hitter_prop_analyzer.py#L17-L50)):**
   * **Root Cause:** `_resolve_xwoba()` checks `self.xwoba_registry` **before** checking `statcast_cache.json`.
   * **Impact:** Slumping stars carried hardcoded 2024/2025 elite xwOBAs all season:
     * **Gunnar Henderson:** Hardcoded `.395` vs. actual 2026 Statcast `.314` (**+.081 error**, `.698` OPS)
     * **Royce Lewis:** Hardcoded `.385` vs. actual 2026 `.313` (**+.072 error**, `.688` OPS)
     * **Luis Robert Jr.:** Hardcoded `.385` vs. actual 2026 `.321` (**+.064 error**, `.707` OPS)
     * **Mookie Betts:** Hardcoded `.390` vs. actual 2026 `.331` (**+.059 error**, `.730` OPS)
     * **Christian Walker:** Hardcoded `.358` vs. actual 2026 `.303` (**+.055 error**, `.731` OPS)
     * **Ezequiel Tovar:** Hardcoded `.325` vs. actual 2026 `.275` (**+.050 error**, `.588` OPS)

6. **Hardcoded Stale Team & Pitcher Overrides Still Active in Production:**
   * [`main.py` lines 131–142](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/main.py#L131-L142): Hardcoded override replacing San Diego Padres `'TBD'` starter with `'German Marquez'`.
   * [`data/statcast_bridge.py` lines 273–283](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/data/statcast_bridge.py#L273-L283): Hardcoded team overrides forcing Willi Castro to Colorado Rockies, Jake Bauers to Milwaukee Brewers, and Alec Burleson to St. Louis Cardinals.
   * [`utils/opener_detector.py` lines 519 & 638](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/utils/opener_detector.py#L519): Hardcoded rule matching `'mitch spence'` to `'Kansas City Royals'`.

7. **Dead Team Boosts (`is_pinnacle_offense_boost` and `is_velocity_boost` Fired 0 Times):**
   * In `dataset_teams.csv` (1,446 rows), both `is_pinnacle_offense_boost` and `is_velocity_boost` fired **0 times** all season because `pinnacle_total` and `opening_captured_at` within the `< 2.0 hour` window were never populated during lock runs.

8. **Pitcher `sharp_fade` Penalty Is Directionally Reversed ([`utils/attack_confidence.py`](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/utils/attack_confidence.py#L649-L654)):**
   * `sharp_fade` subtracts `-12.0 CONF` when a pitcher's team has negative money divergence (`<= -20%`). Yet across 119 regular-season starts (`dataset_pitchers.csv`), `sharp_fade` pitchers averaged **14.38 DK pts vs. 12.56 off (+1.81 DK pts, bust rate 32.8% vs. 40.8% off)**! Why? Because public money heavily backs road favorites or popular offenses against strong home/contrarian aces, creating negative money divergence on the pitcher's team ML even when the pitcher's strikeout/outs props are rock solid.

---

## 4. All 18 Passive Tracker Signal Logs Summary (`scratch/passive_tracker/signals/`)

| Signal Log | Layer | Logged Rows | Primary Outcome Metric | Vs. Baseline / ITT | Ceiling / Hit Rate | Verdict |
| :--- | :--- | :---: | :--- | :--- | :--- | :--- |
| `trap_vulnerable` | Pitcher / Opp Stack | 216 | Opp **5.11 R** (SP 2.67 ER, 4.39 IP) | **+1.91 R vs ITT** | **46.8% Opp 5+ R** | **ELITE SIGNAL** |
| `trap_short_leash` | Pitcher / Opp Stack | 199 | Opp **4.58 R** (SP 2.34 ER, 4.44 IP) | **+0.23 R vs ITT** | **42.7% Opp 5+ R** | **STRONG SP FADE** |
| `anti_chalk_smash` | Hitter | 1,309 | **7.21 DK pts** | **+0.99 DK pts** | **16.7% (15+ DK)** | **ELITE GPP SIGNAL** |
| `strong_edge` | Hitter | 1,438 | **7.06 DK pts** | **+0.23 DK pts** | **16.2% (15+ DK)** | **MODEST CEILING** |
| `hot_msmi` | Hitter | 2,492 | **6.72 DK pts** | `+0.37` (in dataset) | **15.8% (15+ DK)** | **KEEP (Small Boost)** |
| `steam` | Team Stack | 92 | **4.96 Runs** | **+0.51 R vs ITT** | **43.5% (5+ R)** | **USE IN DQI ONLY** |
| `top_stack` | Team Stack | 108 | **4.86 Runs** | **+0.13 R vs ITT** | **42.6% (5+ R)** | **LAGGED VEGAS ITT** |
| `burst` | Team Stack | 259 | **4.71 Runs** | **+0.05 R vs ITT** | **44.4% (5+ R)** | **NOISE (+0.05 R)** |
| `pen_fatigue` | Team Stack | 798 | **4.30 Runs** | **-0.02 R vs ITT** | **41.0% (5+ R)** | **NOISE (`is_fatigued` -5% p7)** |
| `pitcher_walks_hazard` | Pitcher / Opp Stack | 575 | Opp **4.50 R** (SP 2.44 ER) | **+0.09 R vs ITT** | **43.3% Opp 5+ R** | **NOISE (`is_hazard` -0.14 DK)** |
| `sharp_fade_pitcher` | Pitcher | 130 | Opp **4.08 R** (SP 2.28 ER, 5.05 IP) | **+0.28 R vs ITT** | **40.0% Opp 5+ R** | **REVERSED (SP averaged 14.38 DK)** |
| `cold_high_br` | Hitter | 60 | **8.26 DK pts** | **+0.79 DK pts** | **21.7% (15+ DK)** | **REVERSED (Do Not Fade!)** |
| `fade_risk` | Team Stack | 20 | **6.35 Runs** | **+0.93 R vs ITT** | **70.0% (5+ R)** | **REVERSED (Do Not Fade!)** |
| `elite_platoon` | Hitter | 768 | **6.73 DK pts** | **-0.18 DK pts** | **14.7% (15+ DK)** | **BROKEN BY `platoon_math.py` BUG** |
| `platoon_trap` | Hitter | 3,473 | **6.31 DK pts** | **+0.28 DK pts** | **13.6% (15+ DK)** | **BROKEN BY `platoon_math.py` BUG** |

---

## 5. Prioritized 2027 Upgrade Roadmap (Confirmed Quantitative Gains)

### Priority 1: Rebuild Team Stack Scoring Around Raw Vegas ITT + Validated GPP Signals
Across the 84 Post-July regular-season slates ($\ge 8$ teams), anchoring stack scores on **uncompressed Vegas `implied_total`** + `team_xwoba` + the 4 statistically validated team signals (`is_anti_chalk_smash`, `is_pitch_alignment`, `DQI >= 82`, `opp_trap_vulnerable`) and subtracting `DQI < 50` and `is_fatigued` (`cf_stack_2027`) produced:

| Stack Ranking Method | Spearman $r$ (Post-Jul) | Top-1 Stack Mean Runs | Top-1 Stack 5+ Run Rate | Top-1 Stack 7+ Run Rate | Top-2 Stacks Mean Runs |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `stack_trust_score` (Jul 9 addition) | `N/A` | 5.08 R | 56.2% | 28.1% | 5.15 R |
| `attack_conf` (Decision layer) | `+0.0834` | 5.69 R | 54.7% | 34.4% | 5.26 R |
| `stack_score` (Engine layer) | `+0.1244` | 5.72 R | 51.6% | 35.9% | 5.38 R |
| **Shipped `blended_rating` (2026 Prod)** | `+0.1294` | **5.75 R** | **56.2%** | **35.9%** | **5.67 R** |
| `legacy_blend` (`0.5*stack + 0.5*conf`) | `+0.1180` | 6.06 R | 57.8% | 40.6% | 5.53 R |
| Raw Vegas `implied_total` | **`+0.1835`** | **6.27 R** | **64.1%** | **42.2%** | **5.82 R** |
| **2027 Counterfactual (`cf_stack_2027`)** | **`+0.1819`** | **6.64 R** | **68.8%** | **42.2%** | **5.90 R** |

* **Action Items for Team Layer:**
  1. **Delete `stack_trust_score`** from `utils/slate_report_generator.py` and `main.py`.
  2. **Remove `calibrate_vegas_itt()` compression** on `implied_total > 5.5` when scoring GPP stacks.
  3. **Restore DQI polarity:** `DQI >= 82` -> `TRUST` (`+3.0` stack pts / `+8.0` CONF); `DQI < 50` -> `FADE` (`-2.5` stack pts / `-8.0` CONF).
  4. **Retire noisy team multipliers:** Remove `is_fade_risk`, `is_public_steam_trap`, `is_true_talent_penalty`, and reduce `is_burst` and `bullpen_boost` caps so a 4.5-ITT team can never outscore a 5.8-ITT team unless backed by `DQI >= 82` + `opp_trap_vulnerable`.

### Priority 2: Fix Hitter Platoon Math, Prop Markets, and Statcast Barrels
1. **Fix `utils/platoon_math.py` (`compute_platoon_multiplier`):**
   * Remove the `matchup_radar` short-circuit on lines 11–48 so `compute_platoon_multiplier` **always** computes true LHP/RHP handedness split ratios (`vs_left_ops` / `vs_right_ops` regressed with a Bayesian prior of `100` PAs so a 19-PA sample in 2025 cannot produce a `1.30x` multiplier).
   * In `engine/matchup_radar.py`, normalize pitch-type xwOBA against the **hitter's own overall xwOBA** (`(h_pitch_xwoba / h_overall_xwoba) / (l_pitch_xwoba / l_overall_xwoba)`), so `MatchupRadar` measures true pitch-mix synergy rather than double-counting baseline hitter xwOBA.
2. **Fix `data/statcast_bridge.py` Barrel & Hard-Hit Ingestion:**
   * Merge `pybaseball.statcast_batter_exitvelo_barrels(yr, minBBE=25)` into `refresh_statcast_cache()` so `barrel_pct` and `hard_hit_pct` are populated for all hitters.
3. **Fix `data/market_fetcher.py` Prop Market Names:**
   * Replace `'batter_runs'` with `'batter_runs_scored'` and `'batter_runs_g_rbi'` with `'batter_hits_runs_rbis'`.
4. **Fix `engine/sharps_weighting.py` `walks_boost` Condition:**
   * Change line 743 from `if wf >= 0.5 and (wp < 0 or wp >= 100):` to `if wf >= 0.5 and wp <= -125 and wp < 0:`.
5. **Retire `self.xwoba_registry` in `data/hitter_prop_analyzer.py` & `is_cold_high_br_warning`:**
   * Let real Statcast `xwoba` (blended 2026 + 2025 by PA weight) drive `_resolve_xwoba()`, and remove the `COLD_HIGH_BR_WARNING` optimizer prompt.

### Priority 3: Calibrate Pitcher Projections & Remove Reversed SP Penalties
1. **Shrink `dk_points_mean` Extremes (`data/pitcher_analyzer.py`):**
   * Across 1,613 regular-season starts, `Actual_DK = 3.61 + 0.690 * dk_points_mean` (Q1 projected `5.5` vs `7.8` actual; Q5 projected `20.4` vs `17.9` actual). Applying `0.70` linear shrinkage toward the `12.7` DK pt mean lowers RMSE from `10.229` to `10.084`.
2. **Remove `sharp_fade` (`-12 CONF`), `is_hazard` (`-12 CONF`), and `is_high_variance` from Pitcher Scoring:**
   * `sharp_fade` pitchers scored **+1.81 DK pts above average** with an **8.0pp lower bust rate**.
   * Keep and emphasize the 6 confirmed SP signals: **`is_juiced_target` (+6.72 DK pts)**, **`is_low_ceiling` (-4.84 DK pts)**, **`trap_vulnerable` (-3.42 DK pts)**, **`is_paradox` (-2.24 DK pts)**, **`is_prop_juice` (+2.05 DK pts)**, and **`is_outlier_driven` (-1.69 DK pts)**.
