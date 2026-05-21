# OMEGA Changelog

## 2026-05-21 — P0 + Safe P1 Audit Cleanup

### Security
- Removed hardcoded `ODDS_API_KEY` fallback from `config.py`; ingestion requires env var.
- Removed default `OMEGA_PASSWORD` / `BANKROLL_PIN` fallbacks in `server.py`.
- Sanitized `/api/debug-env` — no key length, prefix, or snapshot content preview.

### DQI (trust)
- Centralized `calculate_dqi` in `utils/dqi.py` (30-point baseline, divergence gate >= 10%).
- `dqi_history.json` now writes on refresh/analysis/lock only — not on every GET `/api/results`.
- Chat system prompt and handbook aligned to 30-point DQI model.

### Signals
- **`is_sharp` logic tightened:** money >= 65% **and** divergence >= 10% (display: **HEAVY $**). JSON field name unchanged.
- **Display dedupe:** SHARK hides HEAVY $; STEAM hides STORM on team rows.

### UX
- Sidebar **data health** strip (snapshot age, splits status, lineups confirmed %).
- New `GET /api/data-health`.
- Slate **percentile badges** on pitcher/stack/hitter OMEGA columns (`#rank · Pxx`).
- Learning tab: empty-state banner + low-sample warnings on hit-rate subs.

### Bugfixes
- Removed duplicate hitter purge log in `main.py`.
