"""Quick slate export analyzer."""
import json
import sys
from pathlib import Path

def safe(s):
    return (s or "").encode("ascii", "backslashreplace").decode()

def main(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    print("timestamp:", d.get("timestamp"))
    teams = d.get("teams", [])
    pitchers = d.get("pitchers", [])
    hitters = d.get("hitters", [])

    teams_s = sorted(teams, key=lambda t: t.get("stack_score", 0), reverse=True)
    print("\n=== TOP 12 STACKS ===")
    for t in teams_s[:12]:
        sig = []
        if t.get("is_whale"):
            sig.append("WHALE")
        if t.get("is_blind_spot"):
            sig.append("BLIND")
        if t.get("is_burst"):
            sig.append("BURST")
        if t.get("is_shark"):
            sig.append("SHARK")
        if t.get("is_sharp"):
            sig.append("HEAVY")
        if t.get("is_trap"):
            sig.append("STACK_TRAP")
        team = (t.get("team") or "")[:22]
        opp = (t.get("opp_pitcher") or "")[:18]
        ts = safe(t.get("total_signal") or "")
        print(
            f"{team:22} stk={t.get('stack_score', 0):5.1f} conf={t.get('attack_conf', 0):3} "
            f"div={t.get('divergence', 0):+3} dqi={t.get('dqi_score')}/{t.get('dqi_status')} "
            f"vs {opp:18} {' '.join(sig)} tt={t.get('tt_move')} itt={t.get('implied_total')} {ts}"
        )

    print("\n=== TRAP SP ===")
    for p in sorted(pitchers, key=lambda x: -x.get("alpha_score", 0)):
        if p.get("is_trap"):
            print(
                f"{p['pitcher'][:20]:20} vs {(p.get('opponent') or '')[:18]:18} "
                f"OMEGA={p.get('alpha_score')} conf={p.get('attack_conf')} "
                f"div={p.get('divergence', 0):+3} trap={p.get('trap_type')} phys={p.get('physics_score')}"
            )

    print("\n=== TOP SP (conf>=80, no trap) ===")
    for p in sorted(pitchers, key=lambda x: -x.get("attack_conf", 0)):
        if p.get("attack_conf", 0) >= 80 and not p.get("is_trap"):
            print(
                f"{p['pitcher'][:20]:20} vs {(p.get('opponent') or '')[:18]:18} "
                f"OMEGA={p.get('alpha_score')} conf={p.get('attack_conf')} "
                f"div={p.get('divergence', 0):+3} form={p.get('form_status')} TARGET={p.get('is_juiced_target')}"
            )

    print("\n=== SP FADES (trap or conf<=40) ===")
    for p in pitchers:
        if p.get("is_trap") or p.get("attack_conf", 50) <= 40:
            print(
                f"{p['pitcher'][:20]:20} conf={p.get('attack_conf')} trap={p.get('is_trap')} "
                f"hazard={p.get('is_hazard')} paradox={p.get('is_paradox')}"
            )

    print("\n=== TOTALS SIGNALS (sample teams) ===")
    seen = set()
    for t in teams:
        ts = t.get("total_signal") or ""
        if ts and ts not in seen:
            seen.add(ts)
            print(safe(ts), "-", t.get("team"))

    pt = sum(1 for p in pitchers if p.get("is_juiced_target"))
    ht = sum(1 for h in hitters if h.get("is_juiced_target"))
    print(f"\nTARGET counts: pitchers {pt}/{len(pitchers)}, hitters {ht}/{len(hitters)}")

    top_teams = {t["team"] for t in teams_s[:6]}
    print("\n=== TOP HITTERS (top 6 stack teams, score>=100) ===")
    hh = [h for h in hitters if h.get("team") in top_teams and h.get("player_score", 0) >= 100]
    hh.sort(key=lambda x: -x.get("player_score", 0))
    for h in hh[:20]:
        print(
            f"{(h.get('name') or '')[:18]:18} {(h.get('team') or '')[:20]:20} "
            f"sc={h.get('player_score', 0):5.1f} xw={h.get('matchup_xwoba', 0):.3f} "
            f"TARGET={h.get('is_juiced_target')} vs {(h.get('opp_pitcher') or '')[:15]}"
        )

    # DQI TRUST
    print("\n=== DQI TRUST (div>=10) ===")
    for t in sorted(teams, key=lambda x: -x.get("dqi_score", 0)):
        if (t.get("divergence") or 0) >= 10 and t.get("dqi_status") == "TRUST":
            pos = t.get("dqi_positive_factors") or []
            warn = t.get("dqi_warning_factors") or []
            print(f"{t.get('team')}: {t.get('dqi_score')}% - pos={pos[:3]} warn={warn}")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else r"c:\Users\konra\Downloads\omega-results(7).json")
