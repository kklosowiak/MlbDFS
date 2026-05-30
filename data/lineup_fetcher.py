import os
import json
import time
import requests
from datetime import datetime
from bs4 import BeautifulSoup
from utils.normalization import normalize_player_name

ROTOWIRE_TEAM_MAP = {
    'ARI': 'Arizona Diamondbacks',
    'ATL': 'Atlanta Braves',
    'BAL': 'Baltimore Orioles',
    'BOS': 'Boston Red Sox',
    'CHC': 'Chicago Cubs',
    'CWS': 'Chicago White Sox',
    'CHW': 'Chicago White Sox',
    'CIN': 'Cincinnati Reds',
    'CLE': 'Cleveland Guardians',
    'COL': 'Colorado Rockies',
    'DET': 'Detroit Tigers',
    'HOU': 'Houston Astros',
    'KC': 'Kansas City Royals',
    'KCR': 'Kansas City Royals',
    'LAA': 'Los Angeles Angels',
    'LAD': 'Los Angeles Dodgers',
    'MIA': 'Miami Marlins',
    'MIL': 'Milwaukee Brewers',
    'MIN': 'Minnesota Twins',
    'NYM': 'New York Mets',
    'NYY': 'New York Yankees',
    'ATH': 'Oakland Athletics',
    'OAK': 'Oakland Athletics',
    'PHI': 'Philadelphia Phillies',
    'PIT': 'Pittsburgh Pirates',
    'SD': 'San Diego Padres',
    'SDP': 'San Diego Padres',
    'SF': 'San Francisco Giants',
    'SFG': 'San Francisco Giants',
    'SEA': 'Seattle Mariners',
    'STL': 'St. Louis Cardinals',
    'TB': 'Tampa Bay Rays',
    'TBR': 'Tampa Bay Rays',
    'TEX': 'Texas Rangers',
    'TOR': 'Toronto Blue Jays',
    'WSH': 'Washington Nationals',
    'WAS': 'Washington Nationals'
}

class LineupFetcher:
    def __init__(self):
        self.api_url = "https://statsapi.mlb.com/api/v1/schedule"
        self.cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "projected_lineups_cache.json")
        self.cache_expiry = 300  # 5 minutes cache

    def fetch_rotowire_lineups(self):
        """
        Scrapes daily starting lineups from RotoWire's daily lineups page.
        Returns a dict: {
            'Team Name': {
                'lineup': ['Player 1', 'Player 2', ...],
                'is_confirmed': True/False
            }
        }
        """
        # Check cache validity
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                timestamp = cache_data.get('timestamp', 0)
                if time.time() - timestamp < self.cache_expiry:
                    return cache_data.get('lineups', {})
            except Exception as e:
                print(f"[LINEUPS]: Error reading RotoWire cache: {e}")

        # Fetch live data
        url = "https://www.rotowire.com/baseball/daily-lineups.php"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        rotowire_lineups = {}
        try:
            r = requests.get(url, headers=headers, timeout=10)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, 'html.parser')
            
            boxes = soup.select('.lineup__box')
            for box in boxes:
                # Find visiting and home team nodes
                visit_abbr_el = box.select_one('.lineup__team.is-visit .lineup__abbr')
                home_abbr_el = box.select_one('.lineup__team.is-home .lineup__abbr')
                if not visit_abbr_el or not home_abbr_el:
                    continue
                
                visit_abbr = visit_abbr_el.text.strip()
                home_abbr = home_abbr_el.text.strip()
                
                visit_team = ROTOWIRE_TEAM_MAP.get(visit_abbr)
                home_team = ROTOWIRE_TEAM_MAP.get(home_abbr)
                if not visit_team or not home_team:
                    continue
                
                for side, team_name in [('visit', visit_team), ('home', home_team)]:
                    ul = box.select_one(f'.lineup__list.is-{side}')
                    if not ul:
                        continue
                    
                    status_el = ul.select_one('.lineup__status')
                    is_confirmed = False
                    if status_el:
                        is_confirmed = 'confirmed' in status_el.get('class', []) or 'Confirmed' in status_el.text
                    
                    players = []
                    for li in ul.select('.lineup__player'):
                        a = li.find('a')
                        if a:
                            # Use full name in title attribute, fallback to text
                            name = a.get('title') or a.text.strip()
                            players.append(name)
                    
                    if len(players) >= 7:
                        rotowire_lineups[team_name] = {
                            'lineup': players,
                            'is_confirmed': is_confirmed
                        }
            
            # Cache the results
            try:
                with open(self.cache_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'timestamp': time.time(),
                        'lineups': rotowire_lineups
                    }, f, indent=2)
            except Exception as e:
                print(f"[LINEUPS]: Error writing RotoWire cache: {e}")
                
            return rotowire_lineups
        except Exception as e:
            print(f"[LINEUPS]: Error fetching RotoWire lineups: {e}")
            # Try to return expired cache as fallback
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    print("[LINEUPS]: Returning expired RotoWire cache as fallback.")
                    return cache_data.get('lineups', {})
                except:
                    pass
            return {}

    def fetch_statsapi_confirmed_lineups(self, date_str=None):
        """
        Fetches official starting lineups from MLB StatsAPI.
        Returns a dict: { 'Team Name': [ 'Player 1', ... ] }
        """
        if not date_str:
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
                        for short, full in franchise_map.items():
                            if full == team_name:
                                lineups[short] = normalized_players
                                
            lineups["_game_times"] = game_times
            return lineups
        except Exception as e:
            print(f"[LINEUPS]: Error fetching StatsAPI: {e}")
            return {}

    def fetch_all_lineups(self, date_str=None):
        """
        Combines StatsAPI confirmed and RotoWire projected/confirmed lineups.
        Returns a dict: {
            'Team Name': {
                'lineup': ['Player 1', 'Player 2', ...],
                'status': 'CONFIRMED' | 'PROJECTED'
            }
        }
        """
        statsapi_confirmed = self.fetch_statsapi_confirmed_lineups(date_str)
        rotowire_lineups = self.fetch_rotowire_lineups()

        all_lineups = {}

        # 1. Base on RotoWire projected or confirmed lineups (keeps the correct order)
        for team_name, info in rotowire_lineups.items():
            all_lineups[team_name] = {
                'lineup': info['lineup'],
                'status': 'CONFIRMED' if info['is_confirmed'] else 'PROJECTED'
            }

        # 2. Overwrite with official StatsAPI confirmed lineups (highest authority)
        for team_name, players in statsapi_confirmed.items():
            if team_name == "_game_times":
                continue
            all_lineups[team_name] = {
                'lineup': players,
                'status': 'CONFIRMED'
            }

        # Handle game times pass-through
        if "_game_times" in statsapi_confirmed:
            all_lineups["_game_times"] = statsapi_confirmed["_game_times"]

        return all_lineups

    def fetch_confirmed_lineups(self, date_str=None):
        """
        Backwards-compatible: Returns only confirmed lineups.
        """
        all_lineups = self.fetch_all_lineups(date_str)
        confirmed = {}
        for team, info in all_lineups.items():
            if team == "_game_times":
                confirmed["_game_times"] = info
            elif isinstance(info, dict) and info.get('status') == 'CONFIRMED':
                confirmed[team] = info['lineup']
        return confirmed

    def fetch_projected_lineups(self, date_str=None):
        """
        Returns only projected lineups.
        """
        all_lineups = self.fetch_all_lineups(date_str)
        projected = {}
        for team, info in all_lineups.items():
            if team == "_game_times":
                continue
            if isinstance(info, dict) and info.get('status') == 'PROJECTED':
                projected[team] = info['lineup']
        return projected

if __name__ == "__main__":
    fetcher = LineupFetcher()
    all_lineups = fetcher.fetch_all_lineups()
    for team, info in all_lineups.items():
        if team == "_game_times":
            continue
        print(f"{team} [{info['status']}]: {len(info['lineup'])} players.")
