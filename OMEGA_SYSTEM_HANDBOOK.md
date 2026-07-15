# OMEGA System Handbook — v19.4
**Last Updated: June 24, 2026 | Mathematically Corrected Build**

This handbook is the definitive reference for the OMEGA MLB DFS and sports betting analytics engine. Read it front to back once. After that, keep it open as a reference while using the dashboard. When starting a new Claude or Antigravity session, paste this file alongside OMEGA_CONTEXT.md and OMEGA_DECISIONS.md to recover full operational continuity.

---

## 1. What OMEGA Is

OMEGA is a proprietary MLB DFS analytics engine built specifically for DraftKings Classic GPP contests. It is not a projection system. It is a tactical scoring cockpit that combines sabermetric pitch-level Statcast data with sharp betting market signals to identify the highest-upside plays on each slate — and, just as importantly, to identify which plays the field is wrong about.

The engine runs in Python on a Render-hosted Flask server and serves a real-time web dashboard. On every refresh (which you can trigger manually, or which happens on a 15-minute cycle), OMEGA re-ingests live Vegas lines, recalculates all scores, and updates every panel in the dashboard.

As of June 24, 2026 (v19.4), the model has been through a comprehensive mathematical audit and all known correctness issues have been resolved. Specifically: platoon adjustments are applied exactly once per hitter, bullpen fatigue is counted exactly once per team score, no retired signals influence any score, all signal weights are controlled through a single config file (data/weights.json), and the blended_rating metric has exactly one canonical computation point in the codebase. The math underneath now does what the dashboard claims it does.

**Signal Validation Status:**
For the official, up-to-date signal validation accuracy figures and sample sizes backtested across all 53 historical slates (including MSMI momentum signals, platoon adjustments, and stack metrics), refer directly to the canonical signal validation table in Section 4.1 of [OMEGA_CONTEXT.md](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/OMEGA_CONTEXT.md#L16). These figures are audited from the `reports/archive` directory.

Automated weekly drift detection runs every Sunday at 3am ET. If any signal degrades more than 5 percentage points from its 4-week average, the dashboard surfaces an alert on the Learning & Audits page. You will never need to wonder if the model is drifting — the system will tell you.

---

## 2. The Three Scoring Layers

Every entity in OMEGA — every team stack, every pitcher, every hitter — is scored through three sequential layers. Understanding these layers is the foundation for reading every panel in the dashboard.

### Physics Layer

The Physics layer measures pure player and team performance using Statcast data from Baseball Savant. For teams, the key inputs are team_xwoba (expected weighted on-base average, a pitch-outcome metric that strips away luck) and power_concentration (how the team's xwOBA is distributed — a team where three hitters each have .380+ xwOBA scores higher than a team where nine hitters each have .330). These two metrics blend as: `effective_physics = (team_xwoba × 0.4) + (power_concentration × 0.6)`, then scaled to a 0–100 range anchored at .260 (replacement level) to .400 (elite).

For pitchers, the Physics inputs are SIERA (skill-interactive ERA, a defense-independent ERA predictor) and CSW% (called strikes plus whiffs percentage, the single best pitch-quality metric in baseball). Each is scaled to 0–100 independently and averaged. A pitcher at SIERA 3.0 and CSW% 34% scores near the top of the range.

### Market Layer

The Market layer translates sharp Vegas activity into a team or pitcher score. The anchor is the implied team total (ITT), which is extracted from the moneyline and total for each game and scaled from 3.0 runs (minimum viable contest) to 5.5 runs (elite run environment) across a 0–100 range. ITT is the single most predictive market signal the model uses — Vegas books set it using sharper data than any model can independently produce.

On top of ITT, the Market layer adds moneyline movement (ML_MOVE, measured in cents from open to current), total movement (TT_MOVE, measured in runs), and divergence (money percentage minus ticket percentage). Divergence is the sharpest signal in the market layer: when money percentage significantly exceeds ticket percentage, institutional betters are on that side. When it goes the other direction, the public is on it. For pitchers, the market inputs are the pitcher's current win probability (converted from ML) plus K prop positioning.

> [!IMPORTANT]
> **Market Layer & Win Probability Caveat (Zack Wheeler Effect):**
> High-market signals such as `is_sharp`, `is_burst`, and positive `divergence` are calibrated against betting markets. These are primarily indicators of win probability and game outcomes, NOT direct indicators of fantasy point volume. 
> A dominant starting pitcher on the same team (Wheeler Effect) can shorten the game (fewer baserunners, less late-game volume), capping the offensive stack's fantasy ceiling even if they win comfortably.

### Decision Layer

The Decision layer is where Physics and Market combine into the final scores that drive the DK optimizer. For team stacks, the blend is: `score = 40 + (physics_raw × 0.80) + (market_raw × 0.20) + bullpen_boost`. This 80/20 Physics/Market split was derived from OLS regression on historical backtest data — an 8.2:1 optimal ratio, meaning team run scoring is primarily a function of team quality (Statcast) with Vegas amplifying the signal.

For pitchers the split is: `score = 45 + (physics_raw × 0.45) + (market_raw × 0.20)`. Pitchers have a narrower Physics dominance (45%) because win probability from the moneyline carries more weight for pitcher targeting than for stack identification.

After the raw score is computed, the CONF (attack confidence) system runs. CONF compresses the score asymptotically into a [0, 100] range using a rolling series of signal additions and subtractions anchored at 50. Positive signals (DQI_LEVERAGE, is_burst, high ITT, confirmed lineup) add CONF points. Negative signals (is_trap, COLD_STREAK_MSMI, DQI_OVERPRICED, volatile lineup) subtract CONF points. All signal weights are read from data/weights.json so any weight change you make to that file immediately affects model behavior on the next refresh — no code changes needed.

The final output metric is blended_rating: `blended_rating = (score + attack_conf) / 2`. This is the canonical ranking metric. It's what feeds into the DraftKings optimizer's priority ordering. High blended_rating means the model both objectively scores the team/pitcher well AND has high confidence in that score.

> [!NOTE]
> **Same-Side Starter Ceiling Cap:**
> Teams whose starting pitcher has an `attack_conf` \ge 85 receive a soft-ceiling penalty of -5 stack confidence. This acts as a minor fader (primarily a tie-breaker when comparing stacks) to account for game-shortening ceiling cap risk.

---

## 3. The Dashboard — How to Read Every Panel

The dashboard has 13 tabs accessible from the left sidebar. Here is what each one contains and how to use it.

### Command Hub

The entry point. At the top you see snapshot cards showing Today's Slate Date, Total Games, Confirmed Lineups, and Active Signals. Below that is the Live Intel Ticker — a scrolling text bar showing the model's most important findings for the current slate (trap pitchers, ITT outliers, burst teams, DNA convergence alerts).

The SLATE OVERLAY card is important. It shows the model's highest-priority slate-level signal using this priority ladder, top to bottom:

1. **ITT SWAP ACTIVE** — the highest implied-total team has been elevated to the #1 stack rank because the run environment gap between it and the default #1 is more than 0.5 runs. This overrides any CONF-based ranking. The model is saying: run environment matters more than signal convergence when the gap is this large.
2. **Sneaky Lean** — a team with lower public exposure has an unusually strong convergence of Physics, Market, and DQI signals.
3. **NO OVERLAY** — the default ranking by blended_rating is the correct read for this slate, no special adjustment applied.

Below the overlay card you'll see the top-ranked stack, top-ranked pitcher, and today's run environment summary.

### Lineup Cards

A live feed of confirmed and projected starting lineups for every team in the slate. Each hitter shows their OMEGA score, batting order position, and CONF percentage. Color coding: blue for confirmed, grey for projected, yellow for low-confidence projection. The key thing to check here is whether your target stack has CONFIRMED status — a PROJECTED_LOW_CONF lineup adds meaningful uncertainty and CONF is penalized accordingly (-8 points).

### Pitchers Matrix

The core pitcher ranking table. Columns left to right:

- **BLENDED** — the canonical ranking metric (score + attack_conf) / 2
- **OMEGA** — raw alpha score from the Physics + Market calculation
- **CONF** — attack confidence, 0–100
- **PHY** — Physics score (SIERA + CSW%)
- **MKT** — Market score (win probability + ML/TT movement)
- **PROFILE** — signal pills: TARGET (strong anti-trap play), TRAP (sticky trap signal, -30 CONF, fade this pitcher), SHARP (heavy institutional ML money), SHARK (sharp market but independent of model score), SURGING (recent K rate trending up), CEILING (high K upside), LOW_CEILING (suppressed K/outs lines), JUICE (vig-juiced K props worth fading), HAZARD (severe environmental risk flag), PARADOX (elite SP vs elite offense — DNA edge negated), TRUE_TALENT_PENALTY (sabermetric underperformer, surface ERA doesn't reflect actual outcomes), HIGH/MODERATE GPP RISK (two-tier confidence underperformance risk warning)
- **MARKET INTEL** — ML movement direction and magnitude, total movement
- **TACTICAL MATCHUP** — DNA-based assessment of pitch-type matchup quality
- **PITCHER** — name and team
- **vs OPP** — the opposing team and their run-scoring environment
- **PROPS** — K line, K odds, notable prop positioning

The most important column for GPP play is PROFILE. A TRAP pill means the model has detected sticky trap signals (recent struggles, high pitch count trend, metrics diverging from results in a bad direction). Fading a trap pitcher and stacking the opposing offense is the model's highest-conviction single play type, validated at 43% accuracy against a 38% baseline.

### Teams Matrix

The team stack ranking table. This is where you pick your core lineup stack.

The column structure: **RANK** (by blended_rating, with ITT swap override when active), **TEAM**, **BLENDED**, **OMEGA**, **CONF**, **ITT** (implied team total), **DIV** (divergence, money% minus tickets%), **BULLPEN** (fatigue score, 0–100), **DQI** (OVERPRICED/CAUTION/LEVERAGE), **LINEUP** (confirmation status), **SIGNALS** (active signal pills).

Signal pills you'll see on teams:

- **BURST** — star-heavy lineup with exploitable opposing SP or pen. Higher ceiling, higher variance.
- **GASSED** — opposing bullpen fatigue >= threshold. Correlated with extra-inning run-scoring and late blowup potential.
- **HOT RUN** — MSMI hot streak detected. Offense is performing above its baseline over a rolling window.
- **COLD STREAK** — MSMI cold streak. Offense genuinely struggling. Fade even if ITT looks decent.
- **ANTI-CHALK** — contrarian leverage signal. Low public interest, model likes the team, no cold streak active (cold streak gates this signal off automatically).
- **DQI OVERPRICED** — Formerly called DQI_TRUST. Early-confirmed public lineup indicator. Implies that the market has priced this cleanliness to perfection, offering no stacking edge (mild -4 CONF penalty).
- **DQI LEVERAGE** — low-DQI sharp interest (formerly FADE) indicating a high-leverage contrarian target.
- **STEAM** — tightened convergent ML + total steam (requires both moving in consistent directions, single-direction steams no longer qualify after the v19.3 tightening).
- **ITT SWAP** — this team was elevated to #1 by the ITT swap mechanism.
- **VOLATILE** — significant CONF swing on recent lineup update. Verify before locking.
- **TRAP** — team is facing a TRAP pitcher (the opponent is the one getting faded, not this team — this is usually a positive signal for the team's offense).

### Hitters Matrix

Individual hitter rankings by OMEGA score with CONF percentages. Each row shows name, team, batting order position, salary, OMEGA score, CONF, and signal pills.

Hitter signal pills:

- **SMASH** — rolling OPS above season baseline plus good matchup. The 66% validated signal.
- **ELITE PLATOON** — strong handedness edge against the opposing pitcher's dominant pitch mix.
- **HOT RUN** — recent form indicator over rolling window.
- **PITCH ALIGN** — Matchup DNA is aligned (hitter has xwOBA edge on the pitcher's primary pitches).
- **STRONG EDGE** — xwOBA advantage computed from platoon math.
- **COLD WARNING** — COLD_HIGH_BR_WARNING badge; fires when a cold hitter has a high blended rating, indicating significant underperformance risk.

Batting order matters enormously in the model. Spots 1–4 receive full score. Spot 5 gets a modest penalty. Spots 6+ receive escalating penalties based on the batting order cliff discovered in the backtest (steep value drop at spot 7+). This is why two hitters with identical Statcast profiles can have meaningfully different OMEGA scores if one bats 3rd and the other bats 7th.

### Platoon Matrix

The handedness split breakdown for each hitter-pitcher matchup in the slate. Shows vs_left and vs_right OPS, BB%, and K% for each hitter, plus the opposing pitcher's handedness and pitch mix. When Matchup DNA data is available, the platoon adjustments shown here incorporate pitch-type xwOBA rather than just OPS by handedness. When DNA data is missing for a specific hitter or pitcher, it falls back to standard OPS-based splits automatically.

The Platoon Matrix is most useful for identifying which specific hitters in your target stack have the strongest individual edges — useful for picking which hitters from a 9-man stack you want to prioritize in tournament builds where you can't play all 9.

### Weather Matrix

Environmental data for every ballpark on the slate. Columns: Temperature, Wind Direction, Wind Speed, Dome Status, Park Factor, and an environmental risk grade. The model already incorporates weather into scores (park factor is a direct input to both pitcher and stack scoring), so this panel is primarily for your own sanity check — if you see 25mph winds blowing in to home plate and the model has that game's teams ranked low, that's the model doing its job correctly.

### Omega Slate Center

The betting picks panel showing LOCK and LEAN recommendations for each game on the slate. A LOCK is a high-conviction play where multiple sharp signals converge. A LEAN is a moderate conviction play.

**Important calibration note:** As of June 24, 2026, the betting EV engine is uncalibrated. Current backtested ROI is -14.2% on LOCKS (40.4% win rate) and -29.4% on LEANS (35.1% win rate) against a 38% baseline. Do not act on these picks for real money until at least 30 additional calibrated picks accumulate, which will be approximately late August 2026. The engine is designed correctly — it needs more data to find its optimal thresholds.

### ML Betting EV

Sharp money panel tracking institutional moneyline positioning. Shows whale fades (teams where the model's Physics score significantly exceeds their implied probability from the ML) and steam tracking (teams where rapid ML movement suggests sharp action). Use this for confirming or challenging your stack selections, not as a primary signal.

### Vegas Board

Live line movement, consensus splits (money% and ticket%), and total movement for every game on the slate. The Divergence column here is the same divergence that feeds the Teams Matrix — you're seeing the raw numbers that generate the signal pills. A team with -30% divergence (30 points more money than tickets on the other side) is a strong public fade, which can be either an institutional backing of the opposing team or a sign the public is overvaluing the wrong side.

### DFS Optimizer

Upload your DraftKings salary CSV and generate optimized DK Classic lineups. The optimizer runs PuLP linear programming against the OMEGA scores and salary constraints. Parameters you can adjust include minimum CONF floor, salary exposure caps, and stack requirements. The optimizer enforces DK's 2 pitcher + 8 hitter format with the C/1B/2B/3B/SS/3OF structure under the $50,000 cap.

### Learning & Audits

The model's self-assessment panel. Two sections:

**Signal Accuracy Report** — the same data as learning_feedback.md, rendered in the dashboard. Shows hit rate per signal over the trailing 45 days. Any signal below 42% for more than 30 fires triggers a yellow warning. Any signal below 38% triggers a red retire-candidate alert.

**Audit Status** — the three-layer audit cadence tracker showing when the last comprehensive audit ran, when the next one is due, and any active drift alerts from the automated Sunday check. If the sidebar Learning & Audits item has a red dot badge, it means there's an active drift alert that needs your attention. Click into this panel to see which signal is drifting and by how much. Use the Resolve button once you've reviewed an alert.

### Omega Knowledge Base

This handbook.

---

## 4. The Signal Codex — Current Active Signals (v19.4)

This section documents every signal that is live in the v19.4 model. The following signals were retired and do not appear anywhere in scoring, output JSON, or the dashboard: is_whale, is_sneaky (TEAM_SNEAKY_STACK is tracked for historical comparison only, fires no scoring boost), is_storm, prop_pressure_label (display only in tooltips, zero scoring weight).

### Pitcher Signals

**TRAP** — The model's most actionable fade signal. Fires when a pitcher shows multiple concurrent signs of deteriorating performance: recent high pitch counts, declining velocity, walk rate trending up, and metrics diverging negatively from surface ERA. Validated at 43% accuracy over 159 fires (vs 38% baseline). CONF penalty is -30 points (config-driven via weights.json `pitchers.is_trap`). When you see a TRAP pitcher, the correct response is to fade them and stack the opposing offense. The opposing team's stack score gets a separate boost because the TRAP designation shortens the effective projected outs (to 15.5), which in turn increases the bullpen fatigue multiplier for that team.

**LOW_CEILING** — Pitcher whose K/9 and projected outs metrics suggest he will not go deep into the game or generate the high-strikeout output needed for SP1 DFS value. Safe pitcher for opposing stacks, poor target for SP in your own lineup.

**HAZARD** — Severe environmental risk. Either extreme weather, extreme park factor, or a matchup with historically poor outcomes. Hard pass as an SP target.

**TARGET** — The anti-trap. A high-Physics pitcher in a favorable matchup environment with no negative momentum signals. These are your SP anchor plays.

**SHARK** — Market-detected institutional interest, independent of the model's Physics score. Sharp money moved this pitcher's line. Can coexist with any Physics score — use as a tiebreaker between two similar Physics plays.

**SHARP** — Heavy institutional ML money (is_sharp signal). Requires a directional ML move of meaningful magnitude. Stronger signal than SHARK because it reflects win-probability pricing, not just line movement.

**PARADOX** — Elite SP facing elite opposing offense. Resolves within-game team selection using an ITT-first hierarchy: (1) higher ITT wins, (2) momentum signals (`is_burst`, `is_hot_run_msmi`) as the first tiebreaker, (3) bullpen fatigue as the second tiebreaker, and (4) raw xwOBA only as the final tiebreaker. Useful for identifying game stacks (fading your own pitcher's K upside).

**SURGING** — Recent K rate trending upward over rolling window. K prop may be underpriced. Good indicator the pitcher is in peak form.

**CEILING** — High K upside pitcher whose K line may be worth targeting from the over side. Useful for the Omega Slate Center betting picks context.

**JUICE** — K prop has unusually high vig attached, indicating the book knows this line is sharp-sharp. Fading juiced K props has positive EV historically. See as a warning not to take the K prop at face value.

**TRUE_TALENT_PENALTY** — Sabermetric underperformer flag. This pitcher's surface ERA is significantly better than what SIERA/FIP predict as sustainable. The model discounts their Physics score accordingly. Useful for identifying regression candidates.

**GPP RISK TIERS** — A two-tier confidence warning system for pitchers. Pitchers with `attack_conf` 55–70 carry a **HIGH GPP RISK** flag (43.2% underperformance rate on 125 starts). Pitchers with `attack_conf` 70–79 carry a **MODERATE GPP RISK** flag (34.6% underperformance rate on 52 starts). Pitchers with `attack_conf >= 80` receive no risk badge (24.4% underperformance rate). These warnings are surfaced as badges in the dashboard and ASCII alerts in the optimizer output. In single-entry GPP contests, do not roster a HIGH GPP RISK pitcher unless no better option exists at that salary.

**is_high_variance** — Pitcher with high start-to-start fantasy scoring volatility (std >= 8.0 or std/mean >= 0.5 over season starts). Low confidence fades (CONF <= 25) on these pitchers are labeled **VOLATILE FADE** (potential tournament leverage due to high ceiling), whereas low-variance low confidence pitchers are labeled **SOLID FADE** (high conviction fades).

**walks_suppression** — Control gate that suppresses the Walks Penalty for control starters who are in peak recent form (recent L3 BB/9 < 3.2 and season BB/9 < 3.8). Audited across all archived slates to shield control starters from slow-adjusting prop lines.

### Opener Detection System
OMEGA uses a multi-tier opener detection system to prevent starting pitcher projections from being applied to low-inning relief openers. The system features a **Tier 1 hard override**: any starting pitcher with a strikeout prop line `k_line <= 1.5` is automatically classified as an opener, with no secondary signals required. For pitchers above this threshold, secondary triggers (salary gaps, CSV tags, and outs lines) are evaluated. When an opener is detected, the model adjusts the projected outs and scales opponent stack projections accordingly.

### The Short-Leash Pitcher Cap (Fix B)
When facing a short-leash starting pitcher (a trap scenario), the model applies a strict confidence cap of 75 (Fix B) on the opposing team's stack. A proposed modifier to relax this cap when the opposing bullpen is gassed was **formally backtested and rejected on June 28** (0-for-4 teams scored 5+ runs in gassed-pen short-leash scenarios). The Fix B cap of 75 holds unconditionally, regardless of opposing bullpen fatigue, and will not be revisited until sample size exceeds 15 additional instances.

### Team / Stack Signals

**FADE_RISK** — Implied total fade signal. Fires when the betting market indicates a team's ITT is artificially inflated. `FADE_RISK` alone shows a **66.7% ITT underperformance rate** (18 instances). When combined with negative divergence (`DIV < -15`), the underperformance rate rises to **76.9%** (13 instances). This combo is the strongest fade signal in the model and should be treated as a near-certain team avoidance in lineup construction. Note: sample size is currently 18 — flagged for July audit when sample reaches 40+.

**ITT SWAP ACTIVE** — The highest-implied-total team has been elevated to #1 stack rank because the gap between it and the default #1 is more than 0.5 runs. Run environment is the most predictive single variable for team run scoring. When one team's ITT is meaningfully higher than everything else on the slate, that is the right #1 stack regardless of what CONF says. Trust the swap.

**BURST** — Star-heavy lineup with exploitable SP or pen conditions. High ceiling but higher variance than a vanilla high-ITT stack. Best in tournament builds where you need differentiated upside.

**GASSED_BULLPEN_ATTACK** — The opposing bullpen's fatigue score has crossed into meaningful territory. The stack score gets up to +25 points of bullpen boost (sliding scale, starts building at 65% fatigue). Validated at 48% accuracy over 106 fires. Note that after the v19.4 triple-stack correction, the is_gassed_attack premium (post-bullpen premium on top of the base bullpen_boost) is halved to +2/+4/+6 at three fatigue tiers, and the BURST beta_signal double-count was removed. The signal is real; the magnitude is calibrated correctly now.

**TEAM_COLD_STREAK_MSMI** — The offense is genuinely struggling over a meaningful rolling window. Even if ITT looks okay, fade this team for stacking. Validated at 69% accuracy over 16 fires, meaning when this fires, the team fails to hit 5+ runs 69% of the time. The Cold Streak signal also gates ANTI_CHALK_SMASH — a team can't be contrarian leverage if they're actually cold.

**TEAM_HOT_RUN_MSMI** — The offense is outperforming its rolling baseline. Positive confirmation for already-good Physics teams. Not a standalone signal — look for it as an additional factor on teams you're already targeting.

**ANTI_CHALK_SMASH** — Contrarian leverage play. Low public exposure combined with decent Physics and no cold streak active. The model likes the team, the field doesn't. Best for millionaire-style tournaments where differentiation matters. Explicitly gated: does not fire CONF boost or score boost when TEAM_COLD_STREAK_MSMI is active on the same team.

**DQI_OVERPRICED (DQI_OVERPRICED)** — Formerly called DQI_TRUST. Early-confirmed public lineup indicator. Implies that the market has priced this cleanliness to perfection, offering no stacking edge. Stacks with this status hit or exceed implied totals only 30.0% of the time (N=20, p=0.1835) and underperform implied totals by -0.80 runs. Applies a small, conservative -4 CONF penalty.

**DQI_LEVERAGE (DQI_LEVERAGE)** — Low-DQI sharp interest (formerly FADE) indicating a high-leverage contrarian target. Stacks with this status hit or exceed implied totals 72.7% of the time (p=0.0074, N=22) and score +1.38 runs above expectations. Validated as a strong positive GPP selector due to public avoidance and strong actual run output.

**STEAM_SUPPORT** — Tightened convergent steam signal. Requires ML and total movement to be directionally consistent (both showing the same team as the play). Single-direction steam no longer qualifies after the v19.3 tightening. Validated at 48% accuracy over 33 fires. Good confirmation signal, not a primary trigger.

**slate_compression** — Fires a **Low Differentiation Warning** banner when the standard deviation of the top 6 stack confidence scores is < 5.0. This indicates a high-scoring but highly compressed run environment where the model cannot discriminate between the top options. Selection must pivot heavily to GPP ownership, game totals, and platoon/radar alignment.

### Hitter Signals

**SMASH (HITTER_SMASH)** — The hitter's rolling OPS is above their season baseline AND the matchup environment is favorable (good park, low pitcher ceiling, favorable platoon). Validated at 66% accuracy over 715 fires. Note: the 66% represents matchup quality rather than contrarian edge — this is the correct plays-in-good-spots signal, not a fade-the-field signal. Use it for identifying which hitters in your target stack deserve full exposure.

**ELITE_PLATOON** — Strong handedness advantage. The hitter has a significant OPS edge against this pitcher's handedness, validated by split data. When DNA data is available, this upgrades to a pitch-type xwOBA edge.

**HOT_MSMI (HOT_RUN)** — Formally validated buy signal. Fires when a hitter shows positive recent form over a rolling window. Worth approximately **+2.11 DFS points above projection on average** (based on 780 instances across 53 historical slates). Gated by a **2% tolerance band** check: if rolling or recent L7 OPS is below the season baseline by > 2% (`rolling_ops < season_ops * 0.98` or `recent_ops < season_ops * 0.98`), the signal is deactivated. Treat as a positive selector when choosing between similarly priced hitters.

**COLD_HIGH_BR_WARNING** — Hitter avoidance flag. Activates when `is_cold_streak_msmi = True` AND `blended_rating >= 80` fire simultaneously. Backtests show a **54.8% underperformance rate** on 31 instances with a significant negative DFS delta compared to other hitters. Hitters with this flag active should not be rostered under any circumstances, regardless of raw blended rating. The warning appears as a red `COLD WARNING` badge in the dashboard and an ASCII warning in the optimizer terminal output.

**PITCH_ALIGN** — Matchup DNA is aligned. The pitcher's primary pitch types are ones this hitter handles above average. This is the DNA system's most direct hitter-level output.

**STRONG_EDGE** — xwOBA advantage computed from platoon math against this specific pitcher. Quantifies the platoon edge in expected outcomes rather than just handedness.

---

## 5. The Matchup DNA System

Matchup DNA is OMEGA's deepest proprietary edge and the system no public DFS tool replicates. The fundamental insight is that "lefty vs righty" OPS splits are too coarse to identify real matchup advantages. What actually matters is whether a hitter is good against the specific pitch types a pitcher throws most often.

### What the DNA Pipeline Does

Every Sunday at 2am ET, the Savant fetcher pulls real Statcast CSV data from Baseball Savant. It builds two databases: a pitcher arsenal breakdown (for each pitcher, what percentage of their pitches are 4-seam fastball, slider, curveball, changeup, cutter, sinker, etc.) and a hitter pitch-type xwOBA database (for each hitter, their expected weighted on-base average against each pitch type). The current database contains 930 pitchers and 543 hitters.

The output for any specific matchup is a pitch-weighted blended xwOBA. If Pitcher A throws 45% 4-seamers and Hitter B has .420 xwOBA against 4-seamers, that's a dominant edge on the pitcher's own primary weapon. If Hitter B also has strong numbers on the slider and curveball that make up another 40% of the pitcher's arsenal, the blended DNA xwOBA will be significantly above the handedness-only baseline.

### How to Read the DNA Radar Chart

When you click into a hitter's detail view and navigate to the Matchup DNA tab, you see a radar chart with two overlapping polygons. The blue polygon shows the pitcher's pitch usage percentages — how often each pitch type appears in their arsenal. The green/red polygon shows the hitter's xwOBA edge on each pitch type versus league average. Green sectors indicate edges greater than 10% above league average. Red sectors indicate weaknesses greater than 10% below league average.

The most actionable configurations: when large blue sectors (the pitcher uses that pitch a lot) align with large green sectors (the hitter crushes that pitch), you have a DNA convergence play. The pitcher is throwing their primary weapon directly into the hitter's wheelhouse. When large blue sectors align with red, the pitcher has a real dominance advantage and you should reconsider this hitter even if the OPS splits look fine.

For example: if a pitcher throws 50% 4-seam fastballs and the hitter has .480 xwOBA against 4-seamers (large blue sector, large green sector), that is a DNA convergence play. If the pitcher's secondary pitches are also green, you have a near-perfect matchup that no OPS split would fully capture because OPS splits aggregate all pitch types together.

### How DNA Feeds Into Scoring

When DNA data is available for both the pitcher and the hitter, the system replaces the standard OPS-based platoon multiplier with the DNA-blended xwOBA in the hitter's individual score calculation. This means the platoon adjustment is no longer just "this hitter has .290 OPS from the left side against righties" — it becomes "this hitter generates .340 expected wOBA on the specific mix of pitches this specific pitcher throws." The precision improvement is material.

When either the pitcher or the hitter lacks DNA data (debut pitchers, recently called-up players, data refresh lag), the system falls back to standard OPS-based platoon math automatically. You won't see an error — the model gracefully degrades to the less precise but still valid baseline.

---

## 6. The Decision Workflow — How to Use OMEGA

This is the strategic guide. The model does its job automatically. Your job is to read the cockpit and execute with discipline.

### Step 1 — Eliminate

Before you think about who to play, identify who not to play. Open the Pitchers Matrix and look for every TRAP pill. Write those pitchers down as fades. Open the Teams Matrix and note every COLD_STREAK pill. Those teams are not stacking candidates today regardless of what the public thinks. Open the Hitters Matrix and note which low-batting-order hitters are showing up — spots 7–9 in a high-ITT stack are still worth playing, but spots 7–9 in an average-ITT stack with PROJECTED lineup status are avoids.

### Step 2 — Find Your Game Environment

Look at the top 4 teams in the Teams Matrix. If ITT SWAP ACTIVE is showing, the #1 team is there because it has the highest run environment. If no swap, the top teams are ranked by blended_rating. Your candidate universe for the slate is typically the top 3–4 teams after eliminating any with COLD_STREAK or VOLATILE.

### Step 3 — Check for Leverage

For each candidate stack, cross-reference their ticket_pct in the Vegas Board. The team with the lowest public interest AND a high CONF score AND no negative signals is your GPP leverage play. This is especially powerful when DQI_TRUST fires alongside low ownership — the model is confident and the field isn't paying attention. Use the DNA radar chart to confirm that your specific hitter targets from that stack have edges against the opposing pitcher's arsenal.

### Step 4 — Build Around It

Pair your primary stack (ideally 4–5 hitters from one team) with one of the top 3 pitchers from the Pitchers Matrix (66% QS accuracy). If your primary stack pitcher is on one of the top 3 teams, that's a legal same-team stack on DraftKings and can actually be optimal when DQI_TRUST confirms the stacking logic. Fill remaining spots with hitters from your secondary stack or the top individual hitters from the Hitters Matrix (75% smash accuracy on the top 5).

### Step 5 — Lock and Don't Second-Guess

Once you've used the framework to build the lineup, trust it and submit. The model's accuracy is statistical — it works over 30 slates, not necessarily on any individual slate. On days when the model is wrong, it is usually wrong because something unexpected happened (injury, weather change, line move post-lock). That's not model error, that's sports variance. Do not let one bad slate change the framework. The framework is correct.

---

## 7. Three Professional GPP Strategies

These three strategies represent the clearest paths to tournament equity using OMEGA.

### Strategy 1 — The TRAP-Pivot Sweep

Identify a high-owned TRAP pitcher (a popular name with a TRAP signal, likely because the public is anchoring to a good recent start or name recognition). Fade him. Find a different SP in the same price range with a TARGET or CEILING signal and a comparable Physics score. Stack the TRAP pitcher's opposing offense (they'll be underowned because the public picked the wrong pitcher to fade, so they'll be fading that team). You now have differentiated exposure with the model on your side: 43% of the time the TRAP pitcher blows up, you're uniquely positioned to capture that ceiling.

### Strategy 2 — The Bullpen Exhaustion Exploit

Find a game where the GASSED signal is active on a team's opposing bullpen (high fatigue score, ideally 80+). Stack that team at any lineup confirmation status — the bullpen exhaustion signal fires because the pen will be deployed early and often regardless of who starts. Layer in a secondary mini-stack from the same game if the game total is high (this creates natural game-stack correlation between two teams both benefiting from a run-heavy environment). Validated at 48% hit rate — above baseline without requiring any other convergent signals.

### Strategy 3 — The DNA Convergence Play

This is the rarest and most valuable setup in OMEGA. You need four conditions to converge: DQI_TRUST firing on the target team, ANTI_CHALK_SMASH active (low public ownership), a DNA radar chart showing multiple green sectors on primary pitches for the hitters you want to play, and an ITT of at least 4.8. When all four align, you have what tournament DFS calls a "leveraged correct play" — the model likes it, the pitch-level math confirms it, and the field isn't on it. This is the play type that wins the big tournaments, not because it wins more often, but because when it wins, you win alone at the top of the leaderboard.

---

## 8. The Mathematical Guarantees — Post-June 24 Audit

The June 24, 2026 audit resolved all known mathematical correctness issues in the model. Here is what the v19.4 model now guarantees:

**Single platoon application.** The platoon multiplier is applied exactly once per hitter in calculate_individual_hitter_score(). Before the fix, xwOBA was pre-multiplied by the platoon factor before being passed into the scoring function, which then applied a second platoon-based adjustment internally. This inflated elite platoon hitters by 5–15%. Corrected.

**Single bullpen signal count.** GASSED_BULLPEN_ATTACK previously fired in three independent places: the bullpen_boost additive in stack scoring (+up to 25 pts), the is_burst beta_signal gate (which doubled with pen pressure), and the is_gassed_attack premium in final_omega scoring. A team facing a 90-fatigue pen could receive +40–50 false score points from one underlying signal. After the fix: bullpen_boost is capped correctly, the beta_signal double-count is removed, and the gassed_attack premium is halved. The signal is real. The magnitude is now correct.

**No retired signal influence.** is_whale, is_sneaky, and is_storm were computed on every run but contributed no scoring in the official model. However, they cluttered the output JSON and created badge confusion in the dashboard. All three are now fully removed from scoring, output, and dashboard rendering.

**Config-driven weights.** Every CONF signal weight in the model is read from data/weights.json on each run. Before the audit, the pitcher trap penalty was hardcoded as -30 in attack_confidence.py regardless of what weights.json said. Any future weight tuning you do in weights.json now actually affects model behavior.

**Single blended_rating computation.** Before the audit, blended_rating was computed in four separate locations (slate_report_generator.py, main.py, dashboard_generator.py, and server.py) with slightly different formulas. The canonical source is now exclusively main.py's post-generate() block. One formula, one location, written once, read everywhere. A sequencing bug where the report generator read blended_rating before it was written was also fixed using an inline _compute_blended() helper.

**ITT swap protects stack #1.** When the highest-ITT team is not the default #1 ranked stack and the ITT gap is more than 0.5 runs, the swap mechanism elevates that team to the top. Run environment is the most empirically predictive variable for team run scoring. The swap ensures the model's most actionable recommendation reflects that reality.

**Stacking diminishing returns (Item 4).** Trailing 54-slate study of 220 team explosions (Runs >= ITT + 2.0) shows that combined stack score scales strongly from 2-man (23.80 avg) to 5-man (55.66 avg) configurations. However, the marginal contribution per added hitter exhibits a real ~13.5% decay: H1/H2 averages 11.90, H3 adds 10.92, H4 adds 10.65, H5 adds 10.29. Additionally, zero-sum cannibalization of runs and RBIs reduces the joint probability of all 3 top hitters simultaneously hitting 15+ ceilings to 2.24% (a 0.65x multiplier vs independence). Thus, while 4-man and 5-man builds are GPP optimal to capture total volume, 2-man and 3-man mini-stacks represent highly viable contrarian leverage pivots when large stacks carry excessive ownership.

---

## 9. The Audit Cadence System

OMEGA maintains its own health through a three-layer system that requires minimal manual oversight.

**Layer 1 — Weekly automated drift detection.** Every Sunday at 3am ET, the nightly maintenance loop runs run_weekly_signal_drift_check(). It reads reports/learning_feedback.json (current week's signal hit rates) and compares against the previous four Sunday's archived feedback files in reports/archive/feedback_*.json. Any signal that has drifted more than 5 percentage points in either direction triggers an alert written to reports/audit_alerts.json. The dashboard Learning & Audits page surfaces this alert immediately. No human action required unless an alert fires, at which point you should review the signal's behavior and decide whether to adjust weights.json or formally retire the signal.

**Layer 2 — Monthly comprehensive audit.** Every 30 days, run a full 8-phase audit covering: math correctness, data flow integrity, signal interaction analysis, config consistency, test coverage gaps, dead code inventory, dashboard binding verification, and architectural smell review. The Antigravity prompt for this audit is standardized and has been used successfully. After completing it, click Mark Complete in the Audit Status card to reset the 30-day timer.

**Layer 3 — Ad-hoc focused audit.** After shipping any significant new feature or refactor, run a focused audit on just that area within 48 hours. The June 24 session itself (a blended_rating consolidation) produced the blended_rating sequencing bug that was caught and fixed the same night — exactly the kind of thing a focused post-ship audit catches.

The audit schedule persists in data/audit_schedule.json. The red dot badge on the Learning & Audits sidebar item is visible from any tab — you will never miss an overdue audit.

---

## 9. Backlog: Pitch-Mix vs. Opponent Contact Profile Matchups

The system includes a backlog item to model the direct interaction between a pitcher's pitch-mix arsenal (Savant) and the opposing team's contact/chase profiles.

### Architecture Scoping:
- **Pitcher Primary Weaponry:** Extracted from `data/matchup_data.json` pitchers' arsenal (e.g. Sinker usage \ge 30%).
- **Opponent Profile:** Compiled from opposing team plate-discipline metrics or averaged from the projected starting lineup's hitter stats.
- **Matchup Alignment:** Flag matchups where a high-contact, low-discipline, or low-walk lineup (Z-Contact% \ge 85%, BB% \le 7.0%, O-Swing% \ge 33%) faces a contact-heavy, low-strikeout pitcher (e.g., sinker-heavy arms). This alignment reduces pitcher confidence and boosts stack confidence.

---

## 10. Final Summary — The OMEGA Mindset

OMEGA is not a passive projection list. It is an active tactical cockpit.

Every panel in the dashboard is answering a specific question. The Pitchers Matrix answers: who should I start and who should I never touch? The Teams Matrix answers: where is the highest expected run environment and who agrees with me? The Hitters Matrix answers: which individual hitters in my target stack have the strongest individual edges? The DNA radar chart answers: is this specific batter vs pitcher matchup as good as the team-level signal suggests?

The model's strongest single use is telling you who NOT to play. Every TRAP pitcher you correctly fade and every COLD_STREAK team you correctly avoid moves the needle more than any single correct "target" call. Avoiding mistakes is the foundation. Finding the upside is the superstructure.

The second strongest use is identifying where the field is wrong about the highest-scoring team. When ITT SWAP ACTIVE fires, the public is typically underweighting that team because it's in a small-market game or the pitcher matchup doesn't look sexy. But run environment is run environment. ITT 5.4 is ITT 5.4 regardless of whether it's Yankees vs Red Sox or Royals vs Tigers.

The third and most powerful use is the DQI_TRUST convergence play: DQI_TRUST plus low ticket_pct plus DNA green sectors on primary pitches. This is the millionaire tournament scenario — the play that wins the contest because you're the only one who saw it.

The math is correct. Trust the TRAP fades. Hammer the DQI_TRUST + low-ownership + DNA edge convergence.

Let's win this thing.

---

*OMEGA v19.4 | Mathematically Audited June 24, 2026 | 114/114 tests passing*
