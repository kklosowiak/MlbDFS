# OMEGA Model — Honest Performance Report Card
*As of OMEGA v13.9 · May 30, 2026*

---

## Overall Grade: **B+**

---

## Category Grades

| Category | Grade | Change |
|:---|:---:|:---:|
| Pitcher Evaluation | **A-** | — |
| Team Stack Scoring | **B+** | ↑ (STORM/SURGING retired) |
| Hitter Scoring | **B** | ↑ (barrel%/hard hit% added) |
| Vegas / Market Integration | **B+** | — |
| Betting EV Engine | **C+** | — (needs 30 days data) |
| Projected Lineups | **B** | ↑ (3-tier fallback added) |
| Learning / Feedback Loop | **B** | ↑ (STORM/SURGING removed) |
| Data Pipeline | **B+** | — |
| Dashboard / UI | **A-** | — |
| Overall Architecture | **B+** | — |

---

### 1. Pitcher Evaluation — **A-**
**Strengths:** TRAP (72%), LOW_CEILING (79%), HAZARD (76%) — real, backtested edges. Form tracking (ERA L3, xwOBA rolling) is multi-factor. K-line ceiling gate is a genuine differentiator.
**Gaps:** LOW_CEILING + HAZARD combo still building sample (24 matchups). No inning-by-inning depth — everything is game-level.

---

### 2. Team Stack Scoring — **B+** *(improved: STORM/SURGING retired)*
**Strengths:** CONF is multi-factor (xwOBA, divergence, Vegas totals, DQI, matchup physics). LOW_CEILING CONF boost is backtested. DQI gate is a real differentiator.
**Gaps:** TEAM_SNEAKY_STACK (29%) still in model and underperforming. Offensive form signals underdeveloped on the team side.

---

### 3. Hitter Scoring — **B** *(improved: barrel%/hard hit% added)*
**Strengths:** Platoon labels, matchup xwOBA, smash factor, MSMI, prop line integration, pitch alignment heat map, barrel% and hard hit% now feeding scores and playbook display.
**Gaps:** Individual hitter recent form (last 7 game logs) is not tracked — only season-level OPS is used. No spray chart data. Still lighter depth than pitcher evaluation.

---

### 4. Vegas / Market Integration — **B+**
**Strengths:** Opening lines frozen at 4:30 AM ET. ML movement, total movement, divergence all feeding scores. Logit-space probability adjustment is mathematically correct.
**Gaps:** No book-by-book line data (sharp books vs. public books). Line movement velocity not tracked.

---

### 5. Betting EV Engine — **C+** *(v1, needs data)*
**Strengths:** LOCK/LEAN/PASS conviction framework is mathematically sound. Auto-swap of expensive ML for run line is correct logic. Best Bets leaderboard is clean and usable.
**Gaps:** Zero historical data yet — thresholds unvalidated. Not a purpose-built win probability model. Spread cover probability uses normal distribution assumption.

---

### 6. Projected Lineups — **B** *(improved: 3-tier fallback)*
**Strengths:** RotoWire primary → StatsAPI confirmed override → Statcast roster fallback. 5-min cache. Anti-ghost filtering. Nothing can break the UI silently anymore.
**Gaps:** Still single-source for projections (RotoWire). No confidence weighting: projected lineup treated same as confirmed.

---

### 7. Learning / Feedback Loop — **B** *(improved: noise signals removed)*
**Strengths:** 32 slates of backtest data. Auto-run on lock snapshot. 4-bucket signal output. STORM (0/14), SURGING (0/22), SHARK, WHALE, PHYSICS_OVERRIDE all retired.
**Gaps:** EV signals have zero history yet. No Bayesian auto-updating — recommendations require manual action. Need 50+ slates for statistically reliable signal grades.

---

### 8. Data Pipeline — **B+**
**Strengths:** Clean module separation. 73 unit tests. Hourly refresh with opening lines freeze. Multi-source ingestion.
**Gaps:** RotoWire and weather scrapers are fragile HTML scrapers. No silent-failure alerting on data fetches.

---

### 9. Dashboard / UI — **A-**
**Strengths:** Premium design. LOCK/LEAN/PASS game cards. Best Bets leaderboard. DFS Playbook heat map with barrel%/HH% columns. Conviction system is immediately readable.
**Gaps:** Mobile responsiveness untested. Old "OMEGA v9.0" reference in chat intro still stale.

---

### 10. Overall Architecture — **B+**
**Strengths:** Discipline removing dead signals based on data. Backtest-before-deploy practice. Clean commit history. Operational workflow (4:30 AM capture → lock → audit) is solid.
**Gaps:** No staging environment. Feedback recommendations don't auto-apply. No formal model versioning beyond manual v13.x labels.

---

## What Moves Grades to A Tomorrow

### Hitter Scoring: B → A
- **Individual recent game log form** — pull last 7 days OPS/HR per hitter from MLB StatsAPI game logs. Zero new dependencies. This is the biggest hitter gap.
- Drop TEAM_SNEAKY_STACK (29% hit rate) same way STORM/SURGING were dropped

### Betting EV Engine: C+ → B (over time)
- Let it accumulate 30 real slates of pick data before touching thresholds
- Track result per pick: won/lost/push + EV realized vs projected
- Add a simple ROI tracker to the lock snapshot

### Projected Lineups: B → B+
- Add a second projection source (FantasyPros or ESPN lineups) as a second fallback before the statcast roster fallback
- Add confidence flag: PROJECTED_HIGH_CONF when two sources agree on same lineup

### Signal Auto-Flagging: B → A (feedback loop)
- Auto-flag any signal with 20+ fires and sub-35% hit rate in the audit report with a "⚠️ RETIRE CANDIDATE" tag
- So you don't have to manually review every signal — the model tells you what's dying

### Betting EV Calibration (longer term)
- After 30 slates: run a simple Brier score on OMEGA win probabilities vs actual outcomes
- This gives an objective calibration number for how accurate the probability model actually is

---

## Tomorrow's Session — Priority List

### 🎯 Signal & Scoring (B+ → A-)
1. **Tighten SNEAKY_STACK** — raise xwOBA trigger from 0.345 → 0.365 AND require xwOBA + at least one structural trigger (not xwOBA alone). Keep the signal, make it earn its fires.
2. **Individual hitter L7 game logs** — pull last 7 days OPS/HR per hitter from MLB StatsAPI game logs. Zero new dependencies. Biggest remaining hitter gap.

### 📡 Signal Discipline (B → A)
3. **Signal auto-flagging in audit** — any signal with 20+ fires and sub-35% hit rate auto-gets a ⚠️ RETIRE CANDIDATE tag in the audit output. Model tells you what's dying without you having to manually review.

### 🏗️ Data Pipeline & Architecture (B+ → A)
4. **Silent failure alerting** — if any data fetch (RotoWire, weather, consensus) fails silently, log it visibly to the dashboard status bar rather than returning empty/stale data without warning.
5. **Second lineup projection source** — add FantasyPros or ESPN lineup scraper as fallback between RotoWire and the Statcast roster tier.
6. **Cache pruning** — statcast_cache.json is getting large. Add a daily pruning job that drops players with no PA in 30+ days.
7. **Staging environment** — set up a second Render service (free tier) that deploys from a `staging` branch so changes can be tested before going live.

### 💰 Betting EV Engine (C+ → B)
8. **ROI tracker** — add won/lost/push tracking per LOCK/LEAN pick to the lock snapshot so after 30 slates we have a real hit rate on the EV engine picks.

### 📋 Model Versioning
9. **Formal version file** — replace the manual v13.x comments with a `VERSION` file in the root so the dashboard header pulls the real version automatically.

