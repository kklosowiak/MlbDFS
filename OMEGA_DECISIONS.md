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
