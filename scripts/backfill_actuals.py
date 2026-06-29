import os
import json
import re
import time
import requests
import sys

# Ensure project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
archive_dir = os.path.join(base_dir, "reports", "archive")
api_base = "https://statsapi.mlb.com/api/v1"

def needs_backfill(data):
    # Check if any hitter is missing runs_scored
    for team, team_data in data.items():
        hitters = team_data.get("hitters", {})
        for hitter_name, hitter_stats in hitters.items():
            if "runs_scored" not in hitter_stats:
                return True
    return False

def fetch_complete_results(date_str, api_calls_counter):
    url = f"{api_base}/schedule?sportId=1&date={date_str}&hydrate=boxscore"
    print(f"  Fetching schedule for {date_str}...")
    api_calls_counter[0] += 1
    
    try:
        response = requests.get(url, timeout=15)
        data = response.json()
        games = data.get('dates', [{}])[0].get('games', [])
        
        results = {}
        
        for game in games:
            teams = game['teams']
            game_pk = game['gamePk']
            status = game['status']['detailedState']
            
            # Fetch detailed boxscore for stats
            box_url = f"{api_base}/game/{game_pk}/boxscore"
            print(f"    Fetching boxscore for game {game_pk}...")
            time.sleep(0.1) # Respectful delay
            api_calls_counter[0] += 1
            
            try:
                box_resp = requests.get(box_url, timeout=10)
                box = box_resp.json()
            except Exception as ge:
                print(f"      Error fetching boxscore {game_pk}: {ge}")
                box = {}
                
            # Team Results
            results[game['teams']['away']['team']['name']] = {'runs': teams['away'].get('score', 0), 'status': status}
            results[game['teams']['home']['team']['name']] = {'runs': teams['home'].get('score', 0), 'status': status}
            
            for side in ['away', 'home']:
                team_name = game['teams'][side]['team']['name']
                
                # Pitching Starter
                pitcher_ids = box.get('teams', {}).get(side, {}).get('pitchers', [])
                if pitcher_ids:
                    sp_id = pitcher_ids[0]
                    sp_data = box.get('teams', {}).get(side, {}).get('players', {}).get(f"ID{sp_id}", {})
                    stats = sp_data.get('stats', {}).get('pitching', {})
                    results[team_name]['sp_stats'] = {
                        'name': sp_data.get('person', {}).get('fullName', 'Unknown'),
                        'k': stats.get('strikeOuts', 0),
                        'er': stats.get('earnedRuns', 0),
                        'ip': stats.get('inningsPitched', "0.0")
                    }
                else:
                    results[team_name]['sp_stats'] = {'name': 'TBD', 'k': 0, 'er': 0, 'ip': "0.0"}
                    
                # Extended Hitting Stats
                results[team_name]['hitters'] = {}
                players = box.get('teams', {}).get(side, {}).get('players', {})
                for p_id, p_data in players.items():
                    b_stats = p_data.get('stats', {}).get('batting', {})
                    if b_stats:
                        name = p_data.get('person', {}).get('fullName', 'Unknown')
                        from utils.normalization import normalize_player_name
                        norm_name = normalize_player_name(name)
                        
                        hits = b_stats.get('hits', 0) or 0
                        hr_val = b_stats.get('homeRuns', 0) or 0
                        rbi_val = b_stats.get('rbi', 0) or 0
                        doubles = b_stats.get('doubles', 0) or 0
                        triples = b_stats.get('triples', 0) or 0
                        runs_scored = b_stats.get('runs', 0) or 0
                        walks = b_stats.get('baseOnBalls', 0) or 0
                        stolen_bases = b_stats.get('stolenBases', 0) or 0
                        hbp = b_stats.get('hitByPitch', 0) or 0
                        singles = hits - (doubles + triples + hr_val)
                        
                        results[team_name]['hitters'][norm_name] = {
                            'hits': hits,
                            'hr': hr_val,
                            'rbi': rbi_val,
                            'doubles': doubles,
                            'triples': triples,
                            'runs_scored': runs_scored,
                            'walks': walks,
                            'stolen_bases': stolen_bases,
                            'hbp': hbp,
                            'singles': singles
                        }
        return results
    except Exception as e:
        print(f"Error fetching schedule for {date_str}: {e}")
        return {}

def main():
    if not os.path.exists(archive_dir):
        print(f"Archive directory {archive_dir} not found.")
        return
        
    files = os.listdir(archive_dir)
    actuals_files = sorted([f for f in files if f.startswith("actuals_cache_") and f.endswith(".json")])
    
    total_slates = len(actuals_files)
    backfilled_count = 0
    already_complete_count = 0
    api_calls_counter = [0]
    
    print(f"Found {total_slates} actuals cache files in archive.")
    
    for af in actuals_files:
        date_match = re.search(r'actuals_cache_(\d{4}-\d{2}-\d{2})\.json', af)
        if not date_match:
            continue
        date_str = date_match.group(1)
        file_path = os.path.join(archive_dir, af)
        
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {af}: {e}")
            continue
            
        if needs_backfill(data):
            print(f"Slate {date_str} is missing complete stats. Backfilling...")
            complete_data = fetch_complete_results(date_str, api_calls_counter)
            if complete_data:
                try:
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(complete_data, f, indent=4)
                    print(f"  Successfully backfilled and saved {af}.")
                    backfilled_count += 1
                except Exception as e:
                    print(f"  Error writing {af}: {e}")
            else:
                print(f"  Failed to fetch complete data for {date_str}.")
        else:
            already_complete_count += 1
            
    print("\n=== BACKFILL SUMMARY ===")
    print(f"Total slates checked: {total_slates}")
    print(f"Slates already complete: {already_complete_count}")
    print(f"Slates backfilled: {backfilled_count}")
    print(f"API calls made: {api_calls_counter[0]}")

if __name__ == "__main__":
    main()
