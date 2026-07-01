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

> Per the 30-day audit script (`scripts/audit_trap_arms.py`), TRAP arms over-delivered
> against the attacking team's ITT 25 times out of 88 fully-tracked instances in the
> June 1-30 window (28.4% of TRAP arm games saw the attacking team score +1 or more
> above ITT; 59.1% saw attacking teams UNDER-score their ITT, which is the expected
> TRAP arm outcome).

### Script-Verified 30-Day Statistics (July 1, 2026 run)
- **Total TRAP arm instances:** 96 (30-day window, 21 dates with archive coverage)
- **Instances with complete run data:** 88/96
- **Attacking team under-scored ITT:** 59.1% (52/88)
- **Average run differential (actual - ITT):** -0.30 runs
- **Breakdown by trap_type:**
  - `Vulnerable`: 66.7% under ITT, avg diff -0.70
  - `Short Leash`: 53.3% under ITT, avg diff +0.01
  - `Both` (Vulnerable + Short Leash): 50.0% under ITT, avg diff +0.20
- **Notable over-deliveries (<=1 ER, >=4.0 IP):** 25 instances in the window

### Research Questions for July Audit

**RQ-4 (TRAP Type Differentiation):** `Vulnerable` trap arms show materially stronger
attack suppression (66.7% under ITT) vs `Short Leash` arms (53.3%). Should the
attack confidence penalty be graduated by trap_type rather than flat? The current
implementation applies the same -30 trap penalty regardless of type.

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

---

## Action Items for July 20-25 Audit Window

| Priority | Item | Type | Status |
|----------|------|------|--------|
| HIGH | Run `scripts/audit_trap_arms.py --days 30` and review full CSV | Data review | Done (July 1) |
| HIGH | Run `scripts/audit_cold_high_br.py --days 45` and review output | Data review | Done (July 1) |
| HIGH | Reconcile COLD_HIGH_BR_WARNING figures in OMEGA_CONTEXT.md (stale: 54.8%) | Doc update | Pending user review |
| HIGH | Investigate RQ-4: Graduated trap penalty by trap_type | Architecture | Deferred to July |
| HIGH | Investigate RQ-5: Recent form gate for TRAP classification | Architecture | Deferred to July |
| MED  | Investigate RQ-1: FADE_RISK confidence propagation to opponent | Code audit | Deferred to July |
| MED  | Investigate RQ-2: TRAP/PARADOX signal interaction with attack conf | Code audit | Deferred to July |
| MED  | Investigate RQ-6: sticky_trap suppression profile | Data analysis | Deferred to July |
| LOW  | Investigate RQ-3: DQI morning-vs-lock signal divergence | Research | Deferred to July |
| LOW  | Investigate RQ-7: Form status persistence after over-delivery | Code audit | Deferred to July |

---

*This file documents observational patterns and research questions only.*
*No model logic, signal weights, or production code was modified in this session.*
*All data referenced is sourced from local production archive files.*
