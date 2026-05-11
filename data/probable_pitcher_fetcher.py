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
        
        # Use current date (local time corresponds to the slate usually)
        fetch_date = datetime.now().strftime("%Y-%m-%d")
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
            for date_entry in data['dates']:
                for game in date_entry.get('games', []):
                    for side in ['away', 'home']:
                        team_data = game.get('teams', {}).get(side, {})
                        team_name = team_data.get('team', {}).get('name')
                        pitcher_name = team_data.get('probablePitcher', {}).get('fullName', 'TBD')
                        
                        if team_name:
                            probables[team_name] = pitcher_name
            
            if probables:
                with open(self.output_path, 'w') as f:
                    json.dump(probables, f, indent=4)
                print(f"  - SUCCESS: Synchronized {len(probables)} starters via StatsAPI.")
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
