"""Compare key players/teams for lineup context."""
import json
import sys
from pathlib import Path

def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))

def team(d, name):
    return next((t for t in d["teams"] if t["team"] == name), None)

def pitcher(d, sub):
    return next((p for p in d["pitchers"] if sub.lower() in p["pitcher"].lower()), None)

def hitter(d, sub):
    return next((h for h in d["hitters"] if sub.lower() in h["name"].lower()), None)

def main(path):
    d = load(path)
    print("FILE", Path(path).name, "ts", d.get("timestamp"))
    for tn in [
        "Pittsburgh Pirates", "Boston Red Sox", "Miami Marlins", "Tampa Bay Rays",
        "Arizona Diamondbacks", "Minnesota Twins",
    ]:
        t = team(d, tn)
        if not t:
            continue
        print(
            f"\n{t['team']}: stk={t.get('stack_score')} conf={t.get('attack_conf')} "
            f"div={t.get('divergence')} dqi={t.get('dqi_score')}/{t.get('dqi_status')} "
            f"vs {t.get('opp_pitcher')} whale={t.get('is_whale')} blind={t.get('is_blind_spot')} "
            f"burst={t.get('is_burst')} total={t.get('total_signal') or '-'}"
        )

    for pn in ["Davis Martin", "Payton Tolle", "Jacob Degrom", "Michael Soroka", "Kevin Gausman", "Gerrit Cole"]:
        p = pitcher(d, pn.split()[-1])
        if p:
            print(
                f"\n{p['pitcher']}: conf={p.get('attack_conf')} omega={p.get('alpha_score')} "
                f"trap={p.get('is_trap')} hazard={p.get('is_hazard')} div={p.get('divergence')} "
                f"form={p.get('form_status')} k={p.get('k_line')}"
            )

    for hn in ["Liam Hicks", "Kyle Stowers", "Ceddanne Rafaela", "Willson Contreras", "Brandon Lowe",
               "Chandler Simpson", "Richie Palacios", "Nick Gonzales"]:
        h = hitter(d, hn.split()[-1])
        if h:
            print(
                f"\n{h['name']}: sc={h.get('player_score')} xw={h.get('matchup_xwoba')} "
                f"smash={h.get('smash_factor')} hot={h.get('is_hot')} TARGET={h.get('is_juiced_target')} "
                f"speed={h.get('is_speed_target')} atk_conf={h.get('attack_conf')}"
            )

if __name__ == "__main__":
    main(sys.argv[1])
