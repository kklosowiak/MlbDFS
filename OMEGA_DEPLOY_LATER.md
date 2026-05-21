# OMEGA — Deploy later (do not run mid-slate)

**Live site (2026-05-21):** `207e354` — manual Vegas opens, ML moves working. User cancelled mid-slate deploys; slate looks good.

**When to deploy:** Quiet window — e.g. **~9 PM ET after lock**, or next morning before slate.

---

## Queue (deploy together or back-to-back)

### 1. Automatic opening lines — `47da038`

| | |
|---|---|
| **What** | 4:30 AM freeze, dated `opening_lines_YYYY-MM-DD.json`, snapshot backfill, `pair_key` |
| **Not included** | Slow refresh, refresh-reset, skip Statcast, progress UI |
| **After deploy** | One Refresh; optional: retire `vegas_opens_manual.json` once 4:30 is trusted |

**Verify:** Miami ~-36, Detroit ~-25 ML moves (console audit script in chat history).

---

### 2. Stack TRAP / DQI alignment — *not committed yet*

**Problem:** 🚨 TRAP on stacks (TOR, ARI) conflicts with high DQI TRUST. Talent Floor Gate treats SHARK/STEAM as “inflation” and flags sharp-backed teams. DQI never shows “Public Chalk Trap” because `calculate_dqi` only uses **opposing pitcher** `is_trap`, not stack trap.

**Agreed fix (brainstorm 2026-05-21):**

#### `engine/sharps_weighting.py` — Talent Floor Gate

- **Exempt sharp steam:** no TRAP if `(is_steam or is_shark) and ml_move <= -10`
- **Exempt elite stacks:** no TRAP if `final` stack score ≥ 110 (before trap mult)
- **Chalk-only conditions:** require weak offense (`team_xwoba < 0.300` OR displayed `physics_score < 25`) **and** public-style pressure (`ml_move >= 5` or high div without steam/shark favoring team)
- Stop treating all of `is_whale|is_storm|is_shark|is_steam|is_sharp|div>12` as generic “inflation” for trap

#### `utils/dqi.py`

- `is_trap = team.is_trap OR opp_pitcher.is_trap` (do not replace team with pitcher only)
- Warning label: **“Stack Chalk Warning (-20)”** when stack trap; keep pitcher trap separate

#### `templates/index.html` (optional UX)

- Stack row: **⚠️ CHALK** (weak physics + public hype)
- Pitcher row: keep **🚨 TRAP SP** (+ `trap_type`)

**Verify after deploy:**

- Toronto / Arizona with STEAM + negative `ml_move` + DQI TRUST → **no** stack TRAP
- True chalk (weak PHY, line moving against, no sharp steam) → still flagged

---

## Render steps

1. **Manual Deploy** → latest `main` (includes `47da038` + trap fix commit when implemented).
2. Wait for **Deploy live**.
3. **One Refresh Slate**.
4. Run ML + TRAP console checks (below).

```javascript
(async () => {
  const data = await (await fetch('/api/results')).json();
  const t = (n) => data.teams?.find(x => (x.team||'').includes(n));
  for (const n of ['Miami','Detroit','Toronto','Arizona']) {
    const x = t(n);
    console.log(n, { ml_move: x?.ml_move, is_trap: x?.is_trap, dqi: x?.dqi_score, steam: x?.is_steam });
  }
})();
```

Expect: ML moves intact; TOR/ARI `is_trap: false` if steam + TRUST DQI.

---

## Rollback

- **Opens only broken:** redeploy `207e354`
- **Trap fix too loose/tight:** revert `sharps_weighting.py` + `dqi.py` commit only

---

## Paste into this chat later

```
Continue OMEGA deploy-later queue per OMEGA_DEPLOY_LATER.md:
1) Deploy 47da038 opening lines if not live
2) Implement stack TRAP / DQI alignment per section 2
Live is 207e354 unless already upgraded. One refresh + console verify after deploy.
```
