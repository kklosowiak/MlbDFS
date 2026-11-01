import os
import sys
import time
import argparse
import requests
import json
from datetime import datetime, timezone, timedelta
try:
    from zoneinfo import ZoneInfo
except ImportError:
    ZoneInfo = None

def get_yesterday_et_str():
    dt_utc = datetime.now(timezone.utc)
    if ZoneInfo:
        dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
    else:
        dt_et = dt_utc - timedelta(hours=4)
    yesterday_et = dt_et - timedelta(days=1)
    return yesterday_et.strftime("%Y-%m-%d")

def fetch_games_for_date(date_str):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}&hydrate=boxscore"
    print(f"Fetching actuals from: {url}")
    try:
        resp = requests.get(url, timeout=15)
        if resp.status_code != 200:
            print(f"Error fetching schedule: HTTP {resp.status_code}")
            return None
        data = resp.json()
    except Exception as e:
        print(f"Connection error: {e}")
        return None

    dates_list = data.get('dates', [])
    if not dates_list:
        return []
    return dates_list[0].get('games', [])

def parse_games(games):
    game_list = []
    completed_states = ["final", "completed early", "game over"]
    postponed_states = ["postponed", "cancelled", "suspended"]
    all_terminal = True
    all_final = True
    failed_pitchers_count = 0
    final_count = 0
    postponed_count = 0
    in_progress_count = 0

    for game in games:
        game_pk = str(game['gamePk'])
        status_raw = game['status']['detailedState']
        status_lower = status_raw.lower()
        home_team = game['teams']['home']['team']['name']
        away_team = game['teams']['away']['team']['name']
        home_runs = game['teams']['home'].get('score', 0)
        away_runs = game['teams']['away'].get('score', 0)

        is_final = status_lower in completed_states
        is_postponed = any(s in status_lower for s in postponed_states)
        is_complete = is_final or is_postponed

        if is_final:
            final_count += 1
            game_status = "final"
        elif is_postponed:
            postponed_count += 1
            game_status = "postponed"
        else:
            in_progress_count += 1
            game_status = status_lower

        if not is_final:
            all_final = False

        if not is_complete:
            all_terminal = False

        game_date_str = game.get('gameDate')
        first_pitch_et = "00:00"
        if game_date_str:
            try:
                dt_utc = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                if ZoneInfo:
                    dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
                else:
                    dt_et = dt_utc - timedelta(hours=4)
                first_pitch_et = dt_et.strftime("%H:%M")
            except Exception:
                pass

        box_url = f"https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore"
        try:
            box_resp = requests.get(box_url, timeout=10)
            boxscore = box_resp.json()
        except Exception:
            boxscore = {}
        sp_home = {"name": "TBD", "ip": 0.0, "er": 0, "k": 0, "h": 0, "bb": 0, "wins": 0, "completeGames": 0, "shutouts": 0, "hitByPitch": 0}
        sp_away = {"name": "TBD", "ip": 0.0, "er": 0, "k": 0, "h": 0, "bb": 0, "wins": 0, "completeGames": 0, "shutouts": 0, "hitByPitch": 0}

        for side, sp_dict in [('home', sp_home), ('away', sp_away)]:
            pitcher_ids = boxscore.get('teams', {}).get(side, {}).get('pitchers', [])
            if pitcher_ids:
                sp_id = pitcher_ids[0]
                sp_data = boxscore.get('teams', {}).get(side, {}).get('players', {}).get(f"ID{sp_id}", {})
                stats = sp_data.get('stats', {}).get('pitching', {})
                sp_dict["name"] = sp_data.get('person', {}).get('fullName', 'Unknown')
                sp_dict["k"] = stats.get('strikeOuts', 0)
                sp_dict["er"] = stats.get('earnedRuns', 0)

                ip_str = stats.get('inningsPitched', "0.0")
                try:
                    sp_dict["ip"] = float(ip_str)
                except ValueError:
                    sp_dict["ip"] = 0.0

                sp_dict["h"] = stats.get('hits', 0)
                sp_dict["bb"] = stats.get('baseOnBalls', 0)
                sp_dict["wins"] = stats.get('wins', 0)
                sp_dict["completeGames"] = stats.get('completeGames', 0)
                sp_dict["shutouts"] = stats.get('shutouts', 0)
                sp_dict["hitByPitch"] = stats.get('hitByPitch', 0) or stats.get('hitBatsmen', 0) or 0

        # OMEGA 2027: Also extract full hitter boxscores (hitters_home & hitters_away)
        hitters_home = []
        hitters_away = []
        for side, h_list in [('home', hitters_home), ('away', hitters_away)]:
            players_dict = boxscore.get('teams', {}).get(side, {}).get('players', {})
            for p_key, p_data in players_dict.items():
                b_stats = p_data.get('stats', {}).get('batting', {})
                if not b_stats:
                    continue
                pa = (
                    int(b_stats.get('atBats', 0))
                    + int(b_stats.get('baseOnBalls', 0))
                    + int(b_stats.get('hitByPitch', 0))
                    + int(b_stats.get('sacFlies', 0))
                    + int(b_stats.get('sacBunts', 0))
                )
                runs = int(b_stats.get('runs', 0))
                sb = int(b_stats.get('stolenBases', 0))
                if pa == 0 and runs == 0 and sb == 0:
                    continue
                hits = int(b_stats.get('hits', 0))
                doubles = int(b_stats.get('doubles', 0))
                triples = int(b_stats.get('triples', 0))
                hr = int(b_stats.get('homeRuns', 0))
                singles = max(0, hits - doubles - triples - hr)
                rbi = int(b_stats.get('rbi', 0))
                bb = int(b_stats.get('baseOnBalls', 0))
                hbp = int(b_stats.get('hitByPitch', 0))
                tb = int(b_stats.get('totalBases', singles + 2 * doubles + 3 * triples + 4 * hr))
                dk_pts = (
                    singles * 3
                    + doubles * 5
                    + triples * 8
                    + hr * 10
                    + rbi * 2
                    + runs * 2
                    + bb * 2
                    + hbp * 2
                    + sb * 5
                )
                h_list.append({
                    "name": p_data.get('person', {}).get('fullName', 'Unknown'),
                    "batting_order": p_data.get('battingOrder', ''),
                    "pa": pa,
                    "ab": int(b_stats.get('atBats', 0)),
                    "h": hits,
                    "1b": singles,
                    "2b": doubles,
                    "3b": triples,
                    "hr": hr,
                    "r": runs,
                    "rbi": rbi,
                    "bb": bb,
                    "hbp": hbp,
                    "sb": sb,
                    "k": int(b_stats.get('strikeOuts', 0)),
                    "tb": tb,
                    "dk_pts": dk_pts,
                })

        # Track pitcher fetch failures for final/completed games
        if is_final:
            if sp_home["name"] in ["TBD", "Unknown"]:
                failed_pitchers_count += 1
            if sp_away["name"] in ["TBD", "Unknown"]:
                failed_pitchers_count += 1

        game_list.append({
            "game_id": game_pk,
            "home_team": home_team,
            "away_team": away_team,
            "home_runs": home_runs,
            "away_runs": away_runs,
            "sp_home": sp_home,
            "sp_away": sp_away,
            "hitters_home": hitters_home,
            "hitters_away": hitters_away,
            "first_pitch_et": first_pitch_et,
            "status": game_status,
            "is_complete": is_complete
        })

    return game_list, all_terminal, all_final, failed_pitchers_count, final_count, postponed_count, in_progress_count

def main():
    parser = argparse.ArgumentParser(description="OMEGA Nightly Actuals Fetcher")
    parser.add_argument("--date", help="Target date (YYYY-MM-DD), defaults to yesterday")
    args = parser.parse_args()

    date_str = args.date or get_yesterday_et_str()
    print(f"Targeting actuals for date: {date_str}")

    target_dir = os.path.join("scratch", "passive_tracker", "actuals")
    os.makedirs(target_dir, exist_ok=True)
    target_path = os.path.join(target_dir, f"actuals_{date_str}.json")
    log_path = os.path.join("scratch", "passive_tracker", "actuals_log.txt")

    # Idempotency Check
    if os.path.exists(target_path):
        try:
            with open(target_path, "r", encoding="utf-8") as f:
                existing_data = json.load(f)
            def is_entry_complete(g):
                if g.get("is_complete") is True:
                    return True
                st = g.get("status", "").lower()
                return st in ["final", "completed early", "game over", "postponed", "cancelled", "suspended"]

            if existing_data and all(is_entry_complete(g) for g in existing_data):
                print(f"Complete actuals for {date_str} already exist. Skipping.")
                sys.exit(0)
        except Exception:
            pass

    # First Attempt
    games = fetch_games_for_date(date_str)
    if games is None:
        log_message(log_path, date_str, "FAIL", "Failed to contact MLB StatsAPI")
        sys.exit(1)

    if not games:
        print(f"No games found on date {date_str}. Writing empty actuals.")
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=4)
        log_message(log_path, date_str, "SUCCESS", "No games scheduled")
        sys.exit(0)

    game_list, all_terminal, all_final, failed_pitchers, final_cnt, post_cnt, in_prog_cnt = parse_games(games)

    # If any game is still active, wait 30 min and retry once if running un-dated
    if not all_terminal and not args.date:
        print("Some games are still in progress. Waiting 30 minutes for completion...")
        time.sleep(1800) # 30 minutes
        games = fetch_games_for_date(date_str)
        if games is not None:
            game_list, all_terminal, all_final, failed_pitchers, final_cnt, post_cnt, in_prog_cnt = parse_games(games)

    if failed_pitchers > 0:
        log_message(log_path, date_str, "INCOMPLETE", f"{failed_pitchers} pitchers failed to fetch, sample incomplete for {date_str}")
        print(f"Error: {failed_pitchers} starting pitchers failed to fetch from boxscores. Terminating.")
        sys.exit(1)

    # Save output
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(game_list, f, indent=4)
    except Exception as e:
        log_message(log_path, date_str, "FAIL", f"File write failed: {str(e)}")
        print(f"Error writing actuals file: {e}")
        sys.exit(1)

    status_code = "SUCCESS" if all_terminal else "INCOMPLETE"
    msg_parts = []
    if final_cnt > 0:
        msg_parts.append(f"{final_cnt} final")
    if post_cnt > 0:
        msg_parts.append(f"{post_cnt} postponed")
    if in_prog_cnt > 0:
        msg_parts.append(f"{in_prog_cnt} in progress")
    detail_str = f" ({', '.join(msg_parts)})" if msg_parts else ""

    log_message(log_path, date_str, status_code, f"Fetched {len(game_list)} games{detail_str}")
    print(f"Successfully saved actuals for {date_str} (Status: {status_code}).")


def log_message(log_path, date_str, status, message):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] DATE: {date_str} | STATUS: {status} | {message}\n")

if __name__ == "__main__":
    main()
