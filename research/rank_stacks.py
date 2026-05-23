import json
import sys
from pathlib import Path

def main(path):
    d = json.loads(Path(path).read_text(encoding="utf-8"))
    teams = [t for t in d["teams"] if "Diamondback" not in t["team"]]
    teams.sort(key=lambda t: (-t.get("stack_score", 0), -t.get("attack_conf", 0)))
    print("Rank | Team | Stk | CONF | Div | DQI | Opp SP | Signals")
    for i, t in enumerate(teams[:12], 1):
        sig = []
        if t.get("is_whale"):
            sig.append("WHALE")
        if t.get("is_blind_spot"):
            sig.append("BLIND")
        if t.get("is_burst"):
            sig.append("BURST")
        if t.get("is_trap"):
            sig.append("CHALK_TRAP")
        dqi = f"{t.get('dqi_score')}/{t.get('dqi_status')}" if t.get("dqi_score") else "-"
        ts = (t.get("total_signal") or "").encode("ascii", "backslashreplace").decode()
        print(
            f"{i:2}  {t['team'][:22]:22}  {t.get('stack_score', 0):6.1f}  "
            f"{t.get('attack_conf', 0):3}  {t.get('divergence', 0):+4}  {dqi:12}  "
            f"{(t.get('opp_pitcher') or '')[:18]:18}  {' '.join(sig)}  {ts}"
        )

if __name__ == "__main__":
    main(sys.argv[1])
