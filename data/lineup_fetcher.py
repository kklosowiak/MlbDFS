import requests
from datetime import datetime
from utils.normalization import normalize_player_name

class LineupFetcher:
    def __init__(self):
        self.api_url = "https://statsapi.mlb.com/api/v1/schedule"

    def _normalize_name(self, name: str) -> str:
        """OMEGA v6.9.1: Hardened name normalization with accent stripping."""
        if not name: return ""
        import unicodedata
        # Strip accents (e.g., Rodríguez -> Rodriguez)
        name = "".join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
        # Standard cleaning
        name = name.lower().replace(".", "").replace("-", " ").strip()
        # Nickname/Suffix handling
        name = name.replace("jr", "").replace("sr", "").strip()
        return name

    def fetch_confirmed_lineups(self, date_str=None):
        """
        Fetches official starting lineups from MLB StatsAPI.
        Returns a dict: { 'Team Name': [ 'Player 1', 'Player 2', ... ] }
        """
        if not date_str:
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
                
            date_str = slate_date.strftime("%Y-%m-%d")
            
        params = {
            'sportId': 1,
            'date': date_str,
            'hydrate': 'lineups'
        }
        
        # OMEGA v6.9.4: Global Franchise Mapping
        franchise_map = {
            "Texas": "Texas Rangers", "TX": "Texas Rangers",
            "Arizona": "Arizona Diamondbacks", "AZ": "Arizona Diamondbacks",
            "Detroit": "Detroit Tigers", "DET": "Detroit Tigers",
            "Chicago Cubs": "Chicago Cubs", "CHC": "Chicago Cubs",
            "Chicago White Sox": "Chicago White Sox", "CHW": "Chicago White Sox",
            "Los Angeles Dodgers": "Los Angeles Dodgers", "LAD": "Los Angeles Dodgers",
            "Los Angeles Angels": "Los Angeles Angels", "LAA": "Los Angeles Angels"
        }
        
        lineups = {}
        game_times = {}
        try:
            response = requests.get(self.api_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            if 'dates' not in data or not data['dates']:
                return {}
                
            games = data['dates'][0].get('games', [])
            for game in games:
                game_date = game.get('gameDate')
                lineups_data = game.get('lineups', {})
                
                for side in ['away', 'home']:
                    team_info = game.get('teams', {}).get(side, {}).get('team', {})
                    team_name = team_info.get('name')
                    
                    if team_name and game_date:
                        game_times[team_name] = game_date
                        for short, full in franchise_map.items():
                            if full == team_name:
                                game_times[short] = game_date
                                
                    team_players = lineups_data.get(f'{side}Players', [])
                    if team_players:
                        normalized_players = [normalize_player_name(p.get('fullName')) for p in team_players]
                        lineups[team_name] = normalized_players
                        # Also map the short name if possible
                        for short, full in franchise_map.items():
                            if full == team_name:
                                lineups[short] = normalized_players
                                
            lineups["_game_times"] = game_times
            return lineups
        except Exception as e:
            print(f"[LINEUPS]: Error fetching confirmed lineups: {e}")
            return {}

if __name__ == "__main__":
    fetcher = LineupFetcher()
    lineups = fetcher.fetch_confirmed_lineups()
    for team, players in lineups.items():
        print(f"{team}: {len(players)} players confirmed.")
