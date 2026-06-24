1. What this model is

The OMEGA model is a proprietary, end-to-end MLB DFS and sports betting analytics engine specifically engineered for DraftKings Classic contests. Running on Python and hosted on Render, the system provides a web dashboard that the owner uses daily during the MLB season to generate high-upside GPP lineups and identify profitable sports betting edges. The codebase is vibe-coded in a pair-programming loop, leveraging Antigravity for implementation tasks and Claude for high-level architecture decisions and model validation.

2. How the scoring works

Scoring is calculated across three distinct layers. The Physics layer evaluates pure player performance using Statcast metrics like xwOBA, SIERA, and CSW%. The Market layer assesses Vegas implied team totals, Moneyline movements, line divergence, and player prop juice. Physics and Market scores are blended using weights derived from OLS regression on historical backtest data, allocating an 80/20 ratio for stack scoring and a 45/20 ratio for pitchers. Finally, the Decision layer computes a blended rating, defined as the average of the raw score and the attack confidence, which directly feeds the PuLP DraftKings optimizer.

3. Proprietary signals and what makes it different

What sets OMEGA apart are its custom, highly specialized proprietary signals. The DQI triple gate filters out high-variance stacks by checking pitcher form, reliever fatigue, and walk-rate matchups to verify stack safety. The MSMI dual-factor momentum signal tracks hitter performance swings over rolling intervals. The sticky pitcher trap applies a feed-drop persistence logic that identifies pitchers whose recent struggles or high pitch counts make them targets despite favorable baseline stats. The NPAS slate-relative platoon system computes platoon advantages compared to the active slate's averages rather than static baselines. Matchup DNA blends pitcher pitch-mix usage with hitter pitch-type xwOBA to predict matchup-level synergy. The true talent sabermetric penalty adjusts player baselines when Statcast metrics deviate significantly from surface-level results. The Vegas ITT non-linear calibration scales team totals to capture actual runs scored distribution rather than linear expectations. The nightly signal validator and weight proposer automatically tests weights against actual slate outcomes and proposes adjustments. Finally, the doubleheader resolution engine aligns player targets, game times, and game numbers to prevent scheduling errors.

4. What's been backtested and validated

The model has been validated against 48 historical slates of actual game data, yielding critical design insights. The backtest proved that gassed bullpens perform poorly, showing a 60.9% hit rate on 5+ runs against weak bullpens compared to 47.9% against elite pens, which led to a split tiered boost. It also identified a major batting order cliff at spot 5, prompting a steep penalty for hitters batting 7th, 8th, or 9th. Raising the DQI TRUST floor to 80 improved its hit rate from 31.6% to 47.1%, while the top-ranked stack hit its run projections 64.6% of the time. Conversely, several signals were retired after showing negative correlation with success, including the whale flag (r=-0.093), the shark alpha flag (r=-0.088), sneaky premium stacks (r=-0.126), storm alpha weather adjustments, and the qualitative prop pressure labels.

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
