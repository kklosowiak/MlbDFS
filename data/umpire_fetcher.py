import requests
from datetime import datetime

class UmpireFetcher:
    def __init__(self):
        # Static database of high-impact umpires (Career K-rate vs Run-rate deviations)
        # 1.0 = Neutral, > 1.0 = Pitcher Friendly, < 1.0 = Hitter Friendly
        self.umpire_database = {
            "Bill Miller": 0.85,    # High run environment
            "Pat Hoberg": 1.15,     # Pitcher friendly / Accurate zone
            "Laz Diaz": 0.90,       # Hitter friendly
            "Vic Carapazza": 1.10,  # Pitcher friendly
            "Angel Hernandez": 0.95, # Unpredictable/Hitter lean
            "Doug Eddings": 1.05,
            "Hunter Wendelstedt": 1.08,
            "Joe West": 0.90,
            "CB Bucknor": 0.92,
            "Ron Kulpa": 1.12,
            "James Hoye": 1.05
        }

    def fetch_daily_assignments(self):
        """Fetches today's home plate umpires from MLB Stats API."""
        date_str = datetime.now().strftime("%Y-%m-%d")
        url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&hydrate=officials&date={date_str}"
        
        assignments = {}
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            for date in data.get('dates', []):
                for game in date.get('games', []):
                    # Each game has 'officials'
                    hp_umpire = "Unknown"
                    for official in game.get('officials', []):
                        if official.get('officialType') == "Home Plate":
                            hp_umpire = official['official']['fullName']
                            break
                    
                    # Store by Venue or Team (Map to Home Team for easy lookup)
                    home_team = game['teams']['home']['team']['name']
                    assignments[home_team] = {
                        "name": hp_umpire,
                        "factor": self.umpire_database.get(hp_umpire, 1.0)
                    }
            return assignments
        except Exception as e:
            print(f"ERROR: Umpire fetch failed: {e}")
            return {}

if __name__ == "__main__":
    fetcher = UmpireFetcher()
    data = fetcher.fetch_daily_assignments()
    print(data)
