"""One-off slate export analyzer for pitcher vs stack decisions."""
import json
import sys
from pathlib import Path

ABBR = {
    "Philadelphia Phillies": "PHI", "Cleveland Guardians": "CLE", "Los Angeles Dodgers": "LAD",
    "Milwaukee Brewers": "MIL", "Detroit Tigers": "DET", "Chicago Cubs": "CHC",
    "Houston Astros": "HOU", "Seattle Mariners": "SEA", "New York Yankees": "NYY",
    "Boston Red Sox": "BOS", "Atlanta Braves": "ATL", "San Diego Padres": "SD",
    "Texas Rangers": "TEX", "Minnesota Twins": "MIN", "Pittsburgh Pirates": "PIT",
    "Washington Nationals": "WSH", "Oakland Athletics": "OAK", "Athletics": "OAK",
    "Tampa Bay Rays": "TB", "Arizona Diamondbacks": "ARI", "Colorado Rockies": "COL",
    "Cincinnati Reds": "CIN", "St. Louis Cardinals": "STL", "Toronto Blue Jays": "TOR",
    "Miami Marlins": "MIA", "Chicago White Sox": "CWS", "Kansas City Royals": "KC",
    "Baltimore Orioles": "BAL", "San Francisco Giants": "SF", "New York Mets": "NYM",
    "Los Angeles Angels": "LAA",
}


def abbr(name):
    return ABBR.get(name, (name or "?")[:3].upper())


def stack_sigs(t):
    if not t:
        return []
    out = []
    if t.get("is_whale"):
        out.append("WHALE")
    if t.get("is_shark"):
        out.append("SHARK")
    if t.get("is_sharp"):
        out.append("HEAVY$")
    if t.get("is_burst"):
        out.append("BURST")
    if t.get("is_blind_spot"):
        out.append("BLIND")
    if t.get("is_trap"):
        out.append("CHALK")
    bf = t.get("bullpen_fatigue", 0) or 0
    if bf >= 90:
        out.append("EXHAUSTED")
    elif bf >= 75:
        out.append("GASSED")
    elif bf >= 65:
        out.append("WEARY")
    if t.get("trend") == "SURGING":
        out.append("SURGE")
    return out


def pitcher_sigs(p):
    out = []
    if p.get("is_trap"):
        out.append("TRAP")
    if p.get("is_hazard"):
        out.append("HAZARD")
    if p.get("is_shark"):
        out.append("SHARK")
    if p.get("is_whale"):
        out.append("WHALE")
    if p.get("is_sharp"):
        out.append("HEAVY$")
    if p.get("form_status") == "SURGING":
        out.append("SURGING")
    if p.get("form_status") == "COLD":
        out.append("COLD")
    if p.get("is_low_ceiling"):
        out.append("LOW_CEIL")
    if p.get("is_paradox"):
        out.append("PARADOX")
    return out


def verdict(p, opp_t):
    if p.get("is_trap") or p.get("is_hazard"):
        return "STACK (fade arm)"
    if not opp_t:
        if p.get("attack_conf", 0) >= 75 and not p.get("is_low_ceiling"):
            return "LEAN PITCHER"
        return "PASS / thin"

    osigs = stack_sigs(opp_t)
    if p.get("is_trap") and ("WHALE" in osigs or "SHARK" in osigs):
        return "STACK (trap pivot)"
    if ("WHALE" in osigs or "SHARK" in osigs) and p.get("attack_conf", 0) < 70:
        return "STACK (sharp $)"
    if opp_t.get("bullpen_fatigue", 0) >= 85:
        if p.get("attack_conf", 0) >= 85 and not p.get("is_hazard"):
            return "LEAN PITCHER*"
        return "STACK (pen)"
    if ("BURST" in osigs or "BLIND" in osigs) and p.get("attack_conf", 0) < 80:
        return "STACK (offense)"
    if p.get("attack_conf", 0) >= 80 and not p.get("is_trap") and "WHALE" not in osigs:
        return "LEAN PITCHER"
    if p.get("attack_conf", 0) >= 70 and not p.get("is_trap"):
        return "LEAN PITCHER"
    return "PASS / conflict"


def main():
    path = Path(sys.argv[1] if len(sys.argv) > 1 else r"c:\Users\konra\Downloads\omega-results(6).json")
    data = json.loads(path.read_text(encoding="utf-8"))
    pitchers = data.get("pitchers", [])
    teams = data.get("teams", [])
    teams_by = {t["team"]: t for t in teams}

    print("SLATE:", data.get("timestamp"))
    print(f"Pitchers: {len(pitchers)} | Teams: {len(teams)}\n")

    print("=== GAME-BY-GAME (pitcher vs stack thesis) ===")
    for p in sorted(pitchers, key=lambda x: -x.get("attack_conf", 0)):
        opp = p.get("opponent")
        opp_t = teams_by.get(opp)
        v = verdict(p, opp_t)
        print(
            f"{v:20} | {p['pitcher'][:24]:24} ({abbr(p['team'])}) vs {abbr(opp):3} "
            f"| SP CONF {p.get('attack_conf', 0):3} OMEGA {p.get('alpha_score', 0):5.1f} "
            f"| P:[{','.join(pitcher_sigs(p)) or '-'}] "
            f"| Opp:[{','.join(stack_sigs(opp_t)) or '-'}] "
            f"stack {opp_t.get('stack_score', 0) if opp_t else 0:.0f} CONF {opp_t.get('attack_conf', 0) if opp_t else 0}"
        )

    print("\n=== TOP STACK LOCKS (by stack score + CONF) ===")
    for t in sorted(teams, key=lambda x: (-x.get("attack_conf", 0), -x.get("stack_score", 0)))[:12]:
        opp_p = next((p for p in pitchers if p.get("opponent") == t["team"]), None)
        tag = ""
        if opp_p:
            if opp_p.get("is_trap"):
                tag = "vs TRAP SP ★"
            elif opp_p.get("is_hazard"):
                tag = "vs HAZARD SP"
        print(
            f"{t['team'][:26]:26} vs {abbr(t.get('opponent')):3} | "
            f"STACK {t.get('stack_score', 0):5.1f} CONF {t.get('attack_conf', 0):3} | "
            f"[{','.join(stack_sigs(t)) or '-'}] {tag} | vs {t.get('opp_pitcher', '')[:18]}"
        )

    print("\n=== TOP PITCHER LOCKS (LEAN PITCHER only) ===")
    for p in sorted(pitchers, key=lambda x: -x.get("attack_conf", 0)):
        opp_t = teams_by.get(p.get("opponent"))
        v = verdict(p, opp_t)
        if "PITCHER" in v:
            print(
                f"{p['pitcher'][:26]:26} vs {abbr(p.get('opponent')):3} | "
                f"CONF {p.get('attack_conf', 0):3} OMEGA {p.get('alpha_score', 0):5.1f} | {v}"
            )

    traps = [p for p in pitchers if p.get("is_trap")]
    hazards = [p for p in pitchers if p.get("is_hazard")]
    print(f"\nTRAP SP count: {len(traps)} | HAZARD count: {len(hazards)}")
    for p in traps:
        opp_t = teams_by.get(p["opponent"])
        print(f"  TRAP: {p['pitcher']} -> stack {p['opponent']} (stack {opp_t.get('stack_score') if opp_t else '?'})")


if __name__ == "__main__":
    main()
