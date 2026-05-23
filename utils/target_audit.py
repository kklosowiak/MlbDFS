"""Lightweight slate audit log for TARGET vs JUICE counts (post-mortem hook)."""

import csv
import os
from datetime import date, datetime

from config import config


def log_target_counts(pitchers, hitters):
    log_dir = config.LOG_DIR
    os.makedirs(log_dir, exist_ok=True)
    path = os.path.join(log_dir, "target_juice_log.csv")
    exists = os.path.exists(path)
    n_pt = sum(1 for p in pitchers or [] if p.get("is_juiced_target"))
    n_pj = sum(1 for p in pitchers or [] if p.get("is_prop_juice"))
    n_ht = sum(1 for h in hitters or [] if h.get("is_juiced_target"))
    n_hj = sum(1 for h in hitters or [] if h.get("is_prop_juice"))
    row = {
        "date": date.today().isoformat(),
        "at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "pitcher_target": n_pt,
        "pitcher_juice": n_pj,
        "pitcher_total": len(pitchers or []),
        "hitter_target": n_ht,
        "hitter_juice": n_hj,
        "hitter_total": len(hitters or []),
    }
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            w.writeheader()
        w.writerow(row)
    print(
        f"[TARGET-AUDIT]: SP {n_pt}/{len(pitchers or [])} TARGET, {n_pj} JUICE | "
        f"HIT {n_ht}/{len(hitters or [])} TARGET, {n_hj} JUICE"
    )
