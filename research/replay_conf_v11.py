"""
Replay CONF v11 on a saved omega-results JSON (no live Odds API needed).

Usage:
  python research/replay_conf_v11.py "C:/Users/konra/Downloads/omega-results(11).json"
  python research/replay_conf_v11.py path/to/export.json --teams MIA,BOS
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from utils.attack_confidence import score_pitcher_confidence, score_stack_confidence
from utils.dqi import calculate_dqi
from utils.team_prop_pressure import attach_team_prop_pressure


def load_export(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def replay(data: dict, team_filter: set[str] | None = None):
    teams = [dict(t) for t in data.get("teams", [])]
    pitchers = [dict(p) for p in data.get("pitchers", [])]
    hitters = [dict(h) for h in data.get("hitters", [])]

    attach_team_prop_pressure(teams, hitters, confirmed_lineups=None)

    for t in teams:
        dqi_score, dqi_status, pos, warn = calculate_dqi(t, pitchers=pitchers)
        if dqi_score is not None:
            t["dqi_score"] = dqi_score
            t["dqi_status"] = dqi_status
            t["dqi_pos_factors"] = pos
            t["dqi_warn_factors"] = warn
        t.setdefault("is_volatile", False)

    rows = []
    for t in teams:
        abbr = (t.get("team") or "")[:3].upper()
        if team_filter and abbr not in team_filter and t.get("team") not in team_filter:
            continue
        old_conf = t.get("attack_conf")
        old_reasons = t.get("attack_reasons") or []
        new_conf, new_reasons = score_stack_confidence(t, pitchers)
        rows.append(
            {
                "kind": "team",
                "name": t.get("team"),
                "omega": t.get("stack_score"),
                "old_conf": old_conf,
                "new_conf": new_conf,
                "delta": (new_conf - old_conf) if old_conf is not None else None,
                "prop": t.get("prop_pressure_label"),
                "prop_score": t.get("prop_pressure_score"),
                "dqi": t.get("dqi_status"),
                "old_top_reason": old_reasons[0][:70] if old_reasons else "",
                "new_top_reason": new_reasons[0][:70] if new_reasons else "",
            }
        )

    for p in pitchers:
        old_conf = p.get("attack_conf")
        p.setdefault("is_volatile", False)
        new_conf, new_reasons = score_pitcher_confidence(p, teams)
        omega = p.get("alpha_score")
        if isinstance(omega, dict):
            omega = omega.get("final", omega.get("score"))
        rows.append(
            {
                "kind": "sp",
                "name": p.get("pitcher"),
                "omega": omega,
                "old_conf": old_conf,
                "new_conf": new_conf,
                "delta": (new_conf - old_conf) if old_conf is not None else None,
                "prop": "K-TGT" if p.get("is_juiced_target") else ("K-JUICE" if p.get("is_prop_juice") else ""),
                "prop_score": p.get("_juice_gap"),
                "dqi": "",
                "old_top_reason": (p.get("attack_reasons") or [""])[0][:70],
                "new_top_reason": new_reasons[0][:70] if new_reasons else "",
            }
        )

    return rows


def _fmt_omega(v):
    if isinstance(v, dict):
        v = v.get("final", v.get("score"))
    if v is None:
        return "—"
    try:
        return f"{float(v):.1f}"
    except (TypeError, ValueError):
        return str(v)


def print_report(path: Path, rows: list[dict]):
    print(f"\n=== CONF v11 REPLAY: {path.name} ===")
    stacks = sorted(
        [r for r in rows if r["kind"] == "team"],
        key=lambda x: -(x["new_conf"] or 0),
    )
    print("\n--- STACKS (new CONF desc) ---")
    print(f"{'TEAM':<28} {'OMEGA':>6} {'OLD':>4} {'NEW':>4} {'D':>4}  PROP    DQI     TOP NEW REASON")
    for r in stacks[:15]:
        d = r["delta"]
        ds = f"{d:+d}" if d is not None else "—"
        print(
            f"{r['name'][:28]:<28} {_fmt_omega(r['omega']):>6} "
            f"{r['old_conf'] if r['old_conf'] is not None else '—':>4} "
            f"{r['new_conf']:>4} {ds:>4}  "
            f"{(r['prop'] or '—'):<6} {(r['dqi'] or '—'):<6} "
            f"{r['new_top_reason']}"
        )

    sps = sorted(
        [r for r in rows if r["kind"] == "sp"],
        key=lambda x: -(x["new_conf"] or 0),
    )
    print("\n--- SP (new CONF desc, top 12) ---")
    print(f"{'PITCHER':<24} {'OMEGA':>6} {'OLD':>4} {'NEW':>4} {'D':>4}  K-PROP  TOP NEW REASON")
    for r in sps[:12]:
        d = r["delta"]
        ds = f"{d:+d}" if d is not None else "—"
        print(
            f"{r['name'][:24]:<24} {_fmt_omega(r['omega']):>6} "
            f"{r['old_conf'] if r['old_conf'] is not None else '—':>4} "
            f"{r['new_conf']:>4} {ds:>4}  "
            f"{(r['prop'] or '—'):<6} {r['new_top_reason']}"
        )

    big_moves = sorted(
        [r for r in rows if r["delta"] is not None],
        key=lambda x: abs(x["delta"]),
        reverse=True,
    )[:8]
    if big_moves:
        print("\n--- BIGGEST CONF SWINGS ---")
        for r in big_moves:
            print(
                f"  {r['kind'].upper()} {r['name']}: "
                f"{r['old_conf']} -> {r['new_conf']} ({r['delta']:+d}) "
                f"[{r['prop'] or '—'} / DQI {r['dqi'] or '—'}]"
            )


def main():
    ap = argparse.ArgumentParser(description="Replay CONF v11 on saved export JSON")
    ap.add_argument("export", type=Path, help="Path to omega-results JSON")
    ap.add_argument(
        "--teams",
        type=str,
        default="",
        help="Comma-separated team abbrev filter (e.g. MIA,BOS,MIN)",
    )
    args = ap.parse_args()
    if not args.export.exists():
        print(f"File not found: {args.export}")
        sys.exit(1)
    filt = {x.strip().upper() for x in args.teams.split(",") if x.strip()} or None
    data = load_export(args.export)
    rows = replay(data, filt)
    print_report(args.export, rows)


if __name__ == "__main__":
    main()
