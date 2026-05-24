# OMEGA — Deploy later (do not run mid-slate)

**Live site (2026-05-21):** `207e354` — manual Vegas opens, ML moves working. User cancelled mid-slate deploys; slate looks good.

**When to deploy:** Quiet window — after lock or next morning. **Say "deploy now" in the original Package A chat** before push/Render.

**Full spec:** `docs/PACKAGE_ROLLOUT.md` (UI batch details)

---

## Package A — deploy together (one PR / one Render deploy)

### 1. Automatic opening lines — `47da038` (on main)

- 4:30 AM `capture_opening=True`, `opening_lines_YYYY-MM-DD.json`, snapshot backfill, `pair_key`
- Routine refresh must NOT overwrite frozen `opening_*`
- **Do NOT re-add:** slow refresh, refresh-reset, skip Statcast, progress UI

**Verify:** Miami ~-36, Detroit ~-25 ML moves.

---

### 2. Stack TRAP / DQI alignment — *implement*

See `engine/sharps_weighting.py`, `utils/dqi.py`, `templates/index.html`, `tests/test_trap_gate.py`

- Exempt sharp steam; exempt elite stacks (≥110); chalk-only trap conditions
- DQI: `is_trap = team OR opp pitcher`; labels Stack Chalk vs TRAP SP
- Stack **⚠️ CHALK** · Pitcher **🚨 TRAP SP**

**Verify:** TOR/ARI STEAM + DQI TRUST → no stack TRAP/CHALK false positive.

---

### 3. Stack score scale — cap **150**, NOT 100

- `sharps_weighting.py`: `combined_mult = min(..., 1.35)`
- `main.py`: `final_stack_score = min(150.0, ...)` after all post-processing
- Optional: `stack_score_raw` in team JSON
- Keep percentile badges; keep UI tiers 85/98/110

**Verify:** No stack_score > 150; top teams ~130–150 not 180+.

---

### 4. OMEGA UI Package Rollout — `docs/PACKAGE_ROLLOUT.md`

| Item | Status | Action |
|------|--------|--------|
| **Attack Plan sub-tabs fix** | Ready in `templates/index.html` | Deploy + QA all 5 tabs (Ultimate · Stacks · Pitchers · Traps · Leverage) |
| **Attack conf (`attack_conf`) column** | Pending UI | Add **CONF** column to Pitchers + Teams matrices; data already in `/api/results` from `slate_report_generator.py` |

**Attack conf v1 spec:**
- Column **CONF** (or **ATK**) after OMEGA — integer 0–100, bands ≥70 green / 40–69 neutral / <40 muted
- Tooltip or hover: first 3 `attack_reasons` lines
- Do **not** change default table sort (keep alpha_score / stack_score primary)

**QA:** See checklist in `docs/PACKAGE_ROLLOUT.md` §1–2.

---

### 5. GPP Signal Contradiction Overrides — *implement next morning*

See [test_signal_exclusions.py](file:///c:/Users/konra/OneDrive/Desktop/Antigravity/Projects/MlbDFS/tests/test_signal_exclusions.py) for details and unit tests.

- **Trap vs. Sneaky**: If a team is flagged as a Chalk Trap (`is_trap` is True), automatically force `is_sneaky` to `False`.
- **Fade Risk vs. GPP Targets**: If a team is flagged as a GPP Fade Risk (`is_fade_risk` is True), automatically force `is_physics_override` and `is_anti_chalk_smash` to `False`.
- Prevents cockpit views from showing conflicting "Fade" vs. "Buy" markers for the same team.

---

## Do NOT tonight (unless added later)

- Package B: weak-stack market cap, splits hardening, game-started audit
- Cap stack scores at 100
- Push/deploy before "deploy now"

---

## Post-deploy verify

1. Render Manual Deploy → latest `main`
2. One **Refresh Slate** (~1 min)
3. Console:

```javascript
(async () => {
  const data = await (await fetch('/api/results')).json();
  const t = (n) => data.teams?.find(x => (x.team||'').includes(n));
  for (const n of ['Miami','Detroit','Toronto','Arizona']) {
    const x = t(n);
    console.log(n, { stack_score: x?.stack_score, ml_move: x?.ml_move, is_trap: x?.is_trap, dqi: x?.dqi_score, attack_conf: x?.attack_conf });
  }
  console.log('max stack_score', Math.max(...(data.teams||[]).map(x => x.stack_score||0)));
})();
```

4. Attack Plan: click all 5 sub-tabs
5. Spot-check CONF column vs JSON `attack_conf`

**Rollback:** redeploy `207e354`

---

## Paste into Package A chat

```
Deploy Package A per OMEGA_DEPLOY_LATER.md + docs/PACKAGE_ROLLOUT.md:
opens (47da038) + TRAP/DQI + 150 stack cap + UI package (Attack Plan tabs QA + attack_conf CONF columns).
Wait for my "deploy now" before push.
```
