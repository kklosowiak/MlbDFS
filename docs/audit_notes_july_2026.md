# OMEGA Audit Notes — July 2026

**Branch:** `audit/july-2026`
**Last Updated:** July 1, 2026
**Author:** AG audit session (June 30 / July 1 slate review)

---

## Pattern #5: "Right Game, Wrong Team" — Accumulated Instance Log

### Definition
A "Right Game, Wrong Team" failure is any slate where OMEGA correctly identifies the
high-scoring game environment (e.g., weak opposing pitcher, gassed bullpen, high ITT)
but the model's confidence rankings direct the build toward the wrong side of the
matchup. The game delivers on run expectations; the wrong team captured most of them.

### Instance Log

| # | Date | Game | Model's Stack | Actual High-Scorer | Notes |
|---|------|------|---------------|--------------------|-------|
| 1 | 2026-06-25 | PHI vs DET | DET (conf=96) | PHI scored 10 runs | Imai TRAP/PARADOX, DET 1 run |
| 2 | 2026-06-26 | COL vs (opp) | Opponent stack | COL scored 8 runs | COL had DQI=87 TRUST in morning, compressed mid-afternoon |
| 3 | 2026-06-27 | TBD | TBD | TBD | Short-leash arm exited early, handed to rested pen — wrong team targeted |
| 4 | 2026-06-28 | TBD | TBD | TBD | STL Fix B non-fire due to vig adjustment — documented in DECISIONS.md |
| 5 | 2026-06-30 | SD @ CHC | CHC (opp of Mahle) | SD scored (see notes) | FADE_RISK on SD implied CHC was play; research Q below |

> Note: Instances 3 and 4 require cross-referencing the June 27-28 archive files for
> full game details. Instance 5 is the June 30 slate trigger for this log entry.
> June 30 actuals are not yet in the archive cache and are excluded from script runs
> until the cache populates naturally.

### Research Questions for July Audit

**RQ-1 (FADE_RISK Propagation):** When OMEGA fires `is_fade_risk=True` on Team A,
does the attack confidence score for Team B (the opponent) receive an implicit or
explicit boost? Or does Team B's score remain purely derived from its own signals?
If the opponent's conf does NOT receive a boost when Team A is faded, OMEGA may be
systematically under-valuing the opposing stack in these situations.

**RQ-2 (Signal Interaction Audit):** Do TRAP/PARADOX/STICKY signals on the opposing
pitcher simultaneously suppress the attack team's confidence OR do they fire
independently? The correct architecture is: TRAP on SP should inform the attacking
team's score upward, not just act as a fader for the pitcher slot. Verify in
`utils/attack_confidence.py` and `engine/sharps_weighting.py`.

**RQ-3 (DQI Morning-vs-Lock Divergence):** For the June 26 COL case, DQI=87 TRUST
fired in the morning refresh and was suppressed by afternoon. Does the lock-time
confidence weight incorporate any memory of the earlier signal state? If not, the
model may be systematically discarding valid early signals that do not persist to lock.

### Finding — July 5, 2026: Top Stack 80% ITT miss rate (N=5)

Highest attack_conf team hit ITT only once in 5 slates (July 2 LAD, 12 runs). All other top stacks missed ITT. Raw CONF number alone is not a reliable primary stack selector at the 97+ level. Aligns with 90+ overconfidence zone concern from June sessions.

Research question: Is there a signal combination (CONF + divergence + DQI + signal count) that predicts top stack success more reliably than CONF alone?

---

## Pattern: TRAP Arm Over-Delivery — Consecutive Night Sequence

### Definition
A TRAP arm over-delivery is any start where a pitcher flagged `is_trap=True` at lock
delivers a quality outing (low ER, sufficient IP) causing the attacking team's actual
runs to fall below ITT, despite the model having suppressed that team's attack conf.

### Documented Consecutive Sequence (June 25–30, 2026)

| Date | Pitcher | trap_type | Result | Attacking Team Outcome |
|------|---------|-----------|--------|------------------------|
| 2026-06-25 | Tatsuya Imai | TRAP+PARADOX | 0 ER, 6.0 IP, 10K | DET: 1 run (ITT ~4.7) |
| 2026-06-26 | Sean Thornton | TRAP+STK+EIV | 1 ER, 6.0 IP, 7K | PHI: 2 runs |
| 2026-06-26 | Nathan Eovaldi | TRAP+STICKY | 0 ER, 7.0 IP, 9K | Opponent: scored below ITT |
| 2026-06-27 | (Short leash arm) | Short Leash | 0 ER, exited early | BAL: 3 runs (below ITT) |

### Script-Verified 30-Day Statistics (July 1, 2026 run — `scripts/audit_trap_arms.py`)

> June 30 excluded from script run: actuals cache not yet populated.
> Script coverage: June 1–June 29 (21 dates with paired results + actuals in archive).

- **Total TRAP arm instances:** 96 (30-day window)
- **Instances with complete run data:** 88/96
- **Attacking team under-scored ITT:** 59.1% (52/88)
- **Average run differential (actual - ITT):** -0.30 runs
- **Breakdown by trap_type:**
  - `Vulnerable`: 66.7% under ITT, avg diff -0.70
  - `Short Leash`: 53.3% under ITT, avg diff +0.01
  - `Both`: 50.0% under ITT, avg diff +0.20
- **Notable over-deliveries (<=1 ER, >=4.0 IP):** 25 instances in the window

> Status: Confirmed from production archive files per AGENTS.md Rule 4.
> CSV available at `scratch/trap_arm_audit_30day.csv`.

### Research Questions for July Audit

**RQ-4 (TRAP/Vulnerable Suppression — Actionable):** The 30-day confirmed data splits
clearly by trap_type. `Vulnerable` (66.7% under ITT, avg -0.70 runs) shows real and
meaningful attack suppression. `Short Leash` (53.3% under ITT, avg +0.01) is noise —
no suppression warranted and no action needed on that designation.

The specific July research question for TRAP/Vulnerable is:

> "Should TRAP/Vulnerable reduce team attack_conf at lock, and if so by how much?
> The 30-day confirmed data suggests approximately -0.70 runs of inflation. Does a
> threshold-based suppression (e.g. cap attack_conf at 85 when opposing pitcher is
> TRAP/Vulnerable) produce better ITT alignment than the current behavior?
> **Do not implement — analyze during July audit.**"

**RQ-5 (Over-Delivery Clustering):** Do consecutive-night TRAP arm over-deliveries
cluster in specific game contexts (e.g., high-xwOBA teams, high-variance pitchers,
Coors Field)? The June 25-27 sequence all involved pitchers with recent_era < 2.5
despite their trap classification. Is there a `recent_form` gate missing from the
current trap logic?

**RQ-6 (TRAP vs STICKY_TRAP):** How does `sticky_trap=True` compare to `is_trap=True`
in actual run suppression? The short-leash cap (hard cap 75 when EIV + k_line <= 4.0)
is already implemented for one sub-type. Audit whether `sticky_trap` instances warrant
a separate suppression profile.

**RQ-7 (Consecutive-Night Persistence):** After a TRAP arm over-delivers on Night N,
does the model correctly update that pitcher's form status for Night N+1? Specifically:
if Imai throws a gem on June 25 (0 ER, 6 IP), does his form_status update to SURGING
or NEUTRAL for June 26's run? If not, there is a persistence bug.

### Finding — July 3, 2026: TRAP/Vulnerable vs TRAP/Short Leash confirmed as distinct patterns

Randy Vásquez (SD, July 2 lock):
trap_type=Short Leash, attack_conf=0, recent_era=8.31, ITT=5.95
Result: LAD scored 12 runs — arm gave up runs as expected. No over-delivery. +6.05 vs ITT.

Contrast: TRAP/Vulnerable pattern June 25-30 showed over-delivery 4 consecutive nights.

Working hypothesis: TRAP/Vulnerable fires when recent ERA is BETTER than season numbers — arm has momentum and may continue pitching well. TRAP/Short Leash fires on early-exit risk regardless of performance — gives up runs before being pulled.

Action for July audit: Compare trap_vulnerable_log vs trap_short_leash_log outcomes once N≥10 each. If hypothesis confirmed, consider suppressing team attack_conf specifically for TRAP/Vulnerable designation. Short Leash may require no change.

---

## Task 2: COLD_HIGH_BR_WARNING Reconciliation — Status and Findings

### Reconciliation Result: INSUFFICIENT DATA — DO NOT UPDATE DOCS

> Script: `scripts/audit_cold_high_br.py`
> Run date: July 1, 2026 (--days 45)

**Data availability (direct `is_cold_high_br_warning` field reads only):**

| Category | Count |
|----------|-------|
| Dates with field PRESENT and actuals available | 2 (June 28, June 29) |
| Dates skipped — field ABSENT (pre-implementation) | 32 |
| Dates skipped — missing results archive | 11 |
| June 30 | Excluded (actuals cache gap — add when populated) |
| **Flagged instances found (N)** | **0** |

The field `is_cold_high_br_warning` was implemented on **June 28, 2026**. Archive
files generated before that date do not contain the field. On the two post-implementation
dates with full coverage (June 28 and June 29), zero instances fired.

### Why the Previous 29-Instance Figure Was Wrong

An earlier version of the audit script used a fallback recalculation:
`is_cold_streak_msmi=True AND blended_rating >= 80`. This produced 29 instances
but **did not reflect what the model actually fired** — it was a re-derivation of
the flag from components on archive files that never stored the field. Those 29
instances have been discarded from this audit.

### What This Means for the Doc Figures

| Doc | Figure | Classification |
|-----|--------|----------------|
| OMEGA_CONTEXT.md | 54.8%, -0.58 DFS delta (31 instances) | Logic-level check: June 28 backtest script re-derived the flag from components on 53 pre-implementation slates |
| OMEGA_DECISIONS.md | 83.9%, -4.03 pts (26/31 instances) | Logic-level check: same June 28 backtest run, post-actuals-backfill |

Neither figure can be confirmed or refuted from the direct stored field. Both represent
the backtest script's recalculated view of what _would have_ fired given those hitter
states — which is a valid research result, but must be labeled accordingly.

> **UNVERIFIED AS OF JULY 1, 2026:**
> COLD_HIGH_BR_WARNING performance figures (both CONTEXT.md 54.8% and DECISIONS.md
> 83.9%) are unverified as of July 1. Both are derived from pre-implementation
> retroactive backtest, not confirmed production data. Do not treat either figure as
> validated until the mid-July re-run produces N >= 20 confirmed production instances.
> The signal continues to be used as a qualitative exclusion rule — the conceptual
> logic is sound — but performance statistics are not cited until the data is real.

**Do not update either doc.** Hard re-run scheduled July 21 (see Action Items).

### Finding 1 — COLD_HIGH_BR_WARNING live production failures

Yordan Alvarez fired the warning on both July 3 and July 4. Results: +6.7 DK pts vs baseline July 3, +31.0 DK pts vs baseline July 4. Combined: +37.7 pts above baseline across two consecutive nights.

Signal is not working as described in production.
Priority: URGENT. Re-examine before July 20 audit. Do not use as hard exclusion rule until verified.

---

## Action Items for July 20-25 Audit Window

| Priority | Item | Type | Status |
|----------|------|------|--------|
| **FIRST — July 21** | Re-run `audit_cold_high_br.py` against full post-June-28 actuals window. Target N >= 20 confirmed production instances before updating either governing doc. If N < 20, extend window and re-run July 25. **This runs before any other audit work begins.** | Data review | Hard calendar |
| HIGH | Investigate RQ-4: TRAP/Vulnerable attack_conf suppression — threshold analysis (e.g. cap at 85). Do not implement, analyze only. | Architecture | Deferred to July |
| HIGH | Investigate RQ-5: Recent form gate for TRAP classification | Architecture | Deferred to July |
| MED  | Investigate RQ-1: FADE_RISK confidence propagation to opponent | Code audit | Deferred to July |
| MED  | Investigate RQ-2: TRAP/PARADOX signal interaction with attack conf | Code audit | Deferred to July |
| MED  | Investigate RQ-6: sticky_trap suppression profile | Data analysis | Deferred to July |
| LOW  | Add June 30 actuals to cache, re-run both audit scripts | Data | When cache populates |
| LOW  | Investigate RQ-3: DQI morning-vs-lock signal divergence | Research | Deferred to July |
| LOW  | Investigate RQ-7: Form status persistence after over-delivery | Code audit | Deferred to July |

---

*This file documents observational patterns and research questions only.*
*No model logic, signal weights, or production code was modified in this session.*
*All data referenced is sourced from local production archive files.*
