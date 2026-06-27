# OMEGA Model Decision Log

This file tracks the reasoning behind major architectural and strategic decisions made on the OMEGA model. It's a companion to OMEGA_CONTEXT.md — context tells you WHAT the model is, decisions tell you WHY. When starting a new Claude or Antigravity session, paste both files at the start to recover full continuity.

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

