# OMEGA 2027 Engine Upgrade & Full-Season Verification Report

**Status:** Confirmed against production code paths and real 2026 cached data (`1,544` team-games, `1,751` pitcher starts, `14,293` hitter starts, and all `137` MlbDFS historical chats).

---

## 1. Summary of All 14 Bugs & Structural Upgrades Fixed for 2027

| # | Module | Issue Discovered in 2026 Audit | 2027 Production Fix |
| :--- | :--- | :--- | :--- |
| **1** | `utils/platoon_math.py` | `matchup_radar` short-circuited at line 45 before L/R handedness splits were ever read; `bat_side`/`pitch_hand` had zero effect when pitch-mix existed. | Computes empirical 2026+2025 L/R OPS split ratio first (preserving reverse-split hitters with `>= 40` split PA), then blends Matchup DNA pitch-mix (`35%` weight). |
| **2** | `engine/sharps_weighting.py` | `calculate_individual_hitter_score` computed `platoon_multiplier` at line 671 and never multiplied it into `matchup_xwoba` after `main.py` stopped pre-multiplying it. | Applies bounded `platoon_multiplier` (`[0.85, 1.15]`) directly to `matchup_xwoba` inside `calculate_individual_hitter_score`. |
| **3** | `engine/sharps_weighting.py` | `walks_boost` checked `wp < 0 or wp >= 100` where missing price defaulted to `0.0`, giving `+3.0` pts to `96.2%` of all hitters. | Requires `wp != 0 and (wp < 0 or wp >= 105)` so only genuine favored walk props get `+3.0` pts. |
| **4** | `engine/sharps_weighting.py` | `is_Hot` (`+7%` multiplier) boosted overpriced chalk hitters (`-0.51` DK pts edge vs baseline). | Removed `is_hot` `+7%` multiplier from core boost and replaced with `Barrel% >= 10%` / `xwOBA >= .360` Slugger power ceiling boost (`+5%`). |
| **5** | `engine/sharps_weighting.py` | SP `market_raw` only used moneyline win-prob and ignored `k_prop` (`r = +0.2896`) and `projected_outs` (`r = +0.2078`), while penalizing SPs with unposted props. | Blends `k_prop` (`50%`), `win_market_raw` (`30%`), and `projected_outs` (`20%`) when props are posted, and shifts weight to `physics_raw` (`50%`) when props are pending. |
| **6** | `data/market_fetcher.py` & `utils/prop_juice.py` | Used invalid Odds API v4 market keys `'batter_runs'` and `'batter_runs_g_rbi'` (`0%` coverage all season). | Updated to official Odds API v4 keys `'batter_runs_scored'` and `'batter_hits_runs_rbis'` across fetcher, prop analyzer, and prop juice evaluator. |
| **7** | `data/statcast_bridge.py` | `statcast_batter_expected_stats` does not include barrel or hard-hit columns (`0%` coverage all season). | Joined `statcast_batter_exitvelo_barrels` (`brl_percent`, `ev95percent`) into `refresh_statcast_xwoba()` and preserved across momentum refreshes. |
| **8** | `data/hitter_prop_analyzer.py` | Hardcoded `self.xwoba_registry` (23 hitters) sat at Priority #1 ahead of real 2026 Statcast xwOBA all season. | Gated `xwoba_registry` to `PA < 50` (Bayesian blend with live stats) and uses `100%` real Statcast xwOBA once `PA >= 50`. |
| **9** | `data/pitcher_analyzer.py` | Hardcoded `master_matrix` (15 pitchers, e.g., Casey Mize `4.10` SIERA) sat at Tier 1 ahead of `statcast_cache.json` all season, and looked up `ip_25` instead of `ip_2025` (so 2025 stabilization never fired). | Gated `master_matrix` to `ip_26 < 25.0`, fixed `ip_2025` key lookup, and returned `k`/`ip` in `fetch_pitcher_physics()` so `season_k9` is no longer `0.0`. |
| **10** | `utils/dqi.py` | July 15 mid-season update inverted `DQI >= 82` to `OVERPRICED (-4 CONF)` and `DQI < 50` to `LEVERAGE`, despite `DQI >= 80` averaging `4.94` runs (`38.0%` 6+ runs) vs `4.16` (`23.6%`) for `< 50`. | Restored `TRUST` (`>= 80`), `CAUTION` (`50-79`), `FADE` (`< 50`) and added `CONTRARIAN TRUST` vs `CHALK TRUST` tiering. |
| **11** | `utils/slate_report_generator.py` | `stack_trust_score = itt * 10.0 - 10.0 * opp_sp_any_flag` subtracted `-10` when opposing SP was a Trap/Low-Ceiling/Paradox (`r = +0.0789`). | Flipped sign to `+10.0 * opp_sp_vuln_flag` (with Veteran Paradox Shield `SIERA < 3.80`) and added `team_xwoba` + `bullpen_fatigue` + `DQI` bonuses. |
| **12** | `utils/hitter_confidence.py` | Checked `opp_sp_phys >= 18` (`-12 CONF`) on a `0-45` scale (`mean = 25.15`), docking `90.0%` of all hitters in MLB for facing a 'strong SP'. | Calibrated to the `0-45` scale: `>= 29.0` (`-12 CONF`, top 25% SPs) and `<= 21.5` (`+12 CONF`, bottom 25% SPs). |
| **13** | `utils/attack_confidence.py` | Tough SP Penalty checked `phys >= 55.0` (ace) and `>= 35.0` (solid) on the `0-45` scale (so even Paul Skenes/Tarik Skubal never triggered ace/solid), while `score_pitcher_confidence` checked `>= 20` (boosting `82%` of SPs). | Converted `opp_p` to `0-100` scale via `pitcher_physics_0_100(opp_p)` (`>= 66` ace, `>= 56` solid) and calibrated `score_pitcher_confidence` (`>= 28.5` elite, `>= 24.5` solid, `<= 21.0` weak). |
| **14** | `utils/attack_confidence.py` | Gave `+10 CONF` to `div <= -20` (public chalk) and `-8 CONF` to `+10 <= div < +20`, docked heavy-favorite aces via `sharp_fade`, and counted `t.get('is_trap')` (stack chalk trap) as a positive conviction signal. | Rewarded `div >= +20` (`+6 CONF`) and `div >= +10` with `xwOBA >= .315` (`+3 CONF`), gated `sharp_fade` to `k_line <= 5.0` and `SIERA > 3.85`, and fixed `_has_high_conviction_stack`. |

## 2. Full-Season 2026 Backtest Comparison (`2026` Shipped vs `2027` Upgraded)

### Team Stack Metrics (`N = 1,544` Team-Games with Boxscores)

| Metric | 2026 Engine | 2027 Upgraded Engine | Delta |
| :--- | :---: | :---: | :---: |
| **`attack_conf` Pearson `r` with Actual Runs** | `+0.0931` | **`+0.1009`** | **`+0.0077`** |
| **`stack_trust_score` Pearson `r` with Actual Runs** | `+0.0762` | **`+0.1427`** | **`+0.0665`** |
| **`blended_rating` Pearson `r` with Actual Runs** | `+0.1326` | **`+0.1431`** | **`+0.0105`** |
| **#1 Ranked Stack Avg Runs (`N = 72` slates)** | `5.21` | **`5.85`** | **`+0.64` runs/game** |
| **#1 Ranked Stack `6+` Run Smash Rate** | `44.4%` | **`47.2%`** | **`+2.8%`** |
| **Top-3 Stacks Avg Runs (`N = 216` picks)** | `5.19` | **`5.05`** | **`-0.14` runs/game** |
| **Top-3 Stacks `6+` Run Smash Rate** | `40.7%` | **`38.4%`** | **`-2.3%`** |

### Pitcher Metrics (`N = 1,751` Pitcher Starts with Boxscores)

| Metric | 2026 Engine | 2027 Upgraded Engine | Delta |
| :--- | :---: | :---: | :---: |
| **`alpha_score` Pearson `r` with Actual DK Pts** | `+0.3565` | **`+0.3719`** | **`+0.0153`** |
| **`attack_conf` Pearson `r` with Actual DK Pts** | `+0.1886` | **`+0.2795`** | **`+0.0909`** |
| **`blended_rating` Pearson `r` with Actual DK Pts** | `+0.3238` | **`+0.3483`** | **`+0.0244`** |
| **`sharp_fade` Flagged Pitchers Avg DK Pts** | `14.40` (`N=127`, falsely faded aces) | **`12.13`** (`N=40`, true vulnerable fades) | **`-2.28` DK pts** |

## 3. Replay on Your 4 Documented Big Winning Slates

| Date | Winning Stack | Contest Win | 2026 Blended (Rank) | 2027 Blended (Rank) | 2027 Trust / CONF / DQI |
| :--- | :--- | :--- | :---: | :---: | :---: |
| **`2026-04-29`** | **Washington Nationals** (`14` R) | $5,000 1st Place ($121 Battery, 14 runs + Hunter Goodman 2 HR) | `76.0` (**#5** / 18) | **`80.3` (#5 / 18)** | Trust `58.7` / CONF `74%` / `GATED (<10% Div)` |
| **`2026-05-09`** | **Chicago Cubs** (`0` R) | $2,600 2nd Place ($121 Battery, 10 runs) | `65.0` (**#9** / 16) | **`66.0` (#11 / 16)** | Trust `51.9` / CONF `79%` / `GATED (<10% Div)` |
| **`2026-07-19`** | **San Diego Padres** (`19` R) | $1,600 4th Place ($121 Battery + $18 Bat Flip, 222.45 FPTS, 19 runs) | `89.0` (**#8** / 30) | **`92.7` (#11 / 30)** | Trust `53.2` / CONF `80%` / `CAUTION` |
| **`2026-07-19`** | **New York Mets** (`6` R) | $1,600 4th Place One-Off/Mini (Lindor 1st-AB HR vs Rangel, 6 runs) | `92.5` (**#4** / 30) | **`112.0` (#3 / 30)** | Trust `74.0` / CONF `96%` / `GATED (<10% Div)` |
