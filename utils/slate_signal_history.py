"""Intraday attack_conf / stack_score snapshots for stability (Δ) column."""

from __future__ import annotations

import json
import os
from datetime import date, datetime

VOLATILE_CONF_SWING = 15


def _today():
    return date.today().isoformat()


def _path(reports_dir):
    return os.path.join(reports_dir, "slate_signal_history.json")


def load_history(reports_dir):
    path = _path(reports_dir)
    if not os.path.exists(path):
        return {"slate_date": _today(), "teams": {}, "pitchers": {}}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {"slate_date": _today(), "teams": {}, "pitchers": {}}
    if data.get("slate_date") != _today():
        return {"slate_date": _today(), "teams": {}, "pitchers": {}}
    return data


def _first_entry(entries):
    if not entries:
        return None
    return entries[0]


def persist_slate_signals(reports_dir, teams, pitchers):
    """Append current CONF/stack to history; set open_* on first sighting today."""
    data = load_history(reports_dir)
    now = datetime.now().isoformat()

    for t in teams or []:
        key = t.get("team") or ""
        if not key:
            continue
        conf = int(t.get("attack_conf") or 0)
        stk = float(t.get("stack_score") or 0)
        xw = float(t.get("team_xwoba") or 0)
        rec = data["teams"].setdefault(
            key,
            {"open_conf": conf, "open_stack": stk, "open_xwoba": xw, "entries": []},
        )
        if not rec.get("entries"):
            rec["open_conf"] = conf
            rec["open_stack"] = stk
            rec["open_xwoba"] = xw
        rec["entries"].append(
            {"at": now, "attack_conf": conf, "stack_score": stk, "team_xwoba": xw}
        )
        if len(rec["entries"]) > 48:
            rec["entries"] = rec["entries"][-48:]

    for p in pitchers or []:
        key = p.get("pitcher") or ""
        if not key:
            continue
        conf = int(p.get("attack_conf") or 0)
        alpha = float(p.get("alpha_score") or 0)
        rec = data["pitchers"].setdefault(
            key,
            {"open_conf": conf, "open_alpha": alpha, "entries": []},
        )
        if not rec.get("entries"):
            rec["open_conf"] = conf
            rec["open_alpha"] = alpha
        rec["entries"].append({"at": now, "attack_conf": conf, "alpha_score": alpha})
        if len(rec["entries"]) > 48:
            rec["entries"] = rec["entries"][-48:]

    try:
        os.makedirs(reports_dir, exist_ok=True)
        with open(_path(reports_dir), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[SIGNAL-HIST]: persist failed: {e}")


def attach_signal_deltas(reports_dir, teams, pitchers):
    """Mutates team/pitcher dicts with conf_delta, is_volatile, stack_delta."""
    data = load_history(reports_dir)

    for t in teams or []:
        key = t.get("team") or ""
        rec = data.get("teams", {}).get(key)
        conf = int(t.get("attack_conf") or 0)
        if not rec:
            t["conf_delta"] = 0
            t["stack_delta"] = 0
            t["is_volatile"] = False
            continue
        open_conf = int(rec.get("open_conf", conf))
        open_stk = float(rec.get("open_stack", t.get("stack_score", 0)))
        t["conf_delta"] = conf - open_conf
        t["stack_delta"] = round(float(t.get("stack_score", 0)) - open_stk, 1)
        swings = [abs(e.get("attack_conf", conf) - open_conf) for e in rec.get("entries", [])]
        t["is_volatile"] = max(swings + [abs(t["conf_delta"])]) >= VOLATILE_CONF_SWING

    for p in pitchers or []:
        key = p.get("pitcher") or ""
        rec = data.get("pitchers", {}).get(key)
        conf = int(p.get("attack_conf") or 0)
        if not rec:
            p["conf_delta"] = 0
            p["is_volatile"] = False
            continue
        open_conf = int(rec.get("open_conf", conf))
        p["conf_delta"] = conf - open_conf
        swings = [abs(e.get("attack_conf", conf) - open_conf) for e in rec.get("entries", [])]
        p["is_volatile"] = max(swings + [abs(p["conf_delta"])]) >= VOLATILE_CONF_SWING
