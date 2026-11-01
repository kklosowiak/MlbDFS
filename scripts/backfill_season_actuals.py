"""Backfill per-game MLB boxscore actuals (hitters + starters + team runs) from the public MLB StatsAPI.

No API key required. Output is keyed by game_pk so doubleheaders are kept separate
(utils.audit_engine.AuditEngine.fetch_results keys by team name, which overwrites game 1).
Separate from scripts/backfill_actuals.py, which only repairs reports/archive/actuals_cache_*.json.

Usage:
    python scripts/backfill_season_actuals.py --start 2026-04-15 --end 2026-10-31
Output:
    data/season_2026/actuals/actuals_YYYY-MM-DD.json   (list of games; idempotent, skips complete files)
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import requests

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.normalization import normalize_player_name  # noqa: E402

API = "https://statsapi.mlb.com/api/v1"
OUT_DIR = os.path.join("data", "season_2026", "actuals")
TERMINAL = {"final", "completed early", "game over"}
DEAD = ("postponed", "cancelled", "suspended")


def get_json(url, tries=4):
    last = None
    for i in range(tries):
        try:
            r = requests.get(url, timeout=20)
            if r.status_code == 200:
                return r.json()
            last = "HTTP %s" % r.status_code
        except Exception as e:  # network hiccup
            last = str(e)
        time.sleep(1.5 * (i + 1))
    raise RuntimeError("GET failed %s: %s" % (url, last))


def parse_boxscore(box, side):
    team = box.get("teams", {}).get(side, {})
    players = team.get("players", {})
    hitters = {}
    for pdata in players.values():
        b = pdata.get("stats", {}).get("batting", {})
        if not b:
            continue  # did not bat (same rule as AuditEngine)
        name = pdata.get("person", {}).get("fullName", "Unknown")
        hits = b.get("hits", 0) or 0
        d = b.get("doubles", 0) or 0
        t = b.get("triples", 0) or 0
        hr = b.get("homeRuns", 0) or 0
        bo = pdata.get("battingOrder")
        hitters[normalize_player_name(name)] = {
            "name": name,
            "player_id": pdata.get("person", {}).get("id"),
            "hits": hits,
            "singles": hits - (d + t + hr),
            "doubles": d,
            "triples": t,
            "hr": hr,
            "rbi": b.get("rbi", 0) or 0,
            "runs_scored": b.get("runs", 0) or 0,
            "walks": b.get("baseOnBalls", 0) or 0,
            "stolen_bases": b.get("stolenBases", 0) or 0,
            "hbp": b.get("hitByPitch", 0) or 0,
            "strikeouts": b.get("strikeOuts", 0) or 0,
            "at_bats": b.get("atBats", 0) or 0,
            "plate_appearances": b.get("plateAppearances", 0) or 0,
            "batting_order": (int(bo) // 100) if bo and str(bo).isdigit() else None,
            "is_starter": bool(bo and str(bo).isdigit() and int(bo) % 100 == 0),
        }
    sp = {"name": "TBD", "player_id": None, "ip": "0.0", "er": 0, "k": 0, "h": 0, "bb": 0,
          "wins": 0, "completeGames": 0, "shutouts": 0, "hitByPitch": 0, "pitches": 0}
    pids = team.get("pitchers", [])
    if pids:
        pd_ = players.get("ID%s" % pids[0], {})
        st = pd_.get("stats", {}).get("pitching", {})
        sp = {
            "name": pd_.get("person", {}).get("fullName", "Unknown"),
            "player_id": pd_.get("person", {}).get("id"),
            "ip": st.get("inningsPitched", "0.0"),
            "er": st.get("earnedRuns", 0), "k": st.get("strikeOuts", 0),
            "h": st.get("hits", 0), "bb": st.get("baseOnBalls", 0),
            "wins": st.get("wins", 0), "completeGames": st.get("completeGames", 0),
            "shutouts": st.get("shutouts", 0),
            "hitByPitch": st.get("hitByPitch", 0) or st.get("hitBatsmen", 0) or 0,
            "pitches": st.get("numberOfPitches", 0),
        }
    return hitters, sp


def build_game(g):
    pk = g["gamePk"]
    status = g["status"]["detailedState"]
    low = status.lower()
    is_final = low in TERMINAL
    is_dead = any(s in low for s in DEAD)
    rec = {
        "game_pk": pk,
        "game_type": g.get("gameType"),
        "game_number": g.get("gameNumber"),
        "double_header": g.get("doubleHeader"),
        "game_date_utc": g.get("gameDate"),
        "status": "final" if is_final else ("postponed" if is_dead else low),
        "is_complete": is_final or is_dead,
        "home_team": g["teams"]["home"]["team"]["name"],
        "away_team": g["teams"]["away"]["team"]["name"],
        "home_runs": g["teams"]["home"].get("score", 0),
        "away_runs": g["teams"]["away"].get("score", 0),
        "venue": g.get("venue", {}).get("name"),
    }
    if is_final:
        box = get_json("%s/game/%s/boxscore" % (API, pk))
        rec["hitters_home"], rec["sp_home"] = parse_boxscore(box, "home")
        rec["hitters_away"], rec["sp_away"] = parse_boxscore(box, "away")
    return rec


def already_complete(path):
    if not os.path.exists(path):
        return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return all(x.get("is_complete") for x in data)
    except Exception:
        return False


def do_date(ds):
    path = os.path.join(OUT_DIR, "actuals_%s.json" % ds)
    if already_complete(path):
        return ds, "skip", 0
    sched = get_json("%s/schedule?sportId=1&date=%s" % (API, ds))
    games = (sched.get("dates") or [{}])[0].get("games", [])
    out = [build_game(g) for g in games]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f)
    return ds, "ok", len(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(OUT_DIR, exist_ok=True)
    d0, d1 = date.fromisoformat(a.start), date.fromisoformat(a.end)
    dates = [(d0 + timedelta(n)).isoformat() for n in range((d1 - d0).days + 1)]
    ok = skipped = games = failed = 0
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        futs = {ex.submit(do_date, ds): ds for ds in dates}
        for fut, ds in futs.items():
            try:
                _, st, n = fut.result()
                if st == "skip":
                    skipped += 1
                else:
                    ok += 1
                    games += n
            except Exception as e:
                failed += 1
                print("FAILED %s: %s" % (ds, e))
    print("dates=%d ok=%d skipped=%d failed=%d games_written=%d" % (len(dates), ok, skipped, failed, games))
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
