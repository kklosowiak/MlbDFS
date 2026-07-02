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
    all_final = True

    for game in games:
        game_pk = str(game['gamePk'])
        status = game['status']['detailedState']
        home_team = game['teams']['home']['team']['name']
        away_team = game['teams']['away']['team']['name']
        home_runs = game['teams']['home'].get('score', 0)
        away_runs = game['teams']['away'].get('score', 0)

        if status.lower() not in completed_states:
            all_final = False

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
        sp_home = {"name": "TBD", "ip": 0.0, "er": 0, "k": 0, "h": 0, "bb": 0}
        sp_away = {"name": "TBD", "ip": 0.0, "er": 0, "k": 0, "h": 0, "bb": 0}

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

        game_list.append({
            "game_id": game_pk,
            "home_team": home_team,
            "away_team": away_team,
            "home_runs": home_runs,
            "away_runs": away_runs,
            "sp_home": sp_home,
            "sp_away": sp_away,
            "first_pitch_et": first_pitch_et,
            "status": "final" if status.lower() in completed_states else status.lower()
        })

    return game_list, all_final

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
            # If all games in existing file are final, skip
            if all(g.get("status") == "final" for g in existing_data):
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

    game_list, all_final = parse_games(games)

    # If any game is still active, wait 30 min and retry once
    if not all_final and not args.date:
        print("Some games are still in progress. Waiting 30 minutes for completion...")
        time.sleep(1800) # 30 minutes
        games = fetch_games_for_date(date_str)
        if games is not None:
            game_list, all_final = parse_games(games)

    # Save output
    try:
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(game_list, f, indent=4)
    except Exception as e:
        log_message(log_path, date_str, "FAIL", f"File write failed: {str(e)}")
        print(f"Error writing actuals file: {e}")
        sys.exit(1)

    status_code = "SUCCESS" if all_final else "INCOMPLETE"
    log_message(log_path, date_str, status_code, f"Fetched {len(game_list)} games")
    print(f"Successfully saved actuals for {date_str} (Status: {status_code}).")

def log_message(log_path, date_str, status, message):
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    with open(log_path, "a") as f:
        f.write(f"[{timestamp}] DATE: {date_str} | STATUS: {status} | {message}\n")

if __name__ == "__main__":
    main()
