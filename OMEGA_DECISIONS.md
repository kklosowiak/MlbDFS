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
- **Decision:** Apply a `-10` confidence penalty and display an outlier-driven form warning if a pitcher's rolling 3-start ERA is distorted by a single start (specifically, if `recent_era_ex_best - recent_era >= 1.50` and `recent_era_ex_best >= 4.0`).
- **Validation Note:** **[UNVALIDATED JUDGMENT CALL]** This is an unvalidated judgment-call penalty introduced as a qualitative slump proxy (derived from the Trevor McDonald post-mortem case) to prevent the model from endorsing pitchers whose rolling average is carried by a single outlier game. It has been **backlogged for a future regression check** once more slates with this flag accumulate.

#### Same-Side Starter Stack Ceiling Cap — IMPLEMENTED (UNVALIDATED JUDGMENT CALL)
- **Decision:** Apply a `-5` stack confidence penalty to teams whose starting pitcher has `attack_conf >= 85` (soft ceiling fader).
- **Validation Note:** **[UNVALIDATED JUDGMENT CALL]** This is an unvalidated judgment-call penalty introduced as a qualitative risk buffer to account for game-shortening ceiling cap risk (Zack Wheeler effect). It has been **backlogged for a future regression check** once more slates with this situation accumulate.

#### Backlog Items for Statistical Validation:
1. **Outlier-Driven Recent Form Penalty Check:** Verify if `is_outlier_driven = True` corresponds to a statistically significant drop in actual DraftKings points and success rate compared to clean recent-form starting pitchers.
2. **Same-Side Starter Stack Cap Check:** Verify if teams stacking when their own starter has `attack_conf >= 85` exhibit a statistically significant drop in actual runs scored and DraftKings fantasy points compared to baseline.


### July 9, 2026 — Pitcher Recent-Form Calibration Regression Study

#### Pitcher Recent-Form Rolling Penalties — IMPLEMENTED (UNVALIDATED JUDGMENT CALL)
- **Decision:** Apply confidence penalties for recent poor performance splits:
  - Rolling 5-game ERA (`recent_era_5g >= 4.25`): `-6` confidence penalty.
  - Rolling 3-game ERA (`recent_era >= 4.50`): `-6` confidence penalty.
  - Divergence from season SIERA (`recent_era - siera >= 1.50` or `recent_era_5g - siera >= 1.50`): `-4` confidence penalty.
  - Rolling 3-game walk crisis (`recent_bb9 >= 4.5`): `-6` confidence penalty.
- **Validation Note: [PARTIALLY VALIDATED]**
  - Multiple linear regression was conducted on a sample of $N = 167$ starting pitcher starts (spanning June 27 to July 8, 2026) to test if recent form splits predict actual DraftKings points.
  - **Results:**
    - `recent_era_5g` coefficient: $-1.3059$ ($p = 0.0331$) -> **Statistically significant (95% confidence)**
    - `siera_div` coefficient: $+0.0378$ ($p = 0.9429$) -> **Not statistically significant**
    - `recent_bb9` coefficient: $+0.2178$ ($p = 0.7308$) -> **Not statistically significant**
  - **Conclusion:** 
    - The rolling 5-game ERA (`recent_era_5g`) is a **statistically significant predictor** of a pitcher's actual DraftKings points ($p = 0.0331 < 0.05$). Under standard OMEGA scaling (2.5x), the coefficient $-1.31$ justifies a penalty of up to $-3.26$ confidence points per unit of rolling ERA. This mathematically validates the presence of a slump penalty (the $-6$ penalty implemented for `recent_era_5g >= 4.25` is highly conservative compared to the regression-calibrated value of $-11$).
    - The other three penalties (rolling 3-game ERA, SIERA divergence, and rolling 3-game BB/9) remain **unvalidated judgment-call adjustments** based on qualitative post-mortem case studies (e.g., Davis Martin and MacKenzie Gore). They have been implemented to suppress recommendations on slumping arms, but are not independently validated by historical regression in this sample.






