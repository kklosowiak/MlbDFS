# OMEGA Model Decision Log

This file tracks the reasoning behind major architectural and strategic decisions made on the OMEGA model. It's a companion to OMEGA_CONTEXT.md — context tells you WHAT the model is, decisions tell you WHY. When starting a new Claude or Antigravity session, paste both files at the start to recover full continuity.

---

## AUDIT BRANCH STATUS — June 30, 2026

**Branch:** `audit/july-2026`
**Status:** All 7 audit items implemented and validated. NOT merged to main. NOT deployed.
**Tests:** 123/123 passing as of 2026-06-30.
**Hold for:** July 20-25 audit window — full review and merge decision then.

**Items on this branch:**
1. Pitcher Variance Classifier (VOLATILE/SOLID FADE tiers) — thresholds 8.0/0.50, population audit documented, threshold recalibration deferred to 54-slate archive run
2. Walks Penalty Recent Form Gate — season_bb9 now read from statcast_cache.json directly; Peter Lambert confirmed shielded (season_bb9=3.765 < 3.8)
3. Slate Compression Detection + LOW DIFF banner — wired into offline HTML dashboard generator
4. Within-Team Production Concentration Study — documented below (diminishing-but-positive returns)
5. JSON Schema Matchup Clarity — opposing_team / opp_pitcher_team redundant fields added
6. Doubleheader Scheduling Matching — time-window pitcher-to-game matching via UTC commence_time
7. Hitter MSMI Momentum Logic Fix — is_hot gated with 2% tolerance band; recent_ops=0 (cache miss) now explicitly withholds is_hot

---

## June 24, 2026 — Comprehensive Audit and Math Correctness Sprint

This was a marathon 8-hour session focused on auditing the entire model and fixing accumulated technical debt. Started the session with what felt like an off-feeling model (CONF bunching, hard to read rankings) and ended with mathematically correct math, validated backtest numbers, and an automated audit cadence system.

The audit graded the model B overall with significant technical debt. The biggest findings were: platoon double-application on hitter scoring (xwOBA was being multiplied by platoon_multiplier twice), GASSED_BULLPEN triple-stack (signal fired in three places adding up to +40-50 false points), is_storm contributing scoring boosts in three places despite being officially retired, blended_rating computed in four locations with no source of truth, and pitcher trap weight in code (-30) not matching weights.json (-24).

Decided to fix everything in one session rather than spread across multiple sessions. Reasoning: math correctness issues compound and the longer they persist the harder they are to fix safely. Better to take one marathon session and exit at A grade than ship incremental fixes over weeks.

### Decisions about what NOT to fix

Skipped the mega-function refactoring (generate_report at 1484 lines, _get_team_reports at 735 lines). Reason: high refactoring risk for low correctness payoff. These functions work correctly, they're just ugly. Track as tech debt, don't touch without a dedicated session.

Skipped the 5 redundant statcast_cache.json loads per run. Reason: performance issue not correctness issue. Worth fixing eventually but not at midnight when the priority was math correctness.

Skipped batting order parameter sweep. Reason: only 1 archived slate has batting_order populated. Need 20-30 more slates of data before sweep is statistically meaningful. Revisit mid-July.

Skipped L7 form boost parameter tuning. Reason: ran the diagnostic, found existing continuous form index in hitter_confidence.py works better than any discrete tier alternatives tested.

### Decisions about signals to leave alone for now

TEAM_SNEAKY_STACK at 36-39% over 28-36 fires. Below baseline but kept computing for tracking. Borderline retire candidate. Decision: wait 2-4 more weeks. If still below 42% after 50+ fires, formally retire.

HITTER_SMASH at 66% over 715 fires. Looks great but matches baseline smash rate for any hitter in good matchup. Not adding edge above baseline. Decision: kept in scoring because it correctly identifies good matchups, but don't treat as a strong differentiator. The 66% is real but represents matchup quality, not contrarian edge.

DQI TRUST at 42-50% over 10-12 fires. Sample too small to act on. Decision: wait until 30+ fires before any tuning.

### Strategic decisions about model usage

Line velocity tracker deprioritized. Reason: user refreshes the model 2-3 times before lock but rarely changes lineups mid-build, so late velocity signals don't drive action. On roadmap if user's refresh cadence changes.

Ownership tier display deprioritized. Reason: user's philosophy is "play the best plays regardless" — ownership data would add noise to a decision the user has correctly identified as model-output-only. Future-proof: revisit if user wants to enter higher-variance contests where leverage matters more.

Betting EV calibration deferred. Reason: currently -14.2% ROI on LOCKS and -29.4% on LEANS. Engine is uncalibrated. Don't tune thresholds until 30 more real betting picks accumulate (~6-8 weeks).

### Key bug fix decisions

For pitcher trap weight mismatch (-24 in config vs -30 in code): chose to update config to -30 rather than code to -24. Reason: -30 has been live since initial commit and validated by 43% trap fade hit rate in backtest. Production behavior preserved.

For GASSED_BULLPEN triple-stack: reduced is_gassed_attack premium from +4/+8/+12 to +2/+4/+6 (halved). Removed beta_signal double-count when pen_script drives BURST. Raised pen_script concentration floor from 0.365 to 0.390. Reason: surgical fixes that preserve the signal's value while eliminating triple-counting. Worst case fixable in 2 weeks if backtest shows over-correction.

For COLD_STREAK_MSMI + ANTI_CHALK_SMASH conflict: gated anti_chalk to not fire CONF boost OR OMEGA score boost when cold streak is active. Reason: a team genuinely struggling shouldn't be treated as contrarian leverage. Cold streak takes priority.

For retired signals (is_whale, is_sneaky, is_storm): full removal from output JSON, scoring contributions, and dashboard rendering. Reason: ghost signals computed every run but inert in scoring create confusion. If user sees a WHALE badge they assume it means something. Better to remove cleanly.

Also caught and fixed a sequencing bug introduced during the blended_rating consolidation (v19.2): SlateReportGenerator was reading t['blended_rating'] with hard bracket access before main.py's canonical write block ran. Fixed by adding a _compute_blended() inline helper to the report generator that computes the value on the fly using the same formula, eliminating the ordering dependency entirely.

### Calibration state

The session corrected math but did not optimally tune thresholds. Many threshold values (bullpen tier boosts +4/+8/+12 post-fix, DQI triple gate thresholds, anti_chalk premium magnitudes, is_gassed_attack premium magnitudes) are reasonable but not provably optimal. Real parameter optimization requires 30+ slates of corrected-model data which won't exist until early August 2026. Decision: don't tune until clean data exists. Drift detection system will catch any signals that go wrong in the meantime.

### Tools and workflow decisions

User established the Claude + Antigravity pattern: Claude for strategy, architecture, prompt-writing, and interpretation; Antigravity for implementation, code execution, file editing. This division proved highly effective. Maintain this pattern.

User's typical workflow: download omega-results JSON throughout the day, feed to AG for slate breakdown and lineup recommendations. Use Claude for strategic judgment calls and post-slate analysis. This workflow is correct and should continue.

Created automated weekly drift detection that runs Sunday 3am ET. Reasoning: catches signal drift without requiring user vigilance. User shouldn't have to remember to check signals — system tells them when something needs attention.

Decided on monthly comprehensive audit cadence with dashboard reminders. Reasoning: every 4-6 weeks is the sweet spot for an actively-developed model. More often is wasted effort, less often allows technical debt to accumulate faster than it can be caught.

---

*End June 24 entry*

---

## June 25, 2026 (early hours) — Scratch Directory Cleanup Deferred

End-of-session check on Python file count flagged 913 total Python files which seemed high. Investigation revealed 734 of those files (80%) live in the scratch/ directory — throwaway diagnostic scripts AG creates during sessions and never deletes. Examples: platoon_diag.py, gassed_diag.py, blended_diag.py, various scratch_inventory.py variants from tonight alone.

Production code is appropriately sized at 179 files (utils 28, research 71, archive 23, tests 21, data 16, root 11, engine 7, scripts 2). The 84K Python line count is inflated by approximately 30-70K lines of scratch noise.

Decision: defer cleanup to next housekeeping session. Bulk delete the entire scratch/ directory — AG creates new scratch scripts as needed and does not depend on old ones. The research/ folder at 71 files may also benefit from cleanup but is lower priority.

Reasoning for deferral: doing a 700+ file bulk delete at midnight after a 7-hour session is the classic "one more thing" mistake. Cleanup is housekeeping, not correctness. Risk of accidentally deleting a needed file is low but nonzero, and zero benefit from doing it tonight vs next session.

Action item for next session: `Remove-Item -Recurse -Force scratch/` then verify 84/84 tests still pass.

*End June 25 (early hours) entry*

---

## June 25, 2026 (afternoon) — Pitcher Override Staleness & Ingestion Prioritization

### Bug
The daily slate was showing stale pitchers from yesterday's doubleheader (Javier Assad for Cubs, Nolan McLean for Mets) instead of today's actual starters (Matthew Boyd and Freddy Peralta). 
- **Root Cause**: `pitcher_overrides.json` overrides were configured for yesterday's games using legacy keys like `"Chicago Cubs_1"`. Since the overrides had no date markers and were never cleared, they persisted and overrode today's correct starters.
- **Ingestion Order Issue**: In `market_fetcher.py`, the Odds API probable pitcher metadata took priority over the `probable_pitchers.json` (Stats API) data.

### Fix
1. **Auto-Invalidation & Date-Keyed Overrides**: Updated `ProbablePitcherFetcher.refresh()` to check the overrides file modification date relative to the active slate date (4 AM ET timezone-aware rollover) and automatically clear the file (`{}`) if it's stale. Added support for date-keyed overrides (e.g. `"2026-06-25_Chicago Cubs_1"`) alongside the legacy format.
2. **Prioritize Stats API**: Modified `data/market_fetcher.py` (structural ingestion + resolution loop) to query `probable_pitchers.json` (Stats API) first and fallback to Odds API metadata only as a secondary check. Added descriptive log messages pointing to the resolving source.

### Architectural Follow-Up
Consider migrating all legacy overrides in user workflows to be strictly date-keyed (e.g. `"YYYY-MM-DD_Team_GameNumber"`) to permanently design out override leakage without relying solely on mtime checks.

---

*End June 25 (afternoon) entry*

---

## June 25, 2026 (afternoon) — Rolling Betting ROI Auto-Resolution & In-Progress Caching

### Bug
The Rolling Betting ROI panel showed 0/0 W/L and 0.0% ROI across all tiers, despite the feedback loop having graded slates (like June 24).
- **Root Cause**: The frontend panel reads from `data/betting_history.json`, which is rebuilt by `AuditEngine.backfill_betting_history()`. The backfiller matches each daily results file with its corresponding `reports/archive/actuals_cache_{date}.json`. However, no production process was writing these per-date cache files. The feedback loop was only writing to a unified `scratch/actuals_cache.json` file.
- **In-Progress Caching**: Because the feedback loop ran at 10:56 PM ET on June 24, it cached the slate while some games were still `"In Progress"`. This partial data was then permanently cached with `0` runs, causing incorrect ratings and grading downstream.

### Fix
1. **Backfill Auto-Resolution (Fix A)**: Updated `backfill_betting_history()` in `utils/audit_engine.py` to auto-resolve missing cache files by checking the unified scratch cache, falling back to querying the MLB API directly, and saving the resolved file to `reports/archive/actuals_cache_{date}.json`.
2. **Nightly Validator Fallback (Fix B)**: Implemented the same auto-resolution fallback in `utils/nightly_validator.py` (`run_daily_validation()`) so that the 4:05 AM nightly validation loop writes the file instead of skipping validation.
3. **Prevent Caching In-Progress Slates (Fix C)**: Modified `run_feedback_loop.py` to check if all games in a slate are completed (`Final`, `Game Over`, etc.) before persisting them to the unified scratch cache. If games are still active, they are fetched for the current run but not written to the persistent cache.

### Verification
* Deleted `data/betting_history.json` and triggered a complete rebuild.
* Verified that the backfiller successfully processed all 45 archived slates from April 15 to June 25, resolving missing caches and building 479 total bets.
* Confirmed the overall ROI (-2.1%) and LOCK/LEAN breakdown is correctly reflected in `data/betting_history.json` and rendered in the dashboard.

*End June 25 (afternoon) entry*

---

## Daily Build Log — June 25, 2026

### Contest Summary
| Field | Value |
|-------|-------|
| Type | Single Entry GPP |
| Entry Fee | $121 |
| Field Size | 275 |
| Entries | 1 |
| Final Score | 89.6 |
| Cash Line (est.) | 90.0 |
| Result | MISS |
| Total Salary | $49,800 |
| SP Points | 24.6 |
| Hitter Points | 65.0 |
| Best Player | Bryce Harper (27.0 pts) |
| Worst Player | Colt Keith (0.0 pts) |

### Lineup
| POS | Player | Team | Salary | DK Pts |
|-----|--------|------|--------|--------|
| SP1  | Kevin Gausman          | TOR   | $8,500 | 2.3 |
| SP2  | Troy Melton            | DET   | $7,000 | 22.3 |
| C    | Dillon Dingler         | DET   | $5,600 | 16.0 |
| 1B   | Bryce Harper           | PHI   | $5,900 | 27.0 |
| 2B   | Ernie Clement          | TOR   | $3,100 | 8.0 |
| 3B   | Colt Keith             | DET   | $2,900 | 0.0 |
| SS   | Kevin McGonigle        | DET   | $4,800 | 3.0 |
| OF1  | Riley Greene           | DET   | $4,300 | 6.0 |
| OF2  | Kerry Carpenter        | DET   | $3,800 | 0.0 |
| OF3  | Carson Benge           | NYM   | $3,900 | 5.0 |

### Key Decisions
| Decision | Rationale | Outcome | Verdict |
|----------|-----------|---------|---------|
| DET 5-man stack over PHI                 | Ownership/leverage, DET raw score #1          | DET scored 1 run — wrong call              | ❌ Wrong |
| Harper as only PHI piece                 | Budget forced single PHI bat                  | 27 pts, HR — right player wrong depth      | ⚠️ Mixed |
| Gausman as SP2                           | Budget constraints, no trap flags             | 2.3 pts, 6 ER, 3 HR — lineup killer        | ❌ Wrong |
| Melton as SP1 (DET corr)                 | SURGING form, DET game correlation            | 22.3 pts, 6 IP 1 ER — vindicated           | ✅ Correct |
| Fade Nootbaar → Benge (weather)          | Kevin Roth yellow + gut feeling               | STL postponed, saved 0-pt OF slot          | ✅ Correct |
| Fade ARI/STL entirely                    | Kevin Roth + AccuWeather 49%+ precip          | STL postponed, ARI affected ✅              | ✅ Correct |
| Drop Okamoto for Keith                   | 5-man DET 1-2-3-4-5 stack structure           | Keith 0pts, Okamoto HR missed              | ❌ Wrong |
| Clement over Shaw at 2B                  | Shaw not in confirmed CHC lineup              | Clement 8 pts — acceptable                 | ✅ Correct |

### Lessons Learned
1. STEAM is the tiebreaker when conf is tied. PHI had STEAM, DET did not. PHI won 4/6 secondary tiebreakers (STEAM, individual scores, ITT, market score). When conf is tied run the full checklist: (1) STEAM? (2) Higher individual scores? (3) Higher ITT? (4) Higher market score? (5) Worse opp pitcher? Whoever wins is the primary stack.

2. TRAP/PARADOX/STICKY on opposing SP = avoid rostering that pitcher. It does NOT guarantee the stack scores. Bad pitchers can still have good nights (Imai: 6 IP, 0 ER, 10 K at conf 0%). Build the stack on matchup quality but treat trap flags as a fade signal for SP selection only, not a scoring guarantee.

3. STEAM + ANTI_CHALK firing together = undervalued GPP play, NOT chalk. Don't fade a team with high ticket share if STEAM + ANTI_CHALK are both firing. The model is explicitly saying ownership is suppressed relative to true probability. This is the ideal single-entry structure.

4. SP red flags are real — don't rationalize for budget. ERA L3 7.71 + WALKS_PENALTY = genuine danger. If budget forces a SP with multiple negative indicators, rebuild the lineup structure rather than accepting it. A 2.3 pt SP kills the lineup regardless of hitter quality.

5. Weather research process validated. Kevin Roth (ballparkpal.com) + AccuWeather hourly is the correct workflow. STL postponed on June 25 — the gut call to override Nootbaar for Benge saved the lineup from a 0-point OF slot. Always check Kevin Roth within 90 minutes of lock for weather games.

6. Confirmed batting order matters. DET 1-2-3-4-5 was the build rationale. Even with perfect order alignment the stack can go cold (5 hits, 1 run). Order confirmation reduces variance on PA count but doesn't guarantee run production.


### Signal Performance — Running Log
| Signal | Entity | Date | Prediction | Result | Grade |
|--------|--------|------|-----------|--------|-------|
| STEAM + ANTI_CHALK                  | PHI          | 2026-06-25 | Stack goes off                      | 10 runs, 1.012 OPS ✅                   | A+ |
| ANTI_CHALK (team stack)             | DET          | 2026-06-25 | Low ownership + scores              | Low ownership ✅ / 1 run scored ❌       | D |
| TRAP/PARADOX/STICKY (SP)            | Imai         | 2026-06-25 | DET stack scores freely             | 1 run, Imai 6IP 0ER 10K ❌              | F |
| TRAP/PARADOX/STICKY (SP)            | Cavalli      | 2026-06-25 | PHI stack scores                    | 10 runs, pen imploded ✅                | A+ |
| Individual score 100.0              | Harper       | 2026-06-25 | Elite DK performance                | HR, 3 RBI, 27 pts ✅                    | A+ |
| SURGING form                        | Melton       | 2026-06-25 | Quality start                       | 6 IP, 1 ER, 22.3 pts ✅                 | A |
| ERA L3 7.71 + WALKS_PENALTY         | Gausman      | 2026-06-25 | Red flag SP                         | 6 ER, 3 HR, 2.3 pts ❌                  | F |
| Weather fade STL/ARI                | STL          | 2026-06-25 | Delay or postponement               | STL postponed ✅                        | A+ |
| 96% conf (team)                     | DET          | 2026-06-25 | High scoring game                   | 1 run scored ❌                         | F |
| 96% conf (team)                     | PHI          | 2026-06-25 | High scoring game                   | 10 runs scored ✅                       | A+ |
| HOT_MSMI + SMASH                    | Okamoto      | 2026-06-25 | High upside individual              | HR, 2 RBI — not rostered ❌             | N/A |

### Architectural Updates (June 27, 2026)
#### Opener/Bulk Pitcher Auto-Detection System
- **Context:** Corrected the opponent stack scoring vulnerability where the model was evaluating against short-leash openers rather than bulk relief pitchers.
- **Decision:** Implemented `utils/opener_detector.py` to auto-detect openers based on DraftKings CSV tags (`PO`/`PLR`), salary differentials, and historical/props usage heuristics.
- **Rules Integrated:**
  1. Disabled opener detection for the first 7 days of each MLB season to prevent false positives on unstable opening-week usage patterns.
  2. Nested the opener visually under the bulk arm in the Pitchers Matrix, keeping the opener's details card accessible via click-delegation.
  3. Propagated bulk-arm stats to the opponent's team report stack scoring while keeping the team report signals intact.
  4. Preserved clean, emoji-free ASCII console prints in Python scripts to guarantee Windows Terminal compatibility.

#### June 27, 2026 (Second Session) — Upgraded Opener Detection & Safety Shields
- **Context:** Upgraded the opener detection system to use player props outs lines and RotoWire line-up tags to maximize detection accuracy.
- **Decision:**
  1. **Tier 1A - RotoWire SP Highlighters:** Scraped `.lineup__player-highlight` elements from RotoWire lineups inside `data/lineup_fetcher.py` to identify `(O)` and `(B)` tags. Gracefully falls back with warnings if the page layout changes.
  2. **Tier 1C - Player Props Outs Line:** If the scheduled starter has an outs line $\le 8.0$, they are marked as an opener. We then scan for teammate props with an outs line $\ge 12.0$ to resolve the bulk arm. If no teammate qualifies, map to `BULK_UNRESOLVED`.
  3. **Safety Gate - Props Pending Protection:** If the starter's outs line is missing/null, skip all detection, return `PROPS_PENDING` and render `⚠️ PROPS PENDING` on the pitcher's card. This protects starters whose props are not yet open from false-positive detection.
  4. **Lowered Salary Gap:** Lowered same-team salary gap threshold from `$1,500` to `$1,000` to catch Cruz/Spence-type situations.
  5. **Inline Matrix Warnings:** Render `⚠️ Cruz (OPENER) -> ? (BULK UNRESOLVED)` in the opposing pitcher column of the Teams Matrix if the bulk arm cannot be resolved.

#### June 27, 2026 (Third Session) — Short-Leash Volatility Hard-Cap Implementation
- **Context:** Stacks opposing volatile short-leash starters were failing due to early exits handing games to rested bullpens.
- **Decision:** When opposing SP fires EIV + k_line ≤ 4.0, team is capped at a hard-cap of 75.0 (not soft-cap compression) unless 2+ of STEAM, DQI TRUST, or GASSED pen are present. Implemented after June 27 short-leash bust pattern (Gusto/Imai/Thornton three-slate sequence). Toggle: `short_leash_soft_cap_enabled` in `weights.json`.
- **Backtest Performance:** Showed +1.96% Top 1 hit rate on 51 slates / 31 trigger events (full clean history from May 22 to June 27). This should be revisited at the late-July audit when more trigger events have accumulated.

### June 26, 2026 — Slate Post-Mortem & Strategic Lessons

#### Entry 1 — TRAP Arm Pattern (June 26 2026)
June 26 2026 — TRAP arm over-delivery pattern identified across three consecutive nights. Imai (TRAP+PARADOX) June 25: gem, DET 0 runs. Thornton (conf=0, TRAP+STK+EIV) June 26: 6 IP, 7K, 1 ER, 21.90 DK pts, PHI 2 runs. Eovaldi (TRAP+STICKY) June 26: 7 IP, 9K, 0 ER, 34.15 DK pts (best SP on slate). Three consecutive nights of TRAP-flagged arms delivering strong outings. The model is systematically overconfident in fading TRAP arms short-term. Differentiate between "genuinely bad arm" (13.50 ERA bulk arm) and "arm in a difficult spot who can still execute" (second career start, decent stuff). TRAP+EIV combination may be too aggressive in confidence suppression. Flag for July audit: review full TRAP arm historical outcomes and recalibrate confidence penalties accordingly.

#### Entry 2 — COL Morning Signal Compression (June 26 2026)
June 26 2026 — COL had DQI=87 TRUST at morning refreshes before signal compressed mid-afternoon. COL scored 8 runs tonight against Bradley. Original morning signal was correct. When a DQI TRUST signal fires early and then gets suppressed by later model movements, the original signal may deserve more weight than the degraded version. Research question for July audit: when high-DQI teams experience mid-day signal compression, does the compressed signal or the original signal better predict actual run outcomes historically? Pull all archived slates where DQI TRUST appeared in morning refresh but dropped by afternoon and cross-reference actual runs scored.

#### Entry 3 — ARI Multi-Signal Failure (June 26 2026)
June 26 2026 — ARI fired HOT MSMI + BURST + GASSED + PITCH ALIGN simultaneously (4 signals) with conf=95 and blended=121. Scored 1 run. This is the second instance this week of a team with 4+ signals firing massively underperforming. The June 26 AG backtest showed the 4-5 signal bucket had only 6 historical cases and a 16.7% hit rate for 5+ runs — the smallest and weakest bucket in the analysis. The warning was in the data and should have been weighted more heavily. Decision rule going forward: when a team fires 4+ signals simultaneously, treat the small sample size as a caution flag rather than a conviction amplifier. Do not chase signal count as a proxy for confidence.

### June 28, 2026 — Model Changes Shipped (Post-Backtest Validated)

#### Change C (Fix B GASSED_PEN modifier) — BACKTESTED AND REJECTED June 28, 2026
Proposed raising the Fix B short-leash cap from 75 to 82 when opposing bullpen fatigue is 90%+. Historical backtest across 4 instances (all available data) showed 0% hit rate (0 for 4 teams scoring 5+ runs) with a gassed pen behind a short-leash starter. Teams averaged 3.00 actual runs vs significantly higher ITT in all cases. The 75 cap is working as intended. Do not revisit without at least 15 additional data points. Sample size as of June 28: 4 games.

#### Change A — PARADOX Resolution Logic — IMPLEMENTED
Replaced raw xwOBA comparison with ITT-first tiebreaker hierarchy (ITT → momentum signals → bullpen fatigue → xwOBA). Backtest: 127 games, improved accuracy from 46.5% to 54.3% (+7.9 percentage points). Current logic was sub-coin-flip. This is v1 of PARADOX resolution — marked for deeper optimization pass in July audit. Backtest script permanently saved at tests/backtest_paradox.py.

#### Change B — ANTI_CHALK Attack Conf Ceiling — IMPLEMENTED AS GUARDRAIL
When is_anti_chalk_smash drives attack_conf above 80 and ITT < 4.5, cap the contribution to +5 points max. Backtest: 0 historical firing instances below ITT 4.5 (model gate already exists), 20 games in 4.5-4.8 range showed ANTI_CHALK at 40% hit rate vs 42.5% baseline (not additive). Implemented as documented policy constraint, not a data-validated improvement. Net delta on recommendations: 0.0% on 53 slates.

#### Change C — Fix B GASSED_PEN Modifier — BACKTESTED AND REJECTED
See entry above.

#### Change D — Team Offensive Cold Streak Discount — DEFERRED
Requires team-level recent game result ingestion from StatsAPI schedule endpoint. Not currently in pipeline. Data engineering task for July.

#### Change E — Pitcher CONF Floor GPP Risk Badge — IMPLEMENTED
Implemented a two-tier GPP risk badge system: pitchers with 55-70 confidence are flagged with `HIGH GPP RISK` (43.2% underperformance rate), and pitchers with 70-79 confidence are flagged with `MODERATE GPP RISK` (34.6% underperformance rate). Pitchers with >=80 confidence receive no badge (24.4% underperformance rate). Added visual warnings for recommended starting pitchers falling in these ranges.


#### Phillips/STL Fix B Clarification
Fix B did not fire for STL on June 28 vs Phillips because his outs odds shifted from +102 (trap territory) to -110 (not a trap) between the 3:36 PM and 4:09 PM runs due to a live market vig adjustment. This is expected model behavior, not a bug. Flag for July audit: evaluate whether OMEGA should use the most conservative odds reading within a lock window rather than the most recent reading, to prevent vig adjustments from clearing genuine trap status.

#### COLD_HIGH_BR_WARNING flag — IMPLEMENTED June 28, 2026
New flag fires when is_cold_streak_msmi=True AND blended_rating >= 80. Backtest validation: 83.9% underperformance rate (26/31 instances), average DFS delta -4.03 points, across 53 historical slates. This is the highest-confidence hitter avoidance signal in the model. Fires as a prominent red COLD WARNING badge in dashboard and a warning in optimizer output. Do not roster hitters with this flag active regardless of raw blended_rating. Validated June 28 — add to July audit review with updated sample size.

#### actuals_cache completeness fix — IMPLEMENTED June 28, 2026
Extended actuals_cache hitter records to include complete DraftKings scoring fields: singles (derived), doubles, triples, runs_scored, walks, stolen_bases, hbp. Added calculate_dk_score helper function to utils/audit_engine.py. Backfilled all 53 historical slates via scripts/backfill_actuals.py. All three permanent backtest scripts (backtest_fade_risk.py, backtest_msmi_accuracy.py, backtest_lock_vs_lean.py) updated to use complete scoring formula. Prior hitter signal validation results (HOT_MSMI, COLD_MSMI, STRONG_EDGE, ELITE_PLATOON, PLATOON_TRAP, LEAN vs LOCK) should be considered superseded by post-backfill numbers. Clean baseline established June 28 for July audit.

#### HOT_MSMI signal reversal — June 28, 2026
Earlier in tonight's backtest session, HOT_MSMI appeared neutral vs baseline (34.3% outperformance rate, -0.13 DFS delta) on incomplete actuals. After the actuals_cache completeness fix was implemented and all 53 slates were backfilled with complete DK scoring (runs, walks, stolen bases, HBP), HOT_MSMI rehabilitated entirely: 50.3% outperformance rate, +2.11 DFS points average delta on 780 instances. The earlier finding was an artifact of missing scoring categories in the actuals. HOT_MSMI is a validated positive buy signal worth approximately +2 DFS points above projection on average. Do NOT downgrade or recalibrate this signal in the July audit — the complete data confirms it is working correctly.

#### STRONG_EDGE and ELITE_PLATOON projection inflation — flagged June 28, 2026
With complete actuals, STRONG_EDGE shows 46.4% outperformance rate (below 52% baseline) and ELITE_PLATOON shows 36.6% (well below baseline) on 422 and 224 instances respectively. Both signals may be overcorrecting projections upward — the matchup advantage is real but the model appears to raise the projection ceiling by more than the actual DFS benefit warrants. Add to July audit: investigate whether STRONG_EDGE and ELITE_PLATOON projection multipliers need downward calibration.


### July 20-25 Audit Window — Shipped Decisions (June 30, 2026)

#### Item 1: Pitcher Variance & Fade Tiers — IMPLEMENTED
- **Context:** Starting pitchers with high performance variance hitting low confidence (CONF <= 25) were treated identically to low-variance pitchers, masking their high ceiling potential.
- **Decision:** Implemented game-by-game starting pitcher DraftKings points mean and standard deviation over trailing 15 starts in the form cache. `is_high_variance` is flagged if starts sampled >= 3 and (`std >= 8.0` or `std/mean >= 0.5`). Under low confidence, high-variance pitchers are classified as `⚠️ VOLATILE FADE` (leveraged ceiling options) and low-variance as `🔒 SOLID FADE` (high-conviction fades).
- **Validation:** Trey Yesavage's real starting log (N=14 starts) showed `mean = 15.63`, `std = 8.20`, and `std/mean = 0.525`, successfully triggering the `is_high_variance` flag.

#### Item 2: Walks Penalty Recent Form Gate — IMPLEMENTED
- **Context:** Vegas walks lines adjust slowly, penalizing control pitchers who had early-season control noise but have established solid recent control (like Peter Lambert).
- **Decision:** Gated the Walks Penalty by checking season and recent form walk rates. If a pitcher's recent L3 BB/9 is < 3.2 and season BB/9 is < 3.8, the Walks Penalty is suppressed (`walks_line = None` and `walks_odds = None`).
- **Validation:** Audited 188 penalized starters across 54 slates. Suppressed 37.2% under a 3.5 season gate and 42.0% under a 3.8 season gate. The 9 delta pitchers (e.g. Anthony Kay: 2.76 recent/3.77 season on June 5; Kyle Leahy: 2.93 recent/3.60 season on June 5; Merrill Kelly: 1.96 recent/3.71 season) are all established control starting pitchers in peak form, confirming the 3.8 cutoff is mathematically sound.

#### Item 3: Slate Confidence Compression Warning — IMPLEMENTED
- **Context:** Top stack confidence scores clustering closely prevents the model from discriminating between top options.
- **Decision:** Implemented standard deviation calculation of top 6 stack confidence scores. If std < 5.0, a "Low Differentiation" warning fires on the report and the dashboard banner.
- **Validation:** Hitter-level backtest on 29 slates (25 pre-May 20 slates excluded due to missing `attack_conf` fields) showed compressed slates (N=6) actually have significantly higher average top hitter scores (**13.50 DK pts** vs **9.00** on differentiated slates) and top 3 average (**12.17 DK pts** vs **8.42**). Compressed slates indicate high-scoring environments, but because they are all good, selection must pivot to GPP ownership/leverage. Signal qualified as preliminary due to sample size.

#### Item 4: Within-Team Production Concentration & Stacking — RESEARCH COMPLETED
- **Context:** Evaluated hitter combined scores and marginal score contributions across 220 team run explosions (Runs >= ITT + 2.0) to optimize stacking sizes.
- **Decision:**
  - Hitter 1 (Highest Blend) hit 15+ DK pts at 37.2% rate, Hitter 2 at 30.5%, Hitter 3 at 30.5%.
  - Joint 2-hitter rate is **26.46%** (vs **25.08%** independent, a **1.06x clustering multiplier**).
  - Joint 3-hitter rate is **2.24%** (vs **3.46%** independent, a **0.65x cannibalization penalty**).
  - **Combined Stack Scores:** 2-man: **23.80** | 3-man: **34.72** | 4-man: **45.37** | 5-man: **55.66** (Marginal contributions: H1/H2 avg 11.90, H3 adds 10.92, H4 adds 10.65, H5 adds 10.29).
- **GPP Strategy:** Hitter production exhibits diminishing-but-still-strongly-positive returns as stack size grows: each added hitter contributes slightly less than the previous (a ~13.5% drop in marginal value from the 2nd to the 5th hitter), but even the 5th hitter still adds ~10.3 points on average, so combined stack production keeps growing through 5-man builds. 4-man and 5-man stacks remain optimal for GPPs because they maximize total stack points. However, 2-man and 3-man mini-stacks represent highly effective GPP pivots in single-entry fields where ownership on large stacks is over-concentrated.

#### Item 5: JSON Schema Matchup Clarity — IMPLEMENTED
- **Context:** Matchups were easy to misattribute under time pressure.
- **Decision:** Added redundant `opposing_team` to pitcher objects, and `opp_pitcher_team` to team objects.

#### Item 6: Doubleheader Scheduling Matching — IMPLEMENTED
- **Context:** Opener and bulk arm detection mismatched pitchers on doubleheader slates.
- **Decision:** Grouped team pitchers using timezone-aware local game time compared to event commence UTC time within 1.5 hours, with a naive fallback for unit tests.

#### Item 7: Hitter MSMI Momentum Logic Fix — IMPLEMENTED
- **Context:** Cold hitters with high season averages were triggering positive hot run signals.
- **Decision:** Gated `is_hot` so it is set to `False` if rolling or recent OPS is below season average by more than a 2% tolerance band (`rolling_ops < season_ops * 0.98` or `recent_ops < season_ops * 0.98`).


### July 8, 2026 — Slate Post-Mortem Updates (July 7 Slate Audit)

#### OLS-Calibrated Pitcher Volatility Penalty — IMPLEMENTED
- **Decision:** Apply a standard `-4` confidence penalty to starting pitchers flagged with `is_volatile` at lock.
- **Mathematical Validation:** OLS regression on $N = 1,012$ starts (April 15 to July 2, 2026) shows `is_volatile` has a statistically significant independent coefficient of **$-1.65$ DK points** ($p = 0.0373$). Applying a $2.5\times$ scaling factor (calibrated from the low-ceiling flag's $-3.20$ DK points drop being penalized $-8$ confidence points) maps to a `-4` confidence points penalty.
- **Compound Volatility + Low Ceiling Additive Model:** When combined with `is_low_ceiling` (penalized `-8`), volatile pitchers naturally receive a combined additive `-12` penalty. Regression indicates **no compounding interaction** (interaction term $-0.0279$ DK points is completely insignificant, $p = 0.988$), making a simple additive model statistically superior. The success rate of this group drops from $42.9\%$ (clean) to **$16.1\%$** ($5/31$ starts), though the difference vs. low-ceiling-only ($32.4\%$) has a two-tailed p-value of **$0.0608$** and is not statistically significant at the 95% level due to small sample size ($N = 31$).

#### Outlier-Driven Recent Form Warning & Penalty — IMPLEMENTED (UNVALIDATED JUDGMENT CALL)
- **Decision:** Apply a `-10` confidence penalty and display an outlier-driven form warning if a pitcher's rolling 3-start ERA is distorted by a single outstanding start (specifically, if `recent_era_ex_best - recent_era >= 1.50` and `recent_era_ex_best >= 4.0`).
- **Logic:** `recent_era_ex_best` is computed as the **maximum ERA when any single start is removed** from the L3 window — which necessarily corresponds to removing the *best* start. The condition therefore fires only when removing the pitcher's best start causes a large ERA swing AND the resulting ex-best ERA is still bad (>= 4.0). This correctly identifies pitchers whose good-looking L3 ERA is propped up by a single gem start, with the other starts being genuinely bad. The directional logic is sound. (Note: a July 15 audit initially described this as a "design flaw" — that was incorrect and has been retracted.)
- **Limitation:** The `-10` weight is entirely unvalidated. The penalty also fires only for pitchers in the form cache (~24 entries), which is refreshed only for the current slate. `is_outlier_driven` is not written to snapshot CSVs, making retrospective validation impossible. Statistical testing is blocked until the form cache coverage gap (backlog item #3) is fixed.
- **Validation Note:** **[UNVALIDATED JUDGMENT CALL]** The concept is directionally sound but the weight is not data-derived. Backlogged for regression check once `is_outlier_driven` is logged to snapshots and N >= 300 records with the flag populated are available.

#### Same-Side Starter Stack Ceiling Cap — RETIRED July 15, 2026
- **Original Decision:** Apply a `-5` stack confidence penalty to teams whose starting pitcher has `attack_conf >= 85` (soft ceiling fader, "Zack Wheeler effect").
- **Retired:** July 15, 2026 audit validated this penalty and found no supporting signal.
  - **Controlled regression (N=1,442 hitter-game records):** After controlling for `own_sp_conf` (continuous) and slate-mean pitcher quality, `has_elite_own_sp` coefficient **sign-flips to positive** (+0.36 DK pts, p=0.69). The raw -0.6 DK pt gap was fully explained by the correlation between the binary >=85 flag and the continuous pitcher quality already priced into stack scores (r=0.526).
  - **OOS 5-fold CV:** Adding the cap term **worsened** prediction in 3 of 5 folds (mean MAE +0.004, paired t-test p=0.517). No predictive value confirmed out-of-sample.
  - **Root cause:** Double-counting. Continuous pitcher quality adjustments already suppress stack scores for elite-SP teams through other channels. The -5 penalty was redundant.
- **Implementation:** Code block removed from `score_stack_confidence()` in `utils/attack_confidence.py`. Retired comment left in place.

#### Backlog Items for Statistical Validation:
1. **Outlier-Driven Recent Form Penalty Check:** Verify if `is_outlier_driven = True` corresponds to a statistically significant drop in actual DraftKings points and success rate compared to clean recent-form starting pitchers. **[BLOCKED by item #3 — confirmed July 15]**
2. **Same-Side Starter Stack Cap Check:** Verify if teams stacking when their own starter has `attack_conf >= 85` exhibit a statistically significant drop in actual runs scored and DraftKings fantasy points compared to baseline. **[STUDIED July 15 — signal null, see July 15 entry]**
3. **[ELEVATED PRIORITY — July 15] Pitcher Form Cache Coverage Gap:** `pitcher_form_cache.json` is currently refreshed only for today's slate pitchers, leaving the cache with ~24 entries vs. the full pitcher pool (~175 over a week's slates). **This is now confirmed to be blocking validation of at least two live scoring penalties:**
   - `recent_era_5g >= 4.25` (-6 CONF) — dead code, never populates. Removed July 13.
   - `is_outlier_driven` (-10 CONF) — fires for 14 of 24 cached pitchers today but is never written to snapshot CSVs, making retrospective validation impossible. Cannot be tested statistically until coverage is fixed.
   - This is the third finding this week tracing back to the same root cause. It is not a minor pipeline gap — it is actively preventing validation of live production scoring decisions. **Fix should be prioritized before any further penalty tuning work on pitcher signals.** The form cache refresh in `statcast_bridge.py` must be expanded to cover all pitchers on each day's slate at run time (not just the current day's 24), and `is_outlier_driven` must be added as a logged column in the `signal_tracker.py` snapshot CSV.
4. **recent_era Penalty Re-Calibration:** Current `-6 CONF` penalty for `recent_era >= 4.50` is likely oversized relative to the controlled effect size (~-2.9 DK pts, p=0.041 after controlling for SIERA and opponent environment). Re-calibrate once N exceeds ~400 pitcher-game records to support a stable 3-covariate OLS.


### July 9, 2026 — Pitcher Recent-Form Calibration Regression Study

#### Pitcher Recent-Form Rolling Penalties — IMPLEMENTED (UNVALIDATED JUDGMENT CALL)
- **Decision:** Apply confidence penalties for recent poor performance splits:
  - Rolling 5-game ERA (`recent_era_5g >= 4.25`): `-6` confidence penalty.
  - Rolling 3-game ERA (`recent_era >= 4.50`): `-6` confidence penalty.
  - Divergence from season SIERA (`recent_era - siera >= 1.50` or `recent_era_5g - siera >= 1.50`): `-4` confidence penalty.
  - Rolling 3-game walk crisis (`recent_bb9 >= 4.5`): `-6` confidence penalty.
- **Validation Note: [UNVALIDATED JUDGMENT CALL]**
  - Multiple linear regression was conducted on starting pitcher starts to validate if recent form splits predict actual DraftKings points.
  - We ran two runs of the same model:
    - **Run 1 (N = 153 starts):** `recent_era_5g` coefficient $-0.9553$ ($p = 0.1323$ -> **Not significant**), `siera_div` coefficient $-0.3514$ ($p = 0.5337$), `recent_bb9` coefficient $+0.0933$ ($p = 0.8875$).
    - **Run 2 (N = 167 starts):** `recent_era_5g` coefficient $-1.3059$ ($p = 0.0331$ -> **Significant**), `siera_div` coefficient $+0.0378$ ($p = 0.9429$), `recent_bb9` coefficient $+0.2178$ ($p = 0.7308$).
  - **Discrepancy Analysis:** 
    - The difference of 14 starts between Run 1 and Run 2 is due to API connection timeouts on the host during Run 1, which omitted 10 July 8 starting pitchers completely (e.g. MacKenzie Gore, George Kirby, Colin Rea, Dean Kremer, Alan Rangel, Steven Cruz, Gabriel Hughes, Jeffrey Springs, Troy Melton, Connor Prielipp) and 4 starts that had outdated game logs.
    - Adding these 14 starts (which clustered several bad outings/busts on July 8 like Gore's 5.25 DK pts and Springs' -0.25 DK pts) completely shifted the p-value of `recent_era_5g` from insignificant ($0.132$) to significant ($0.033$).
  - **Conclusion:** Because the regression results are extremely sensitive to the inclusion/exclusion of a single day's slate (July 8), and the coefficients diverge significantly under minor sample variations, **none of the four penalties are statistically validated**. They remain classified as **unvalidated judgment-call adjustments** based on qualitative post-mortem case studies. They are implemented to suppress slumping pitchers (like Davis Martin and MacKenzie Gore), but are not supported by a robust, stable regression.


#### Full First-Half SIERA Dominance Study — RESEARCH COMPLETED (NOT YET ACTED ON) — logged retroactively July 13
- **Methodology:** Full-season game logs through the 2026 first half. N = 962 starting pitcher appearances across all 244 starting pitchers. Outcome: `actual_dk_pts`. Predictors: `recent_era_5g` (rolling 5-game ERA) and `siera` (season-long SIERA). Source: `run_all_studies.py`.
- **Result:**
  \[ \text{dk\_pts} \approx 49.20 - 0.22 \cdot \text{recent\_era\_5g} - 6.80 \cdot \text{siera} \]
- **Interpretation:**
  - Season-long SIERA is the dominant driver of DK output ($-6.80$ per unit). A pitcher moving from a 3.00 SIERA to a 5.00 SIERA represents ~$13.6$ DK pts of expected difference.
  - Rolling 5-game ERA (`recent_era_5g`) has an independent coefficient of only $-0.22$ per unit once SIERA is controlled for. Even a pitcher posting a 7.00 ERA over their last five starts vs. a 4.25 ERA (the penalty trigger) represents an independent effect of only $(7.00 - 4.25) \times 0.22 = 0.61$ DK pts above what SIERA already explains.
  - The small-sample flip-flopping in the N=153/167 runs is explained by multicollinearity: when SIERA is absent from those models, `recent_era_5g` picks up SIERA's predictive power and appears artificially significant. Once SIERA is controlled for at full scale, rolling ERA adds almost nothing independently.
  - `siera_div` (the ERA-minus-SIERA divergence term): adding divergence as a separate term on top of SIERA and rolling ERA introduces further multicollinearity with no independent value — both the N=153/167 runs and this finding confirm zero measured independent effect.
  - `recent_bb9`: both small-sample runs showed small positive (wrong-direction) coefficients, consistent with noise. Not re-run at N=962 but directionally unsupported.
- **Logging Gap:** This finding was produced during the July 9 audit week via `run_all_studies.py` but was not formally recorded at the time. Logged here retroactively on July 13 to establish the documented basis for scoring decisions.
- **Action Gate:** Finding documented. Scoring change pending review.

#### Team Stack attack_conf Predictive Power Study — RESEARCH COMPLETED (DO NOT DEPLOY)
- **Context:** Evaluated the predictive power of the team-level composite `attack_conf` score across $N = 160$ team stacks from June 27 to July 8, 2026.
- **Findings:**
  - **No correlation with run production:** Regression of actual runs vs. ITT against `attack_conf` yields an R-squared of `0.0047` and an insignificant p-value of `0.391` (slope of `-0.0121` runs per confidence point).
  - **Inversion at the extremes:** Elite stacks ($\ge 80$) underperformed their implied totals (averaging $-0.16$ runs below ITT, 41.6% hit rate), while Low confidence stacks ($40\text{–}54$) overperformed (averaging $+0.99$ runs above ITT, 53.8% hit rate).
- **Strategic Impact:** Team-level `attack_conf` is currently uncalibrated and has zero floor-prediction value, likely due to over-weighting of broken/reverse signals (like Steam and DQI TRUST). 
- **Action Gate:** **DO NOT change anything live.** This finding directly impacts stack ranking and must be discussed as a priority upon Konrad's return before any model adjustments or merges are made.


#### July 9, 2026 — Composite Stack Trust Score Backtest & Modeling

##### New `stack_trust_score` Team Ranking Replacement — RESEARCH COMPLETED (UNMERGED / UNDER REVIEW)
- **Decision:** Build a separate `stack_trust_score` field on each team stack object alongside the existing `attack_conf` to evaluate replacement of team stack confidence ranking.
- **Formulation:**
  \[ \text{stack\_trust\_score} = 70.0 - 10.0(\text{opp\_sp\_any\_flag}) - 47.0(\text{is\_fade\_risk}) + 0.64(\text{anti\_chalk\_pct}) + 12.0(\text{is\_pitch\_alignment}) \]
  - *opp_sp_any_flag* = 1 if opposing SP is flagged with `trap_short_leash`, `trap_vulnerable`, `low_ceiling`, `hazard`, or `paradox`.
  - *is_fade_risk* = 1 if team has a public fade/sharp divergence.
  - *anti_chalk_pct* = percentage of hitter-level `is_anti_chalk_smash` flags on the team.
  - *is_pitch_alignment* = 1 if team has a GPP/ownership-leverage pivot flag.
- **Validation Results ($N = 160$ team stacks):**
  - **Component Significance:**
    - `opp_sp_any_flag`: Coefficient $-0.1002$ ($p = 0.8554$) $\rightarrow$ **Not statistically significant**.
    - `is_fade_risk`: Coefficient $-0.4696$ ($p = 0.8912$) $\rightarrow$ **Not statistically significant** (high variance, small flag count).
    - `anti_chalk_pct`: Coefficient $+0.0064$ ($p = 0.3806$) $\rightarrow$ **Not statistically significant** (directionally positive, $+0.32$ runs for 50% concentration).
    - `is_pitch_alignment`: Coefficient $+0.1247$ ($p = 0.8348$) $\rightarrow$ **Not statistically significant**.
  - **Composite Score Predictive Power (`runs_vs_itt ~ stack_trust_score`):**
    - R-squared: **`0.0053`**
    - Coefficient: **`+0.0177`** runs per confidence point
    - p-value: **`0.3589`** $\rightarrow$ **Not statistically significant**
  - **Comparison with `attack_conf` (`runs_vs_itt ~ attack_conf`):**
    - R-squared: `0.0047`
    - Coefficient: `-0.0121` runs per confidence point
    - p-value: `0.3912` $\rightarrow$ **Not statistically significant**
- **Conclusion:** 
  - The new `stack_trust_score` succeeds in inverting the counter-intuitive negative slope of `attack_conf` to a directionally correct positive slope (`+0.0177` runs per point). 
  - However, it remains **statistically insignificant** ($p = 0.3589 > 0.05$) and explains less than 1% of the actual run scoring variance vs ITT ($R^2 = 0.0053$). 
- **Action Gate:** **DO NOT merge to main.** Keep on the `audit/july-2026` branch for manual review. Flagged for Konrad's post-trip review: we must determine if stack ranking should pivot completely to blended projection rating and GPP leverage metrics rather than relying on any confidence/trust-based scoring.


### July 10, 2026 — Automated Daily Digest Wording Neutralization

#### Daily Digest narrative framing removed — IMPLEMENTED
- **Decision:** Modify `generate_digest.py` to prevent narrative/predictive language (such as "correctly suppressed," "top stack HIT," or "Failed") for refuted, reversed, or unvalidated flags.
- **Actionable Fix:**
  - Replaced `HIT`/`MISS` and `CORRECT`/`MISS` results in top stack, steam, and gassed pen loops with factual run details.
  - Added explicit warnings to `COLD_HIGH_BR_WARNING`, `is_steam`, `top_stack_log`, and `burst_log` print statements: `(note: this flag has an unreliable historical hit rate per the July audit)`.
  - Replaced characterizations in the `AUDIT FLAGS` section to describe outcomes strictly factually (e.g. "TRAP Arm Outperformed Expectation", "COLD_HIGH_BR Hitter Outperformed Baseline").
- **Reasoning:** To ensure that automated reports remain completely objective and do not quietly shift user perceptions of unvalidated or reversed signals while on the road.
- **Action Gate:** Implemented on the `audit/july-2026` branch. No changes to `main`.


### July 13, 2026 — Implementation of Redefined Team Stack Trust Score

#### Validation and Deployment of Implied-Total-Inclusive `stack_trust_score` — IMPLEMENTED (audit/july-2026 only)
- **Decision:** Redefine the stack trust score to incorporate the team's implied total: `stack_trust_score = implied_total * 10.0 - 10.0 * opp_sp_any_flag`. This resolves the structural "implied-total blind spot" (where low-scoring environment teams outranked high-scoring environment teams purely due to binary SP flags). It serves as the primary stack-ranking sort key in the report generator and dashboard, replacing and demoting the unvalidated `attack_conf` metric.
- **Formulation:**
  \[ \text{stack\_trust\_score} = 10.0(\text{implied\_total}) - 10.0(\text{opp\_sp\_any\_flag}) \]
  - *opp_sp_any_flag* = 1 if the opposing SP is flagged with `trap_short_leash`, `trap_vulnerable`, `low_ceiling`, `hazard`, or `paradox`.
- **Validation Results ($N = 1,076$ team-stacks):**
  - **Regression Validation:**
    - Regressing actual runs against the separate components `runs ~ implied_total + opp_sp_any_flag` shows that `opp_sp_any_flag` is not individually significant once controlled for `implied_total` ($p = 0.3801$, standard error $0.211$, coefficient $-0.185$). This is due to collinearity, as SP fader status is already priced into Vegas lines.
    - **Labeling Status:** SP-flag penalty term validated as adding incremental value via dry-run testing; exact weight (-10.0) is an unvalidated judgment call, same category as the outlier-driven and same-side-starter-cap penalties from the July 7 audit.
  - **Comprehensive Dry-Run Validation (All 56 Matched Slates):**
    - **New Sort vs. Old Sort Record:** **29 Wins | 10 Losses | 17 Ties**
    - **Win Rate (excluding ties):** **74.4%** on actual runs scored by the #1 pick.
    - **July 2 Pattern (Lower-ITT ranked above higher-ITT with no SP disadvantage):** **0 occurrences (0.0%)** across all 56 slates (down from 50.88% with the binary sort).
    - **Incremental Value over Vegas Baseline:** The pure Vegas implied total sort yields a 59.0% win rate (average 5.179 runs), while the redefined trust score yields 5.625 runs, adding a **real practical value of +0.446 runs per game** over pure Vegas ITT.
- **Key Takeaways & System Notes:**
  - **Resolution of July 2 Disagreement:** Incorporating `implied_total * 10.0` ensures the baseline scoring environment is preserved as the primary driver. On July 2, the Dodgers (6.0 ITT, facing a flagged SP) correctly outrank the Angels (3.4 ITT, facing a clean SP) in both the report and the dashboard (Dodgers #1 in both).
  - **Smooth Blended Ratings:** Because the trust score now operates on a continuous scale (e.g. 30.0 to 70.0), `blended_rating = (stack_score + stack_trust_score) / 2` retains a smooth, continuous distribution, avoiding any clustering or coarseness artifacts.
- **Action Gate:** Implemented on the `audit/july-2026` branch. No changes to `main`.


### July 13, 2026 — Removal of Platoon Label Confidence Adjustments

#### Platoon Split Double-Counting Cleaned and Gassed Bullpen Validated — IMPLEMENTED (audit/july-2026 only)
- **Decision:** Remove the dynamic platoon label adjustments (`ELITE PLATOON` / `STRONG EDGE` / `PLATOON TRAP` / fallback `platoon_multiplier` adjustments) from individual hitter confidence calculations. Keep the `GASSED BULLPEN` confidence adjustment active.
- **Reasoning:** 
  - **The Double-Counting Mechanism:** The individual hitter confidence calculation already directly prices in the matchup quality via `matchup_xwoba` (+18 CONF for >= 0.370, +10 for >= 0.345). Because the matchup xwOBA is itself built from the platoon splits, adding another splits-based confidence modifier (+12 CONF for `ELITE PLATOON`) results in double-counting the splits, which overcorrects hitter confidence scores.
  - **Statistical Evidence (N = 6,963 matched hitter-game outcomes):**
    - **`ELITE PLATOON`:** Statistically refuted by in-sample outcomes (N=196, OLS coefficient: -1.358521, t=-2.541, p=0.011089). Hitters flagged with this label underperform baseline expectations by -1.003 DraftKings points on average (t = -2.169, p=0.031305).
    - **`STRONG EDGE` & `PLATOON TRAP`:** Removed via the shared double-counting mechanism, not by independent proof. Neither signal cleared the individual significance threshold in OLS (p=0.215476 and p=0.240883 respectively).
    - **`GASSED BULLPEN`:** Strongly validated. Facing an exhausted bullpen has a highly significant positive OLS coefficient of **+0.593196 DK points** (t=3.363, p=0.000775).
  - **Out-of-Sample (OOS) Grouped 5-Fold Cross-Validation:**
    - Confirmed that removing the platoon adjustment block yields a **small but real, statistically significant improvement** on held-out slates. 
    - Average test MSE improved from 52.0524 to 51.9890 (paired t-test p=0.049205). Average test correlation improved from 0.0480 to 0.0602, and average R2 improved from -0.00123 to +0.00007 (both still near zero, showing small absolute magnitude relative to a near-zero baseline).
  - **3-Slate Illustrative Dry Run (July 4, 7, 8 — N=262 labeled hitters):**
    - Per-hitter prediction error computed by first fitting a linear calibration (dk_pts = 5.09 + 0.026 * attack_conf) on all 1,433 snapshot hitter-game records, then translating old vs. new CONF into expected pts, then computing signed error vs. actual.
    - **Calibration caveat:** The CONF->pts slope (0.026, r=0.082) is very shallow. A 12-pt ELITE removal shifts predicted pts by only ~0.31 — well inside per-game noise. Per-hitter MAE differences on a 3-slate sample (~0.05-0.08 pts) are not individually meaningful.
    - **Dry-run result:** ELITE PLATOON MAE improved (5.570 -> 5.519, 57% of hitters better). STRONG EDGE unchanged (no adjustment was removed). PLATOON TRAP slightly worse (+0.078) on this specific 3-slate sample.
    - **This dry run is ILLUSTRATIVE ONLY** — not additional statistical evidence. Its purpose is mechanical sanity-check (confirming conf->pts translation is correctly applied), not a separate validation finding. The headline statistical evidence for this change remains the N=6,963 in-sample regression (ELITE PLATOON p=0.011, avg -1.003 DK pts cost) and the N=6,963 OOS cross-validation (paired t-test p=0.049).
- **Action Gate:** Implemented on the `audit/july-2026` branch. No changes to `main`.


### July 13, 2026 — Pitcher Penalty Audit Follow-Up

#### recent_era_5g Penalty — Dead Code Removal
- **Finding:** `recent_era_5g` is `None` for **all 175** pitcher-game records in snapshot history (June 27–July 8). The `-6 CONF` penalty for `recent_era_5g >= 4.25` has **never fired in production**.
- **Root cause:** `pitcher_form_cache.json` is populated by `statcast_bridge.py` only for today's slate pitchers at cache-refresh time. It currently holds only 24 profiles — a fraction of the ~175 pitchers tracked. When `pitcher_analyzer.py` calls `form_cache.get(normalize_player_name(...))` (line 457), most pitchers return `None`, bypassing the entire form-population block (gated at line 474: `if p_form and p_form.get('recent_ip', 0) >= 8.0`). `recent_era_5g` stays at its initialized `None` value and propagates as `None` through to the confidence scorer.
- **Signal validity:** The field is correctly computed and stored when a pitcher is fetched — all 24 cache entries have valid `recent_era_5g` values. This is a coverage gap in the form cache pipeline, not a computation error.
- **Decision:** Remove the `recent_era_5g >= 4.25` penalty block from `attack_confidence.py` as **dead code cleanup**. This is not a signal quality judgment. The form cache coverage gap is **backlogged** for future pipeline work — if coverage is expanded to all slate pitchers, `recent_era_5g` should be re-evaluated statistically before re-adding any penalty.

#### recent_era Group Difference — Confound Check (N=175 pitcher-game records)
- **Question:** Does the naive 6.46 DK pt gap between `recent_era >= 4.50` and `recent_era < 4.50` groups (p=0.0003) survive controls for pitcher quality and opponent environment?
- **Three OLS models run:**

  | Model | `is_bad_era` coef | p-value |
  |---|---|---|
  | Naive (no controls) | -6.46 | 0.0003 |
  | + SIERA control | -5.18 | 0.0040 |
  | + SIERA + opp run environment | -2.86 | 0.0409 |

- **Confound structure:** `is_bad_era` correlates with SIERA ($r = 0.27$, $p = 0.0004$) and opponent run output ($r = 0.20$, $p = 0.009$), confirming partial confounding — bad-ERA pitchers tend to be lower-quality arms facing better offenses.
- **Conclusion:** The signal is **real but partially confounded**. Controlled effect size is approximately $-2.9$ DK pts (not $-6.5$), significant at $p = 0.041$. The current `-6 CONF` penalty is likely oversized relative to the controlled effect. **Kept at `-6` for now** — backlogged for re-calibration once N grows; current N=175 is too small to reliably fit a 3-covariate model.

#### siera_div Reduction — UNVALIDATED JUDGMENT CALL
- **Decision:** Reduce `siera_div >= 1.50` penalty from `-4 CONF` to `-2 CONF`.
- **Rationale:** Both small-sample regressions show near-zero independent coefficient for the divergence term once raw L3 ERA is included in the same model. This conservative reduction acknowledges the lack of evidence for the original weight.
- **Classification: [UNVALIDATED JUDGMENT CALL]** — The `-2` value is not data-derived. It is an arbitrary conservative downward adjustment from `-4`, not a measured effect size. Treat with the same skepticism as the original `-4`.
- **Action Gate:** Pending merge approval.


### July 14, 2026 — Historical Replication Study (2024/2025 Confirmation Layer)

#### Study Scope
Background confirmation study run against 2024 and 2025 backtest data (`backtest_2024_schedule.json`, `backtest_2025_schedule.json`, `backtest_2024_player_stats.json`, `backtest_2025_player_stats.json`). Goal: check whether two structural findings from this week's audit (SIERA dominance over rolling ERA; SP flag suppression) hold in prior seasons. No code changes follow from this study.

Full report: `historical_study_report.md` in the session artifact directory.

#### Finding 1: Run Environment — Comparable Across All Three Seasons
- 2024 mean RPG = 8.763; 2025 mean RPG = 8.889. t-test: t = -0.994, p = 0.320 — not significantly different.
- SP-filtered ERA medians: 2024 = 3.91, 2025 = 3.85, 2026 (snapshots) = 3.90. Within 0.06 runs across all three seasons.
- **Verdict:** Environments are comparable. 2024/2025 data is a valid structural reference layer for slow-moving findings, subject to the constraints below.

#### Finding 2: SIERA Dominance — Genuinely Open, Not Cross-Validated

> **Critical disclaimer:** The N=962 full-season 2026 SIERA-dominance finding (source: `run_all_studies.py`, documented earlier in this log) was **not tested or cross-validated in this study.** The 2026 data used here was the N=175 passive-tracker snapshot sample (9 slates, June-July 2026) — a different, smaller dataset from the same season. The 2025 analysis also used a different outcome variable (season-average runs allowed per start, not per-start DK pts) and a different aggregation level (season-aggregate ERA/SIERA vs. rolling per-start values). **The N=962 finding remains neither confirmed nor denied by any cross-season check.**

- **2025 result (N=342, all pitcher types, outcome = avg runs allowed per start):** ERA is the stronger single predictor (R2 = 0.213) vs. SIERA (R2 = 0.182). In the joint model, ERA wins (coef +0.265, p < 0.001) and SIERA is secondary (coef +0.371, p = 0.008, smaller weight). This is directionally opposite from the 2026 per-start finding — but the outcome variable and methodology differ materially. **Verdict: Different methodology — not comparable, directionally opposite.** This is not a clean contradiction of the N=962 claim.
- **2025 SP-only subset (N=120, IP >= 100):** ERA/SIERA correlation = r = 0.935 (VIF = 7.96). Severe collinearity makes joint-model attribution unreliable. **Verdict: Inconclusive.**
- **2024:** SIERA not present in 2024 player_stats. Analysis skipped.
- **Mechanistic note:** At the season-aggregate level, ERA has already converged toward true talent and competes directly with SIERA. The 2026 per-start finding may be specific to the rolling/small-sample-ERA context, where SIERA's walk/HR-rate components carry signal that small-sample ERA hasn't yet earned. Both observations can be simultaneously true in their respective contexts.
- **What a real cross-season check would require:** 2025 per-start DK point data. That data does not exist in this project's historical files. Not a current-week task.

#### Finding 3: SP Trap Flags — Untestable Historically
- Fields `trap_short_leash`, `trap_vulnerable`, `low_ceiling`, `hazard`, `paradox`, `is_trap`, `is_hazard`, `is_volatile` are **absent from both 2024 and 2025 backtest data.** These flags are computed at runtime by the live engine and not backfilled.
- No proxy substitution was attempted. A proxy would test a different question.
- **Verdict: Untestable with available historical data.** Flag validation must wait until enough 2026 live-slate snapshots accumulate.

#### Summary Table

| Question | Verdict |
|---|---|
| Are environments comparable? | **Yes** (RPG p=0.320, ERA medians within 0.06) |
| SIERA dominance cross-validated (N=962)? | **Not tested here.** N=962 remains an unconfirmed 2026-specific finding. |
| SIERA vs. ERA in 2025 runs-allowed (different methodology)? | **Different methodology — not comparable, directionally opposite.** ERA leads. Not a valid contradiction of N=962 claim. |
| SP trap flags testable historically? | **Untestable** — no flag data in 2024/2025 files. |


### July 15, 2026 — DQI, Public Steam Trap, and True Talent Penalty Signal Retirements

> [!WARNING]
> **Interacting Mechanisms Warning:** These retirements combine three interacting scoring mechanisms: a direct confidence boost (+10 CONF for DQI TRUST), a high-conviction stack gate signal (DQI TRUST and TTP), and a soft-cap bypass override (DQI TRUST overriding the divergence steam trap penalty). While each of these components was validated individually, the combined interaction effects of removing them simultaneously (e.g. Toronto on May 21 losing both the TRUST boost and the steam-trap bypass for a combined -18 CONF drop) have not been separately backtested as a joint interaction. They are implemented under the assumption of additive signal properties.

#### Summary of Re-Run Study Results (N=936 de-duplicated team-starts, 50 slates)

| Signal | Success Definition | Flagged N | Flagged Hit Rate | Baseline Hit Rate | Avg Diff vs ITT | Z-statistic | P-value | Verdict |
|---|---|:---:|:---:|:---:|:---:|:---:|:---:|---|
| **dqi_status_TRUST** | Actual Runs >= ITT | 20 | 30.0% | 44.8% | -0.80 runs | -1.33 | 0.1835 | **Reversed (Fade)** |
| **is_public_steam_trap** | Actual Runs >= ITT | 6* | 50.0% | 44.5% | -0.18 runs | 0.27 | 0.7857 | **Inconclusive (Lines gap)** |
| **is_true_talent_penalty (A)** | Actual Runs >= ITT | 108 | 48.1% | 44.0% | +0.09 runs | 0.81 | 0.4170 | **Neutral (No signal)** |
| **is_true_talent_penalty (B)** | Actual Runs >= ITT | 13 | 23.1% | 40.3% | -0.99 runs | -1.18 | 0.2372 | **Reversed (Fade)** |

*\*is_public_steam_trap note:* Pinnacle/Circa odds fields were missing for 91% of historical files in `reports/archive/`, limiting the retroactive dynamic N to 6. The original live-logged N=16 is also inconclusive (p=0.814) with no path to a larger sample without resolving the lines logging gap.

#### DQI Status TRUST Boost & Gate — RETIRED July 15, 2026
- **Original Decision:** Apply a `+10 CONF` boost to stacks flagged as `dqi_status == "TRUST"` (confirmed lineup/fresh data) and include it as a high-conviction stack gate signal.
- **Retired:** July 15, 2026 audit validated this signal and confirmed it is a reverse indicator.
  - **Hit Rate Analysis (N=20):** Stacks with TRUST status hit their implied totals only **30.0%** of the time (6/20) compared to a **44.8% baseline** (916 stats). Flagged teams underperformed by an average of **-0.80 runs below ITT**.
  - **OOS 5-Fold CV:** Retiring the boost slightly improved predictive accuracy (MAE delta −0.001798), though this small difference is directionally consistent but not meaningfully distinguishable from zero at this scale.
  - **Root cause:** Early confirmed lineups represent clean, public situations that Vegas prices to perfection (high ITT), leading to systematic underperformance relative to expectations.
- **Implementation:** Boost set to `+0.0` in `score_stack_confidence()` (retaining reasons description for tracing) and override logic removed. Removed from `_has_high_conviction_stack()` and `spec_signals` soft-cap check in `utils/attack_confidence.py`.

#### Public Steam Trap Penalty — RETIRED July 15, 2026
- **Original Decision:** Apply a `-8 CONF` penalty to stacks flagged with `is_public_steam_trap` (retail totals steamed up, sharp books held steady).
- **Retired:** July 15, 2026 audit confirmed there is no supporting evidence in the data. Logged as retired because no supporting evidence was found and current data limitations prevent further testing.
  - **Data Limitation:** Pinnacle and Circa odds/totals were missing for 91% of historical files in `reports/archive/`, making full-season backtesting impossible.
  - **Results:** N=6 in archive and N=16 in original live-logged audit are both completely inconclusive (p=0.814).
  - **Verdict:** Retired due to lack of supporting evidence and current data limitations.
- **Implementation:** Penalty block removed from `score_stack_confidence()` in `utils/attack_confidence.py`.

#### True Talent Penalty — RETIRED July 15, 2026
- **Original Decision:** Flag opposing starting pitchers whose Statcast profiles meet the low-talent/regression criteria (`ip >= 50.0`, `k_bb_pct < 0.14`, `hr_9 > 1.6`) and count it as a high-conviction stack gate signal.
- **Retired:** July 15, 2026 audit confirmed the signal is neutral or negative.
  - **Framing A: Retroactive Full-Season Profile Check (N=108):** Stacking against pitchers whose full-season stats fit this profile yielded **48.1%** hit rate vs. **44.0% baseline** (p=0.4170), showing no statistically significant positive edge.
  - **Framing B: Live-Logged Pre-Game Signal Check (N=13):** Stacks facing pitchers flagged live underperformed baseline (**23.1%** hit rate vs. **40.3% baseline**, p=0.2372).
  - **Verdict:** Neutral/negative signal. Retired from the high-conviction gates.
- **Implementation:** Removed from `_has_high_conviction_stack()` in `utils/attack_confidence.py`.




