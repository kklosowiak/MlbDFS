# OMEGA — Scheduled deploy (do not run mid-slate)

**Status (2026-05-21):** User cancelled Render deploy of `47da038`. **Live site should stay on `207e354`** (manual Vegas opens — working).

---

## When to deploy

**~9:00 PM ET** (after DK lock / lineup decisions done for the day).

---

## What to deploy

| | |
|---|---|
| **Commit** | `47da038` — Automatic opening lines: 4:30 freeze, snapshot backfill, dated storage |
| **Stays on** | `207e354` until you deploy |
| **Not included** | Slow refresh, refresh-reset, skip Statcast, progress UI |

---

## Render steps (~5 min)

1. **Manual Deploy** → latest commit on `main` (`47da038`).
2. Wait for **Deploy live** (green check).
3. Open https://mlbdfs.onrender.com → **one Refresh Slate**.
4. Console check (logged in):

```javascript
(async () => {
  const data = await (await fetch('/api/results')).json();
  const t = (n) => data.teams?.find(x => (x.team||'').includes(n));
  ['Miami','Detroit','Arizona'].forEach(n => console.log(n, t(n)?.ml_move, t(n)?.is_steam));
})();
```

Expect non-zero `ml_move` on teams that moved (not all EVEN).

5. **Optional:** Remove or update `data/vegas_opens_manual.json` after a few days once 4:30 AM capture is trusted.

---

## If something breaks

- Render → deploy previous commit **`207e354`** (manual opens only).
- Or cancel deploy before it goes live.

---

## Paste into a new chat (optional)

```
Deploy OMEGA commit 47da038 per OMEGA_DEPLOY_LATER.md. Live is 207e354. Verify ML moves after one refresh; do not change refresh pipeline.
```
