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

    def _load_state(self):
        state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineup_fetcher_state.json")
        if os.path.exists(state_file):
            try:
                with open(state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"consecutive_failures": 0}

    def _save_state(self, state):
        state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lineup_fetcher_state.json")
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f)
        except Exception:
            pass

    def _set_degraded_health(self):
        health_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data_health.json")
        try:
            health = {}
            if os.path.exists(health_file):
                with open(health_file, 'r', encoding='utf-8') as f:
                    health = json.load(f)
            health["status"] = "degraded"
            msg = "RotoWire scraper failed 3 consecutive times — circuit breaker serving cached data."
            if "warnings" not in health:
                health["warnings"] = []
            if msg not in health["warnings"]:
                health["warnings"].append(msg)
            with open(health_file, 'w', encoding='utf-8') as f:
                json.dump(health, f, indent=2)
        except Exception as e:
            print(f"[LINEUPS]: Error updating health file to degraded: {e}")

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
                    
                    # Graceful pitcher tag parsing (Additional Requirement 1)
                    pitchers_data = []
                    try:
                        p_highlight = ul.select_one('.lineup__player-highlight')
                        if p_highlight:
                            p_name_el = p_highlight.select_one('.lineup__player-highlight-name')
                            if p_name_el:
                                a_tags = p_name_el.find_all('a')
                                if not a_tags:
                                    p_text = p_name_el.text.strip()
                                    p_name = p_text.split('\n')[0].strip()
                                    is_o = "(O)" in p_text or "opener" in p_text.lower()
                                    is_b = "(B)" in p_text or "bulk" in p_text.lower() or "primary" in p_text.lower()
                                    pitchers_data.append({
                                        'name': p_name,
                                        'rw_is_opener': is_o,
                                        'rw_is_bulk': is_b
                                    })
                                else:
                                    text_content = p_name_el.text
                                    for a in a_tags:
                                        p_name = a.get('title') or a.text.strip()
                                        sibling_text = ""
                                        next_sib = a.next_sibling
                                        while next_sib and not next_sib.name:
                                            sibling_text += str(next_sib)
                                            next_sib = next_sib.next_sibling
                                        is_o = "(O)" in sibling_text or "opener" in sibling_text.lower()
                                        is_b = "(B)" in sibling_text or "bulk" in sibling_text.lower() or "primary" in sibling_text.lower()
                                        if len(a_tags) == 1:
                                            if not is_o:
                                                is_o = "(O)" in text_content or "opener" in text_content.lower()
                                            if not is_b:
                                                is_b = "(B)" in text_content or "bulk" in text_content.lower() or "primary" in text_content.lower()
                                        pitchers_data.append({
                                            'name': p_name,
                                            'rw_is_opener': is_o,
                                            'rw_is_bulk': is_b
                                        })
                    except Exception as e:
                        print(f"[LINEUPS WARNING]: RotoWire pitcher tag parsing failed: {e}")
                        pitchers_data = []
                    
                    if len(players) >= 7 or pitchers_data:
                        rotowire_lineups[team_name] = {
                            'lineup': players,
                            'is_confirmed': is_confirmed,
                            'pitchers': pitchers_data
                        }
            
            if not rotowire_lineups:
                raise Exception("Scraper returned 0 lineups.")

            # Reset failure count on success
            state = self._load_state()
            state["consecutive_failures"] = 0
            self._save_state(state)

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
            
            # Increment failure count
            state = self._load_state()
            state["consecutive_failures"] = state.get("consecutive_failures", 0) + 1
            self._save_state(state)
            
            if state["consecutive_failures"] >= 3:
                print(f"[LINEUPS]: RotoWire has failed {state['consecutive_failures']} consecutive times. Circuit breaker active. Serving stale cache.")
                self._set_degraded_health()

            # Try to return expired cache as fallback
            if os.path.exists(self.cache_file):
                try:
                    with open(self.cache_file, 'r', encoding='utf-8') as f:
                        cache_data = json.load(f)
                    print("[LINEUPS]: Returning expired RotoWire cache as fallback.")
                    return cache_data.get('lineups', {})
                except Exception as ce:
                    print(f"[LINEUPS]: Failed to read RotoWire cache fallback: {ce}")
            return {}

    def fetch_mlbdotcom_lineups(self):
        """
        Scrapes projected starting lineups from MLB.com/starting-lineups.
        MLB.com publishes projected lineups in a __NEXT_DATA__ JSON blob by ~10am ET daily,
        which is several hours before StatsAPI confirms them — making it ideal for
        projected lineup consensus validation.

        Returns a dict: {
            'Team Name': {
                'lineup': ['Player 1', 'Player 2', ...],
                'is_confirmed': True/False
            }
        }
        """
        import json as _json
        import re as _re

        mlbdotcom_lineups = {}
        try:
            url = "https://www.mlb.com/starting-lineups"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept-Language': 'en-US,en;q=0.9',
            }
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                print(f"[LINEUPS]: MLB.com Starting Lineups returned status {r.status_code}")
                return {}

            # Extract the __NEXT_DATA__ JSON blob embedded in the page
            match = _re.search(r'<script id="__NEXT_DATA__" type="application/json">(.+?)</script>', r.text, _re.DOTALL)
            if not match:
                print("[LINEUPS]: MLB.com __NEXT_DATA__ script tag not found")
                return {}

            raw_json = match.group(1)
            page_data = _json.loads(raw_json)

            # Navigate the Next.js data structure to find lineup entries
            # Path: props -> pageProps -> lineups (list of game lineup objects)
            props = page_data.get('props', {})
            page_props = props.get('pageProps', {})

            # Try multiple known paths for the lineup data
            lineups_list = (
                page_props.get('lineups') or
                page_props.get('data', {}).get('lineups') or
                page_props.get('initialData', {}).get('lineups') or
                []
            )

            if not lineups_list:
                # Fallback: flatten the entire props dict looking for lineup arrays
                raw_str = raw_json
                # Look for battingOrder arrays as a signal of lineup data
                if 'battingOrder' not in raw_str and 'lineup' not in raw_str.lower():
                    print("[LINEUPS]: MLB.com page has no lineup data yet today")
                    return {}

            for game_obj in lineups_list:
                for side in ['away', 'home']:
                    team_obj = game_obj.get(side) or game_obj.get(f'{side}Team') or {}
                    team_name = (
                        team_obj.get('fullName') or
                        team_obj.get('teamName') or
                        team_obj.get('name')
                    )
                    if not team_name:
                        continue

                    # Normalize to full franchise name
                    team_name_norm = ROTOWIRE_TEAM_MAP.get(team_name, team_name)

                    lineup_data = (
                        game_obj.get(f'{side}Lineup') or
                        team_obj.get('lineup') or
                        team_obj.get('battingOrder') or
                        []
                    )

                    players = []
                    is_confirmed = False
                    for entry in lineup_data:
                        if isinstance(entry, dict):
                            name = (
                                entry.get('fullName') or
                                entry.get('name') or
                                entry.get('displayName')
                            )
                            if name:
                                players.append(normalize_player_name(name))
                            # Check confirmation status
                            if entry.get('status') == 'confirmed' or entry.get('isConfirmed'):
                                is_confirmed = True
                        elif isinstance(entry, str):
                            players.append(normalize_player_name(entry))

                    if len(players) >= 7:
                        mlbdotcom_lineups[team_name_norm] = {
                            'lineup': players,
                            'is_confirmed': is_confirmed
                        }

            if mlbdotcom_lineups:
                print(f"[LINEUPS]: MLB.com Starting Lineups returned {len(mlbdotcom_lineups)} teams")
            else:
                print("[LINEUPS]: MLB.com returned page but no structured lineup data parsed — likely pre-release")

            return mlbdotcom_lineups

        except Exception as e:
            print(f"[LINEUPS]: Error fetching MLB.com Starting Lineups: {e}")
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
        Combines StatsAPI confirmed, RotoWire projected/confirmed, and ESPN lineups with consensus logic.
        Returns a dict: {
            'Team Name': {
                'lineup': ['Player 1', 'Player 2', ...],
                'status': 'CONFIRMED' | 'PROJECTED_HIGH_CONF' | 'PROJECTED_LOW_CONF' | 'ROSTER FALLBACK'
            }
        }
        """
        statsapi_confirmed = self.fetch_statsapi_confirmed_lineups(date_str)
        rotowire_lineups = self.fetch_rotowire_lineups()
        
        # Sprint 2 (Updated): MLB.com Starting Lineups as secondary consensus source
        # MLB.com publishes projected lineups ~10am ET daily via __NEXT_DATA__ JSON,
        # much earlier than ESPN which only shows confirmed lineups.
        mlbdotcom_lineups = {}
        try:
            mlbdotcom_lineups = self.fetch_mlbdotcom_lineups()
        except Exception as e:
            print(f"[LINEUPS]: Failed fetching MLB.com Starting Lineups: {e}")

        all_lineups = {}

        # 1. Base on RotoWire projected or confirmed lineups
        for team_name, info in rotowire_lineups.items():
            lineup_players = info['lineup']
            is_confirmed = info['is_confirmed']
            
            if is_confirmed:
                status = 'CONFIRMED'
            else:
                # If RotoWire is projected, check consensus with MLB.com Starting Lineups
                mlb_info = mlbdotcom_lineups.get(team_name)
                if not mlb_info or not mlb_info.get('lineup'):
                    # Default to high confidence if MLB.com is empty (pre-release window)
                    status = 'PROJECTED_HIGH_CONF'
                else:
                    mlb_players = set(mlb_info['lineup'])
                    rw_players = set(lineup_players)
                    if not rw_players:
                        status = 'PROJECTED_LOW_CONF'
                    else:
                        overlap = len(rw_players.intersection(mlb_players)) / len(rw_players)
                        if overlap >= 0.80:
                            status = 'PROJECTED_HIGH_CONF'
                        else:
                            status = 'PROJECTED_LOW_CONF'
            
            all_lineups[team_name] = {
                'lineup': lineup_players,
                'status': status
            }

        # 2. Overwrite with official StatsAPI confirmed lineups (highest authority)
        for team_name, players in statsapi_confirmed.items():
            if team_name == "_game_times":
                continue
            all_lineups[team_name] = {
                'lineup': players,
                'status': 'CONFIRMED'
            }

        # 3. Roster fallback: for any team still missing, pull from statcast cache sorted by OPS
        try:
            sc_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "statcast_cache.json")
            if os.path.exists(sc_path):
                with open(sc_path, 'r', encoding='utf-8') as f:
                    sc_cache = json.load(f)
                # Build team → sorted hitter list
                roster_by_team = {}
                for pname, pdata in sc_cache.items():
                    if pdata.get('type') == 'hitter' and pdata.get('ops', 0) > 0:
                        t = pdata.get('team', '')
                        if t:
                            roster_by_team.setdefault(t, []).append((pname, pdata.get('ops', 0)))
                for t, players in roster_by_team.items():
                    if t not in all_lineups:
                        sorted_players = [p for p, _ in sorted(players, key=lambda x: x[1], reverse=True)[:9]]
                        if sorted_players:
                            all_lineups[t] = {
                                'lineup': sorted_players,
                                'status': 'ROSTER FALLBACK'
                            }
        except Exception as e:
            print(f"[LINEUPS]: Roster fallback failed: {e}")

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
            if isinstance(info, dict) and info.get('status') in ('PROJECTED', 'PROJECTED_HIGH_CONF', 'PROJECTED_LOW_CONF'):
                projected[team] = info['lineup']
        return projected

if __name__ == "__main__":
    fetcher = LineupFetcher()
    all_lineups = fetcher.fetch_all_lineups()
    for team, info in all_lineups.items():
        if team == "_game_times":
            continue
        print(f"{team} [{info['status']}]: {len(info['lineup'])} players.")
