1. What this model is

The OMEGA model is a proprietary, end-to-end MLB DFS and sports betting analytics engine specifically engineered for DraftKings Classic contests. Running on Python and hosted on Render, the system provides a web dashboard that the owner uses daily during the MLB season to generate high-upside GPP lineups and identify profitable sports betting edges. The codebase is vibe-coded in a pair-programming loop, leveraging Antigravity for implementation tasks and Claude for high-level architecture decisions and model validation.

2. How the scoring works

Scoring is calculated across three distinct layers. The Physics layer evaluates pure player performance using Statcast metrics like xwOBA, SIERA, and CSW%. The Market layer assesses Vegas implied team totals, Moneyline movements, line divergence, and player prop juice. Physics and Market scores are blended using weights derived from OLS regression on historical backtest data, allocating an 80/20 ratio for stack scoring and a 45/20 ratio for pitchers. Finally, the Decision layer computes a blended rating, defined as the average of the raw score and the attack confidence, which directly feeds the PuLP DraftKings optimizer.

3. Proprietary signals and what makes it different

What sets OMEGA apart are its custom, highly specialized proprietary signals. The DQI triple gate filters out high-variance stacks by checking pitcher form, reliever fatigue, and walk-rate matchups to verify stack safety. The MSMI dual-factor momentum signal tracks hitter performance swings over rolling intervals. The sticky pitcher trap applies a feed-drop persistence logic that identifies pitchers whose recent struggles or high pitch counts make them targets despite favorable baseline stats. The NPAS slate-relative platoon system computes platoon advantages compared to the active slate's averages rather than static baselines. Matchup DNA blends pitcher pitch-mix usage with hitter pitch-type xwOBA to predict matchup-level synergy. The true talent sabermetric penalty adjusts player baselines when Statcast metrics deviate significantly from surface-level results. The Vegas ITT non-linear calibration scales team totals to capture actual runs scored distribution rather than linear expectations. The nightly signal validator and weight proposer automatically tests weights against actual slate outcomes and proposes adjustments. Finally, the doubleheader resolution engine aligns player targets, game times, and game numbers to prevent scheduling errors.

4. What's been backtested and validated

The model has been validated against 48 historical slates of actual game data, yielding critical design insights. The backtest proved that gassed bullpens perform poorly, showing a 60.9% hit rate on 5+ runs against weak bullpens compared to 47.9% against elite pens, which led to a split tiered boost. It also identified a major batting order cliff at spot 5, prompting a steep penalty for hitters batting 7th, 8th, or 9th. Raising the DQI TRUST floor to 80 improved its hit rate from 31.6% to 47.1%, while the top-ranked stack hit its run projections 64.6% of the time. Conversely, several signals were retired after showing negative correlation with success, including the whale flag (r=-0.093), the shark alpha flag (r=-0.088), sneaky premium stacks (r=-0.126), storm alpha weather adjustments, and the qualitative prop pressure labels.

### 4.1 Signal Validation Status (June 28, 2026)

The following table summarizes the validation status and performance of OMEGA's primary signals based on backtesting across all 53 historical slates in the archive (using complete DraftKings scoring actuals):

| Signal | Status | Sample Size | Key Finding |
| :--- | :--- | :--- | :--- |
| **HOT_MSMI** | Validated — buy signal | 780 instances | +2.11 DFS pts avg, 50.3% outperformance |
| **COLD_MSMI** | Validated — mild drag | 650 instances | 47.1% underperformance rate |
| **COLD_HIGH_BR_WARNING** | Validated — strong avoid | 31 instances | 54.8% underperformance, -0.58 DFS delta |
| **PLATOON_TRAP** | Validated — underperformance | 973 instances | 40.9% outperformance (below 52% baseline) |
| **STRONG_EDGE** | Flagged — possible projection inflation | 422 instances | 46.4% outperformance (below baseline) |
| **ELITE_PLATOON** | Flagged — possible projection inflation | 224 instances | 36.6% outperformance (well below baseline) |
| **FADE_RISK** | Promising — needs more data | 18 instances | 66.7% ITT underperformance, 76.9% with div < -15 |
| **PARADOX resolution** | Validated — fixed June 28 | 127 instances | ITT-first hierarchy: 54.3% vs 46.5% baseline |
| **LOCK stack accuracy** | Validated | 28 slates | 64.3% hit 5+ runs, model overconfidence at CONF 90+ |

5. The data pipeline


OMEGA ingests data from a variety of sources to compile daily snapshots. Market data is pulled from the Odds API on every refresh. Probable pitchers and starting lineups are fetched directly from the MLB StatsAPI. Baseball Savant CSV endpoints provide Statcast pitch arsenals and hitter xwOBA by pitch type, which automatically refresh every Sunday at 2:00 AM Eastern Time. Projected lineups are cross-referenced with RotoWire, while FantasyLabs consensus files supply additional split and divergence data. To lock in stable projections, opening betting lines are frozen daily at 4:30 AM Eastern Time.

6. The tech stack

The technical architecture consists of a Python backend running a Flask server hosted on Render. Optimization is solved via linear programming using the PuLP library. State data is persisted locally in statcast_cache.json for player profiles, matchup_data.json for pitch-type DNA data covering 930 pitchers and 543 hitters, and weights.json for signal weights. The key scripts in the codebase are main.py for orchestration, engine/sharps_weighting.py for the scoring engine, utils/attack_confidence.py for the decision layer, utils/dqi.py for DQI calculations, utils/pitcher_trap.py for trap logic, and data/savant_fetcher.py for the DNA pipeline.

7. Current model grade and gaps

The model currently sits at an overall grade of A-. Its primary strengths are a robust 91-test passing suite, genuine self-auditing via the nightly validator, real pitch DNA data flowing from Baseball Savant, and a data-driven process for signal retirement. The remaining gaps are the line velocity tracker, which has math defined in OMEGA_ARCHITECTURAL_UPGRADES.md but is not yet implemented, and the betting EV engine, which requires 30 real slates of data before calibration can begin. Next priorities are displaying the ownership tier for informational purposes, building the line velocity tracker, and calibrating the EV engine.

8. How the owner works

In daily operations, the owner refreshes the model every 15 minutes leading up to lock, utilizing the Render dashboard for analysis and the optimizer tab to build lineups. After generating the daily lineups, the owner drops the output json into Claude for slate advice and lineup review. The owner uses Claude as a brain trust for architecture and Antigravity for implementation. Contests are built strictly for the DraftKings Classic format, which requires roster configurations of 2 pitchers and 8 hitters (C, 1B, 2B, 3B, SS, 3 OF) under a $50,000 salary cap.

9. Session workflow

When starting a new session with Claude, the owner begins by pasting the GitHub repository URL (https://github.com/kklosowiak/MlbDFS) and the contents of this OMEGA_CONTEXT.md file. This immediately equips Claude with full architectural and operational context. Any model changes or design decisions are debated with Claude first to form a plan. The owner then writes an Antigravity prompt based on Claude's recommendations, runs the changes, and brings the verification outputs back to Claude to verify before pushing to production.

10. Audit Cadence

The model uses a three-layer audit system to stay healthy over time. Weekly: the system automatically runs a signal drift check every Sunday at 3am ET. If any signal's hit rate drifts more than 5 percentage points from its 4-week average, the dashboard surfaces an alert on the Learning & Audits page. No human action needed unless an alert fires. Monthly: every 30 days the comprehensive audit should be run manually by sending an audit prompt to Antigravity covering all 8 phases (math correctness, data flow, signal interactions, config consistency, test coverage, dead code, dashboard binding, architectural smells). After completing it the user clicks "Mark Complete" on the Audit Status section to reset the 30-day timer. Ad-hoc: after shipping any major new feature or refactor, do a focused audit on just that area within 48 hours. Mark complete in the dashboard.

The dashboard shows "Next Audit Due" dates so the user never has to remember on their own. If something needs attention the red badge will be visible on the Learning & Audits sidebar item from any page. The automated drift check reads reports/learning_feedback.json (current week) and reports/archive/feedback_*.json (previous 4 Sundays). Any new signals added to scoring should also be added to the SIGNALS_TO_TRACK list in run_weekly_signal_drift_check() in server.py so they get monitored automatically. The audit schedule persists in data/audit_schedule.json and active alerts in reports/audit_alerts.json.

11. Historical Data State

The model's full modern schema — which includes batting_order, recent_ops, and season_ops at the hitter level alongside attack_conf, blended_rating, implied_total, and divergence at the team level — is complete starting from June 24, 2026. Every archive file before that date has some subset of these fields missing. The hitter-level OPS and batting order fields in particular were only wired into the archived output on June 24, so all earlier slates show zeros for those columns. Team-level fields matured earlier: implied_total was present from April 29, attack_conf appeared May 20, and blended_rating was added May 27.

This means the usable historical windows for parameter optimization are different depending on what you are tuning. For team-level work — trap penalty values, bullpen tier breakpoints, signal weight adjustments, or blended_rating thresholds — the window starts May 27, 2026, which as of June 24 gives 21 slates of clean data. That is enough to run a meaningful grid search on team-level parameters and is the basis for the existing backtest calibration report. For hitter-level work — batting order modifiers, recent_ops thresholds, smash factor criteria, or platoon multiplier ranges — the usable window only starts June 24, 2026. As of that date there is exactly one slate of full hitter-level data. Any serious parameter sweep on those dimensions requires waiting for at least 20 to 30 additional slates to accumulate, which at a pace of roughly 5 slate days per calendar week means approximately 4 to 6 weeks of patience before that work is statistically meaningful.

The actuals_cache files in reports/archive/ provide ground truth boxscore outcomes going back to April 15, 2026, with 44 files of coverage as of June 24. These are the paired ground truth for the results archives and are the correct input for any backtest validation. They contain runs scored, starting pitcher stats, and individual hitter boxscore lines per team per slate. Coverage is excellent and the actuals window is actually wider than the results archive window for the same dates.

One important limitation to be aware of is that data/statcast_cache.json is a current snapshot rather than a time-series database. Every time the Savant fetcher runs it overwrites the profile for each player with their current rolling stats. This means you cannot use the cache to reconstruct what a player's rolling OPS looked like on a specific historical date. If a future research task requires knowing a hitter's form at the time a specific archived slate was generated, the only source for that is the results archive file itself, which does capture team_xwoba and rolling signals at lock time.

Two prior research artifacts in reports/ are worth consulting before starting any new parameter optimization work. The file parameter_sweep_results.json contains 100 parameter combinations from a prior optimization run, with the best configuration achieving a joint_score of 1.024. The file backtest_calibration_report.json documents that the most recent calibration improved stack correlation from r=0.077 to r=0.111 and pitcher correlation from r=0.198 to r=0.239, using walk_stack_boost=8.0, er_stack_boost=8.0, pitcher_penalty=-10.0, and true_talent_stack_boost=2.0 as the winning parameters. Both files were generated against the pre-v19.4 model, so once sufficient post-correction slate data accumulates, a fresh parameter sweep against the corrected model is the recommended next research task.
