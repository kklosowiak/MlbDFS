# OMEGA Package A — deferred deploy

**Product:** OMEGA / MlbDFS — MLB DFS decision intelligence (stacks, SP, one-offs). Hand-build DK lineups.

**Live site:** Deploying Package A (Konrad approved **deploy now**).

**Rule:** Package A shipped — see deploy checklist below for post-deploy QA.

**NOT in scope:** DK salaries, optimizer, lineup export, `main.py` / `server.py` refactors.

---

## Package A — one deploy, all items together

### 1) Automatic opening lines (`47da038` — already on GitHub main)

**Goal:** True morning ML/TT baselines without pasting FantasyLabs every day.

- **4:30 AM ET:** `perform_fetch(capture_opening=True)` freezes opens for the slate day.
- **Files:** `opening_lines_YYYY-MM-DD.json` + legacy `opening_lines.json`.
- **Routine refresh:** Updates current lines only — never overwrites `opening_*`.
- **Late games / new `game_id`:** Backfill from earliest same-day `snapshot_*.json` (max 30 files) or inherit via matchup `pair_key` (`away|home`).
- **Optional backup:** `data/vegas_opens_manual.json` still overrides if present for that date.

**Explicitly NOT included** (broke refresh before):

- Slow refresh / skip Statcast
- Odds API timeout changes
- `/api/refresh-reset`
- Refresh progress UI

**Verify:** Miami ~-36, Detroit ~-25 `ml_move`; not all EVEN after restart.

---

### 2) Stack TRAP / DQI alignment — **shipped**

**Problem:** 🚨 TRAP on stacks (e.g. Toronto, Arizona, Miami) while DQI shows TRUST. Talent Floor Gate treats SHARK/STEAM as generic “inflation.” DQI “Public Chalk Trap (-20)” never shows because DQI only checked opposing **pitcher** trap, not **stack** trap.

**`engine/sharps_weighting.py` — Talent Floor Gate**

- Exempt sharp steam: no stack trap if `(is_steam or is_shark) and ml_move <= -10`
- Exempt elite stacks: no trap if stack score ≥ 110 (before trap multiplier)
- Chalk-only: weak offense (`team_xwoba < 0.300` OR displayed `physics_score < 25`) and public-style pressure (`ml_move >= 5` or high divergence **without** steam/shark in team’s favor)
- Stop treating all market signals as generic “inflation” for trap

**`utils/dqi.py`**

- `is_trap = team.is_trap OR opp_pitcher.is_trap` (do not replace team with pitcher only)
- Warning: **“Stack Chalk Warning (-20)”** for stack trap; pitcher trap stays separate

**`templates/index.html`**

- Stack row: **⚠️ CHALK** (not 🚨 TRAP on stacks)
- Pitcher row: **🚨 TRAP SP** (+ `trap_type`)

**`tests/test_trap_gate.py`** — steam exempt, chalk still flags

**Verify:** TOR / ARI / **MIA with SHARK + negative `ml_move` + DQI TRUST** → no false stack TRAP/CHALK.

**Tonight (pre-deploy):** Miami `is_trap` + `is_shark` together is expected — use **Sandy + mini MIA**, not full MIA stack. After #2 ships, SHARK steam on the dog should **not** show stack CHALK.

---

### 3) Stack score scale — cap at **150**, NOT 100

**Problem:** Scores run too high (e.g. Arizona ~188); sneaky stacks look far behind.

**`engine/sharps_weighting.py`**

- Cap combined multipliers before final stack score:
  - `combined = multiplier × div × convergence × trap × magnetism × bullpen_skill`
  - `combined = min(combined, 1.35)`
  - `final_omega = score × combined`

**`main.py`**

- After all post-processing (SHARK ×1.15, O-DIV, debut, sentiment, etc.):
  - `final_stack_score = min(150.0, final_stack_score)`
- Optional: `stack_score_raw` (pre-cap) + `stack_score` (display/sort) on team JSON

**Do NOT cap at 100** — breaks UI tiers (85 / 98 / 110 elite bands).

Keep: Slate percentile badges (#rank · Pxx); signals (STEAM, SHARK, DQI, etc.).

**Verify:** No `stack_score` > 150; top teams ~130–150, not 180+.

---

### 4) UI rollout (this file §4a–4b)

#### 4a) Attack Plan sub-tabs fix — **ready in code**

**Problem:** Only “Ultimate Suggestion” worked; other tabs highlighted wrong section.

**Fix:** `templates/index.html` — `setActiveAnalysisTab(tab, card)` per section (closure bug).

**QA after deploy:** Attack Plan → click all five: **Ultimate · Stacks · Pitchers · Traps · Leverage**. Each shows the right section from `reports/slate_analysis.md`.

**Note:** Static `reports/dashboard.html` has no sub-tabs; web app only (`/api/analysis`).

#### 4b) Attack confidence (`attack_conf`) on dashboard — **shipped**

Data already in `/api/results` (`attack_conf`, `attack_reasons` on pitchers + teams from `utils/slate_report_generator.py`). Not on matrices today.

**Pitchers + Teams matrices:**

- Column **CONF** (or **ATK**) after OMEGA — integer 0–100
- Color: ≥70 green, 40–69 neutral, &lt;40 muted
- Tooltip/hover: first 3 `attack_reasons` lines
- **Do not** change default table sort (keep `alpha_score` / `stack_score` primary; CONF is decision layer)

---

## Deploy checklist (when Konrad says deploy now)

1. Run full slate refresh after deploy.
2. **Opens:** MIA ~-36, DET ~-25 `ml_move` (not all EVEN).
3. **Trap:** TOR/MIA SHARK + negative ML + DQI TRUST → no false stack CHALK.
4. **Scores:** Nothing &gt; 150; Arizona ~130–150 not ~180+.
5. **Attack Plan:** All five sub-tabs work.
6. **CONF column** visible on pitcher/team tables.

---

## Backlog (post–Package A)

- [ ] Mirror Attack Plan sub-tabs in `dashboard_generator.py` static export
- [ ] Export/download omega JSON: legend for `attack_conf` vs `alpha_score` vs CHALK vs TRAP SP
- [ ] DQI + attack_conf cross-link in hub
