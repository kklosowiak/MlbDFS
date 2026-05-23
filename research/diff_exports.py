"""Diff two omega-results exports."""
import json
import sys
from pathlib import Path


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def by_team(d):
    return {t["team"]: t for t in d.get("teams", [])}


def by_pitcher(d):
    return {p["pitcher"]: p for p in d.get("pitchers", [])}


def by_hitter(d):
    return {h["name"]: h for h in d.get("hitters", [])}


def fmt_delta(old, new, key, pct=False):
    o, n = old.get(key), new.get(key)
    if o is None and n is None:
        return ""
    if o is None:
        return f"{key}: -> {n}"
    if n is None:
        return f"{key}: {o} -> -"
    if isinstance(o, (int, float)) and isinstance(n, (int, float)):
        d = n - o
        if pct and o:
            return f"{key}: {o} -> {n} ({d:+.1f}, {100*d/o:+.0f}%)"
        return f"{key}: {o} -> {n} ({d:+.1f})" if d else f"{key}: {o} (flat)"
    if o != n:
        return f"{key}: {o} -> {n}"
    return ""


def main(old_path, new_path):
    old, new = load(old_path), load(new_path)
    print(f"OLD: {Path(old_path).name}  {old.get('timestamp')}")
    print(f"NEW: {Path(new_path).name}  {new.get('timestamp')}")
    print()

    # Teams - biggest stack/conf moves
    ot, nt = by_team(old), by_team(new)
    rows = []
    for team in set(ot) | set(nt):
        o, n = ot.get(team), nt.get(team)
        if not o or not n:
            continue
        ds = (n.get("stack_score") or 0) - (o.get("stack_score") or 0)
        dc = (n.get("attack_conf") or 0) - (o.get("attack_conf") or 0)
        dd = (n.get("divergence") or 0) - (o.get("divergence") or 0)
        rows.append((abs(ds) + abs(dc) * 2 + abs(dd), team, o, n, ds, dc, dd))
    rows.sort(reverse=True)

    print("=== TEAM MOVERS (top 12) ===")
    for _, team, o, n, ds, dc, dd in rows[:12]:
        flags = []
        for k in ("is_whale", "is_blind_spot", "is_burst", "is_trap"):
            if o.get(k) != n.get(k):
                flags.append(f"{k}:{o.get(k)}->{n.get(k)}")
        dqi_o = f"{o.get('dqi_score')}/{o.get('dqi_status')}"
        dqi_n = f"{n.get('dqi_score')}/{n.get('dqi_status')}"
        print(f"\n{team}")
        print(f"  stack {o.get('stack_score')} -> {n.get('stack_score')} ({ds:+.1f})")
        print(f"  conf  {o.get('attack_conf')} -> {n.get('attack_conf')} ({dc:+.0f})")
        print(f"  div   {o.get('divergence')} -> {n.get('divergence')} ({dd:+.0f})")
        if dqi_o != dqi_n:
            print(f"  dqi   {dqi_o} -> {dqi_n}")
        if o.get("opp_pitcher") != n.get("opp_pitcher"):
            print(f"  opp   {o.get('opp_pitcher')} -> {n.get('opp_pitcher')}")
        if o.get("total_signal") != n.get("total_signal"):
            print(f"  total {o.get('total_signal')!r} -> {n.get('total_signal')!r}")
        if flags:
            print(f"  flags {'; '.join(flags)}")

    # Pitchers user cares about
    op, np = by_pitcher(old), by_pitcher(new)
    print("\n=== PITCHERS (tracked) ===")
    names = [
        "Davis Martin", "Jacob Degrom", "Payton Tolle", "Michael Soroka",
        "Kevin Gausman", "Tomoyuki Sugano", "Connor Prielipp", "Tobias Myers",
        "Logan Henderson", "Cristopher Sánchez",
    ]
    for name in names:
        p = next((np[k] for k in np if name.split()[-1] in k and (
            name.split()[0].lower() in k.lower() or "Degrom" in name)), None)
        o = next((op[k] for k in op if name.split()[-1] in k and (
            name.split()[0].lower() in k.lower() or "Degrom" in name)), None)
        if not p:
            continue
        print(f"\n{p['pitcher']}")
        for key in ("alpha_score", "attack_conf", "divergence", "is_trap", "is_hazard", "k_line", "ml_move", "tt_move"):
            if o and o.get(key) != p.get(key):
                print(f"  {key}: {o.get(key)} -> {p.get(key)}")

    # Hitters tracked
    oh, nh = by_hitter(old), by_hitter(new)
    print("\n=== HITTERS (tracked) ===")
    for sub in [
        "Perdomo", "Mccarthy", "Rafaela", "Contreras", "Hicks", "Stowers",
        "Edwards", "Norby", "Moniak", "Gausman",
    ]:
        h = next((nh[k] for k in nh if sub.lower() in k.lower()), None)
        o = next((oh[k] for k in oh if sub.lower() in k.lower()), None)
        if not h:
            continue
        ch = []
        for key in ("player_score", "attack_conf", "matchup_xwoba", "smash_factor", "is_juiced_target"):
            if o and o.get(key) != h.get(key):
                ch.append(f"{key}:{o.get(key)}->{h.get(key)}")
        if ch or not o:
            print(f"{h['name']}: {', '.join(ch) if ch else 'new'}")

    # Trap list change
    print("\n=== TRAP SP flags ===")
    for label, data in [("OLD", old), ("NEW", new)]:
        traps = [p["pitcher"] for p in data["pitchers"] if p.get("is_trap")]
        print(f"{label}: {', '.join(traps) or 'none'}")

    # Whale teams
    print("\n=== WHALE teams ===")
    for label, data in [("OLD", old), ("NEW", new)]:
        w = [(t["team"], t.get("divergence")) for t in data["teams"] if t.get("is_whale")]
        print(f"{label}: {w}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
