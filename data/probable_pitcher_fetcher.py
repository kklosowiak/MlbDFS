import requests
import json
import os
import sys

# Standalone execution support
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from config import config

class ProbablePitcherFetcher:
    """
    OMEGA v6.5: Dynamic Slate Synchronizer.
    Hits the official MLB StatsAPI to pull announced starters for the day.
    """
    def __init__(self):
        self.base_url = "https://statsapi.mlb.com/api/v1/schedule"
        self.output_path = os.path.join(config.DATA_DIR, "probable_pitchers.json")

    def refresh(self):
        """
        Fetches today's probable pitchers and updates the local source of truth.
        """
        print("[INGEST]: Synchronizing MLB Probable Pitchers (Dynamic Slate)...")
        
        # OMEGA v9.6: Timezone-aware DFS slate rollover (4:00 AM US/Eastern Time)
        from datetime import datetime, timedelta, timezone
        dt_utc = datetime.now(timezone.utc)
        try:
            from zoneinfo import ZoneInfo
            dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
        except Exception:
            dt_et = dt_utc - timedelta(hours=4)
            
        if dt_et.hour < 4:
            slate_date = (dt_et - timedelta(days=1)).date()
        else:
            slate_date = dt_et.date()
            
        fetch_date = slate_date.strftime("%Y-%m-%d")
        print(f"  - TARGET DATE: {fetch_date}")
        params = {
            'sportId': 1,
            'hydrate': 'probablePitcher',
            'date': fetch_date
        }
        
        try:
            response = requests.get(self.base_url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if not data.get('dates'):
                print("  - WARNING: No games found in MLB schedule for today.")
                return False
                
            probables = {}
            team_games = {}
            for date_entry in data['dates']:
                for game in date_entry.get('games', []):
                    game_date = game.get('gameDate')
                    game_num = game.get('gameNumber', 1)
                    for side in ['away', 'home']:
                        team_data = game.get('teams', {}).get(side, {})
                        team_name = team_data.get('team', {}).get('name')
                        pitcher_name = team_data.get('probablePitcher', {}).get('fullName', 'TBD')
                        if team_name:
                            if team_name not in team_games:
                                team_games[team_name] = []
                            team_games[team_name].append({
                                'pitcher': pitcher_name,
                                'date': game_date,
                                'number': game_num
                            })

            # OMEGA: Load pitcher overrides if they exist
            overrides_path = os.path.join(config.DATA_DIR, "pitcher_overrides.json")
            overrides = {}
            if os.path.exists(overrides_path):
                try:
                    import time
                    mtime = os.path.getmtime(overrides_path)
                    mtime_dt = datetime.fromtimestamp(mtime, timezone.utc)
                    try:
                        from zoneinfo import ZoneInfo
                        mtime_et = mtime_dt.astimezone(ZoneInfo("America/New_York"))
                    except Exception:
                        mtime_et = mtime_dt - timedelta(hours=4)
                    
                    if mtime_et.hour < 4:
                        file_slate_date = (mtime_et - timedelta(days=1)).date()
                    else:
                        file_slate_date = mtime_et.date()
                    
                    if file_slate_date != slate_date:
                        print(f"  - [CLEANUP]: Stale pitcher overrides found from {file_slate_date}. Clearing file.")
                        with open(overrides_path, 'w', encoding='utf-8') as f:
                            json.dump({}, f, indent=4)
                    else:
                        with open(overrides_path, 'r', encoding='utf-8') as f:
                            overrides = json.load(f)
                        print(f"  - LOADED overrides: {list(overrides.keys())}")
                except Exception as ov_err:
                    print(f"  - WARNING: Failed to load/clear pitcher overrides: {ov_err}")

            for team_name, games in team_games.items():
                # Sort games by game number
                games.sort(key=lambda x: x['number'])
                # Suffixes
                for i, g in enumerate(games):
                    suffix = f"_{i+1}"
                    pitcher = g['pitcher']
                    
                    # Try to match override by Date_Team_GameNumber or legacy Team_GameNumber
                    date_override_key = f"{fetch_date}_{team_name}{suffix}"
                    override_key = f"{team_name}{suffix}"
                    date_team_key = f"{fetch_date}_{team_name}"
                    
                    if date_override_key in overrides:
                        pitcher = overrides[date_override_key]
                        print(f"  - OVERRIDE: {date_override_key} -> {pitcher} (was {g['pitcher']})")
                    elif override_key in overrides:
                        pitcher = overrides[override_key]
                        print(f"  - OVERRIDE: {override_key} -> {pitcher} (was {g['pitcher']})")
                    # Try to match override by general team name for Game 1
                    elif i == 0 and date_team_key in overrides:
                        pitcher = overrides[date_team_key]
                        print(f"  - OVERRIDE: {date_team_key} -> {pitcher} (was {g['pitcher']})")
                    elif i == 0 and team_name in overrides:
                        pitcher = overrides[team_name]
                        print(f"  - OVERRIDE: {team_name} -> {pitcher} (was {g['pitcher']})")
                        
                    probables[f"{team_name}{suffix}"] = pitcher
                    probables[f"{team_name}{suffix}_time"] = g['date']
                    
                # Default is Game 1 for backward compatibility
                probables[team_name] = probables.get(f"{team_name}_1", games[0]['pitcher'])
            
            if probables:
                with open(self.output_path, 'w') as f:
                    json.dump(probables, f, indent=4)
                print(f"  - SUCCESS: Synchronized {len(probables)} starters via StatsAPI (applied overrides).")
                return True
            else:
                print("  - WARNING: No probable pitchers found in the API response.")
                return False
                
        except Exception as e:
            print(f"  - ERROR: Failed to sync probable pitchers. {e}")
            return False

if __name__ == "__main__":
    fetcher = ProbablePitcherFetcher()
    fetcher.refresh()
