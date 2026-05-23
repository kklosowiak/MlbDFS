import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = Path(r"C:\Users\konra\Downloads\omega-results(11).json")
d = json.load(open(p, encoding="utf-8"))
print("timestamp", d.get("timestamp"))
print("counts", len(d.get("pitchers", [])), "teams", len(d.get("teams", [])), "hitters", len(d.get("hitters", [])))

print("\n=== SP (top 12 by alpha) ===")
for i, pr in enumerate(sorted(d["pitchers"], key=lambda x: -x.get("alpha_score", 0))[:12], 1):
    flags = []
    if pr.get("is_trap"):
        flags.append("TRAP")
    if pr.get("is_hazard"):
        flags.append("HAZARD")
    if pr.get("is_juiced_target"):
        flags.append("TARGET")
    if pr.get("form_status") == "SURGING":
        flags.append("SURGE")
    if pr.get("is_paradox"):
        flags.append("PARADOX")
    print(
        f"{i:2} {pr['alpha_score']:5.1f} conf{pr.get('attack_conf', 0):3} "
        f"{pr['pitcher'][:30]} vs {pr.get('opponent', '')[:24]} "
        f"K{pr.get('k_line')} trap={pr.get('is_trap')} haz={pr.get('is_hazard')} "
        f"{'|'.join(flags)}"
    )

print("\n=== STACKS (top 12) ===")
for i, t in enumerate(sorted(d["teams"], key=lambda x: -x.get("stack_score", 0))[:12], 1):
    sig = []
    if t.get("is_steam"):
        sig.append("STEAM")
    if t.get("is_shark"):
        sig.append("SHARK")
    if t.get("is_burst"):
        sig.append("BURST")
    print(
        f"{i:2} {t.get('stack_score', 0):5.1f} conf{t.get('attack_conf', 0):3} "
        f"xw{t.get('team_xwoba', 0):.3f} {t.get('team', '')[:28]} "
        f"vs {str(t.get('opp_pitcher', ''))[:22]} DQI={t.get('dqi_score')} {t.get('dqi_status', '')} "
        f"{'|'.join(sig)}"
    )
    for r in (t.get("attack_reasons") or [])[:3]:
        print("   ", r[:95])

print("\n=== MIA / ARI / COL / MYERS / SOROKA ===")
for pr in d["pitchers"]:
    if any(x in pr["pitcher"] for x in ("Myers", "Soroka", "Sugano", "Martin", "deGrom", "Sánchez", "Sanchez")):
        print(
            pr["pitcher"],
            "trap",
            pr.get("is_trap"),
            pr.get("trap_type"),
            "haz",
            pr.get("is_hazard"),
            "k",
            pr.get("k_line"),
            pr.get("k_odds"),
            "conf",
            pr.get("attack_conf"),
        )
for t in d["teams"]:
    if any(x in t.get("team", "") for x in ("Miami", "Arizona", "Colorado", "Boston", "Detroit", "Tampa")):
        print(t["team"], "conf", t.get("attack_conf"), "xw", t.get("team_xwoba"), "stack", t.get("stack_score"))
        print("  reasons:", t.get("attack_reasons"))

print("\n=== KEY HITTERS ===")
keys = [
    "Stowers", "Edwards", "Perdomo", "McCarthy", "Mcgonigle",
    "Contreras", "Rafaela", "Simpson", "Hicks", "Norby",
]
for nm in keys:
    for h in d["hitters"]:
        if nm.lower() in h["name"].lower():
            rs = h.get("attack_reasons") or []
            print(
                f"{h['name']:22} sc{h.get('player_score', 0):5.1f} "
                f"xw{h.get('matchup_xwoba', 0):.3f} conf{h.get('attack_conf', 0):3} "
                f"juice={h.get('is_juiced_target')} | {rs[0] if rs else ''}"
            )

print("\n=== TOP HITTER SCORES ===")
for h in sorted(d["hitters"], key=lambda x: -x.get("player_score", 0))[:18]:
    j = " J" if h.get("is_juiced_target") else ""
    print(f"{h.get('player_score', 0):5.1f} {h['name'][:26]:26} {h.get('team', '')[:20]}{j}")

print("\n=== HAZARD / TRAP SPs ===")
for pr in d["pitchers"]:
    if pr.get("is_hazard") or pr.get("is_trap"):
        print(pr["pitcher"], "vs", pr.get("opponent"), "trap", pr.get("is_trap"), "haz", pr.get("is_hazard"))

print("\n=== TRAP targets + PIT/TB ===")
for pr in d["pitchers"]:
    if pr.get("is_trap"):
        print(pr["pitcher"], "vs", pr.get("opponent"), "type", pr.get("trap_type"), "alpha", pr.get("alpha_score"))
for t in d["teams"]:
    if "Pittsburgh" in t.get("team", ""):
        print(t["team"], "stack", t.get("stack_score"), "conf", t.get("attack_conf"))
for h in d["hitters"]:
    if "Simpson" in h["name"] or "Caminero" in h["name"] or "Judge" in h["name"]:
        print(h["name"], h.get("team"), "sc", h.get("player_score"))
