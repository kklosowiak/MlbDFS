"""
OMEGA weekly package audit — run when you open Anti Gravity.

Default flow:
  1. git fetch + pull (--ff-only)
  2. unit tests (tests/test_*.py)
  3. replay CONF / prop pressure on latest omega-results export
  4. optional diff vs older export
  5. tail TARGET/JUICE audit log

Usage:
  python research/audit_package.py
  python research/audit_package.py --skip-pull
  python research/audit_package.py --export "C:/Users/konra/Downloads/omega-results(11).json"
  python research/audit_package.py --diff-old "C:/Users/konra/Downloads/omega-results(10).json"
  python research/audit_package.py --since d3e8ce1
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import subprocess
import sys
import traceback
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SINCE = "d3e8ce1"
EXPORT_GLOB = "omega-results*.json"


def _run(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=cwd or ROOT,
        text=True,
        capture_output=True,
        check=False,
    )


def sync_repo(skip: bool) -> tuple[bool, str]:
    if skip:
        return True, "git pull skipped (--skip-pull)"

    fetch = _run(["git", "fetch", "origin"])
    if fetch.returncode != 0:
        return False, fetch.stderr.strip() or fetch.stdout.strip() or "git fetch failed"

    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    branch_name = (branch.stdout or "main").strip() or "main"

    pull = _run(["git", "pull", "--ff-only", "origin", branch_name])
    if pull.returncode != 0:
        msg = (pull.stderr or pull.stdout or "git pull failed").strip()
        return False, msg

    head = _run(["git", "rev-parse", "--short", "HEAD"])
    short = (head.stdout or "?").strip()
    lines = [f"on {branch_name} @ {short}"]
    if pull.stdout.strip():
        lines.append(pull.stdout.strip())
    return True, "\n  ".join(lines)


def git_commits_since(since: str, limit: int = 20) -> list[str]:
    proc = _run(["git", "log", "--oneline", f"{since}..HEAD"])
    if proc.returncode != 0:
        return [f"(could not read log since {since})"]
    rows = [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]
    return rows[:limit] or [f"(no commits after {since})"]


def discover_test_functions() -> list[tuple[str, str, object]]:
    tests_dir = ROOT / "tests"
    out: list[tuple[str, str, object]] = []
    for path in sorted(tests_dir.glob("test_*.py")):
        mod_name = f"_audit_{path.stem}"
        spec = importlib.util.spec_from_file_location(mod_name, path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as exc:
            out.append((path.name, "<import>", exc))
            continue
        for attr in sorted(dir(mod)):
            if attr.startswith("test_"):
                out.append((path.name, attr, getattr(mod, attr)))
    return out


def run_tests() -> tuple[int, int, list[str]]:
    passed = failed = 0
    errors: list[str] = []
    for module, name, fn in discover_test_functions():
        if name == "<import>":
            failed += 1
            errors.append(f"  FAIL import {module}: {fn}")
            continue
        try:
            fn()
            passed += 1
        except Exception:
            failed += 1
            errors.append(f"  FAIL {module}::{name}\n{traceback.format_exc(limit=3)}")
    return passed, failed, errors


def find_latest_export(explicit: Path | None, downloads: Path) -> Path | None:
    if explicit:
        return explicit if explicit.exists() else None
    if not downloads.is_dir():
        return None
    candidates = list(downloads.glob(EXPORT_GLOB))
    if not candidates:
        return None
    return max(candidates, key=lambda p: (p.stat().st_mtime, p.name))


def load_export(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def analyze_export(data: dict) -> dict:
    from utils.attack_confidence import score_pitcher_confidence, score_stack_confidence
    from utils.dqi import calculate_dqi
    from utils.team_prop_pressure import attach_team_prop_pressure

    teams = [dict(t) for t in data.get("teams", [])]
    pitchers = [dict(p) for p in data.get("pitchers", [])]
    hitters = [dict(h) for h in data.get("hitters", [])]

    attach_team_prop_pressure(teams, hitters, confirmed_lineups=None)

    for t in teams:
        dqi_score, dqi_status, _, _ = calculate_dqi(t, pitchers=pitchers)
        if dqi_score is not None:
            t["dqi_score"] = dqi_score
            t["dqi_status"] = dqi_status
        t.setdefault("is_volatile", False)

    prop_labels = Counter(t.get("prop_pressure_label", "?") for t in teams)
    hot_teams = [t["team"] for t in teams if t.get("prop_pressure_label") == "HOT"]

    sp_prop_risk = []
    for p in pitchers:
        p.setdefault("is_volatile", False)
        _, reasons = score_pitcher_confidence(p, teams)
        if any("prop board" in r.lower() for r in reasons):
            sp_prop_risk.append(p.get("pitcher"))

    stack_conf = []
    for t in teams:
        conf, reasons = score_stack_confidence(t, pitchers)
        blended = round((float(t.get("stack_score", 0) or 0) + conf) / 2, 1)
        stack_conf.append((t.get("team"), conf, t.get("stack_score", 0), blended, t.get("prop_pressure_label"), reasons[:1]))

    n_pt = sum(1 for p in pitchers if p.get("is_juiced_target"))
    n_pj = sum(1 for p in pitchers if p.get("is_prop_juice"))
    n_ht = sum(1 for h in hitters if h.get("is_juiced_target"))
    n_hj = sum(1 for h in hitters if h.get("is_prop_juice"))

    return {
        "teams": len(teams),
        "pitchers": len(pitchers),
        "hitters": len(hitters),
        "prop_labels": prop_labels,
        "hot_teams": hot_teams,
        "sp_prop_risk_count": len(sp_prop_risk),
        "sp_prop_risk": sp_prop_risk,
        "sp_total": len(pitchers),
        "target_juice": {"sp_tgt": n_pt, "sp_juice": n_pj, "hit_tgt": n_ht, "hit_juice": n_hj},
        "volatile_teams": sum(1 for t in teams if t.get("is_volatile")),
        "volatile_sp": sum(1 for p in pitchers if p.get("is_volatile")),
        "blind_spot": [t["team"] for t in teams if t.get("is_blind_spot")],
        "stack_conf_top": sorted(stack_conf, key=lambda x: -x[3])[:8],
        "stack_conf_bottom": sorted(stack_conf, key=lambda x: x[3])[:5],
        "timestamp": data.get("timestamp") or data.get("generated_at") or "unknown",
    }


def diff_exports(old_path: Path, new_path: Path) -> None:
    old = load_export(old_path)
    new = load_export(new_path)
    print(f"\n--- EXPORT DIFF: {old_path.name} -> {new_path.name} ---")

    ot = {t["team"]: t for t in old.get("teams", [])}
    nt = {t["team"]: t for t in new.get("teams", [])}
    conf_swings = []
    for team in set(ot) & set(nt):
        dc = (nt[team].get("attack_conf") or 0) - (ot[team].get("attack_conf") or 0)
        if dc:
            conf_swings.append((abs(dc), team, ot[team].get("attack_conf"), nt[team].get("attack_conf"), dc))
    conf_swings.sort(reverse=True)
    print("Top CONF swings (stored in export, not replayed):")
    for _, team, o, n, dc in conf_swings[:8]:
        print(f"  {team[:28]:<28} {o} -> {n} ({dc:+d})")

    op = {p["pitcher"]: p for p in old.get("pitchers", [])}
    np_ = {p["pitcher"]: p for p in new.get("pitchers", [])}
    trap_old = [p for p in op.values() if p.get("is_trap")]
    trap_new = [p for p in np_.values() if p.get("is_trap")]
    print(f"\nTRAP SP: {len(trap_old)} -> {len(trap_new)}")
    if trap_new:
        print("  " + ", ".join(p["pitcher"] for p in trap_new[:10]))


def tail_target_log(lines: int = 5) -> None:
    log_path = ROOT / "logs" / "target_juice_log.csv"
    print(f"\n--- TARGET/JUICE LOG ({log_path.name}) ---")
    if not log_path.exists():
        print("  (no log yet — run a live slate refresh first)")
        return
    for row in log_path.read_text(encoding="utf-8").strip().splitlines()[-lines:]:
        print(f"  {row}")


def print_banner(title: str) -> None:
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def print_analysis(path: Path, stats: dict) -> None:
    print_banner(f"EXPORT REPLAY — {path.name}")
    print(f"  export time: {stats['timestamp']}")
    print(f"  pool: {stats['teams']} teams, {stats['pitchers']} SP, {stats['hitters']} hitters")
    tj = stats["target_juice"]
    print(
        f"  TARGET/JUICE (export flags): SP {tj['sp_tgt']} tgt / {tj['sp_juice']} juice | "
        f"HIT {tj['hit_tgt']} tgt / {tj['hit_juice']} juice"
    )

    print("\n  Prop pressure (recomputed with current code):")
    for label, count in stats["prop_labels"].most_common():
        pct = 100 * count / max(stats["teams"], 1)
        print(f"    {label:<8} {count:>2}  ({pct:.0f}%)")
    if stats["hot_teams"]:
        print(f"    HOT teams: {', '.join(stats['hot_teams'][:6])}")
        if len(stats["hot_teams"]) > 6:
            print(f"               +{len(stats['hot_teams']) - 6} more")
    else:
        print("    HOT teams: none")

    risk_pct = 100 * stats["sp_prop_risk_count"] / max(stats["sp_total"], 1)
    print(
        f"\n  SP with elite prop-board run risk: "
        f"{stats['sp_prop_risk_count']}/{stats['sp_total']} ({risk_pct:.0f}%)"
    )
    if stats["sp_prop_risk"]:
        print("    " + ", ".join(stats["sp_prop_risk"][:8]))

    if stats["blind_spot"]:
        print(f"\n  BLIND SPOT: {', '.join(stats['blind_spot'])}")

    print(f"  Volatile: {stats['volatile_teams']} teams, {stats['volatile_sp']} SP")

    print("\n  Top stack (replayed, sorted by BLENDED):")
    for team, conf, omega, blended, prop, reasons in stats["stack_conf_top"]:
        reason = reasons[0][:55] if reasons else ""
        print(f"    BLENDED: {blended:>5} | CONF: {conf:>3}% | OMEGA: {omega:>5} | {prop or '-':<8} | {team[:20]:<20} | {reason}")

    print("\n  Lowest stack (replayed, sorted by BLENDED):")
    for team, conf, omega, blended, prop, reasons in stats["stack_conf_bottom"]:
        reason = reasons[0][:55] if reasons else ""
        print(f"    BLENDED: {blended:>5} | CONF: {conf:>3}% | OMEGA: {omega:>5} | {prop or '-':<8} | {team[:20]:<20} | {reason}")


def health_checks(stats: dict | None) -> list[str]:
    warnings: list[str] = []
    if stats is None:
        warnings.append("No export found — skip export replay or pass --export")
        return warnings

    hot_pct = 100 * stats["prop_labels"].get("HOT", 0) / max(stats["teams"], 1)
    if hot_pct > 35:
        warnings.append(f"HOT prop pressure on {hot_pct:.0f}% of teams — may be too loose")
    risk_pct = 100 * stats["sp_prop_risk_count"] / max(stats["sp_total"], 1)
    if risk_pct > 40:
        warnings.append(f"Elite prop-board run risk on {risk_pct:.0f}% of SP — check gates")

    tj = stats["target_juice"]
    if stats["hitters"] and tj["hit_tgt"] > 50:
        warnings.append(f"Hitter TARGET count {tj['hit_tgt']} exceeds cap expectation (~45)")
    return warnings


def main() -> int:
    ap = argparse.ArgumentParser(description="OMEGA package audit (git pull + tests + export replay)")
    ap.add_argument("--skip-pull", action="store_true", help="Skip git fetch/pull")
    ap.add_argument("--skip-tests", action="store_true", help="Skip unit tests")
    ap.add_argument("--export", type=Path, default=None, help="omega-results JSON (default: newest in Downloads)")
    ap.add_argument("--downloads", type=Path, default=None, help="Downloads folder (default: ~/Downloads)")
    ap.add_argument("--diff-old", type=Path, default=None, help="Older export to diff against --export")
    ap.add_argument("--since", default=DEFAULT_SINCE, help=f"Show commits since ref (default: {DEFAULT_SINCE})")
    ap.add_argument("--no-export", action="store_true", help="Skip export replay")
    args = ap.parse_args()

    downloads = args.downloads or (Path.home() / "Downloads")

    print_banner("OMEGA PACKAGE AUDIT")
    print(f"  {ROOT}")
    print(f"  started: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}")

    print_banner("GIT SYNC")
    ok, msg = sync_repo(args.skip_pull)
    print(f"  {msg}")
    if not ok:
        print("  WARNING: pull failed — continuing with local code")

    print("\n  Commits in this package:")
    for line in git_commits_since(args.since):
        print(f"    {line}")

    failed = 0
    if not args.skip_tests:
        print_banner("UNIT TESTS")
        passed, failed, errors = run_tests()
        print(f"  {passed} passed, {failed} failed")
        if errors:
            print("\n".join(errors))
        if failed:
            print("\n  >>> Fix failing tests before trusting replay <<<")

    stats = None
    export_path = None
    if not args.no_export:
        export_path = find_latest_export(args.export, downloads)
        if export_path is None:
            print_banner("EXPORT REPLAY")
            print(f"  No export found in {downloads} (glob: {EXPORT_GLOB})")
            print("  Export JSON from dashboard or pass --export PATH")
        else:
            stats = analyze_export(load_export(export_path))
            print_analysis(export_path, stats)
            if args.diff_old and args.diff_old.exists():
                diff_exports(args.diff_old, export_path)
            elif args.diff_old:
                print(f"\n  diff-old not found: {args.diff_old}")

    tail_target_log()

    warnings = health_checks(stats)
    print_banner("SUMMARY")
    if warnings:
        for w in warnings:
            print(f"  ⚠ {w}")
    else:
        print("  No automatic warnings.")
    print("\n  Anti Gravity prompt (audit-only):")
    print("    Run research/audit_package.py and review SUMMARY.")
    print("    Flag over-triggered signals; do not change code unless I say fix.")

    return 1 if (not args.skip_tests and failed) else 0  # type: ignore[possibly-undefined]


if __name__ == "__main__":
    sys.exit(main())
