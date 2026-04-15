import requests
from bs4 import BeautifulSoup
import json
import os
import sys

# Support for standalone execution
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config


class ConsensusFetcher:
    """
    OMEGA v5.2: VSiN Consensus Scraper
    Scrapes public betting splits (Ticket % vs Money %) from VSiN (DraftKings-owned).
    Falls back to the local consensus_splits_live.json cache if the scrape fails.
    """

    def __init__(self):
        # [OMEGA v5.2.8]: Source Pivot to ScoresAndOdds (Resilient source)
        self.url = "https://www.scoresandodds.com/mlb/consensus-picks"
        self.cache_path = os.path.join(os.path.dirname(__file__), "consensus_splits_live.json")

        self.team_abbrev = {
            'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
            'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
            'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
            'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
            'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
            'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
            'New York Yankees': 'NYY', 'Athletics': 'ATH', 'Oakland Athletics': 'ATH',
            'Philadelphia Phillies': 'PHI', 'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD',
            'San Francisco Giants': 'SF', 'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL',
            'Tampa Bay Rays': 'TB', 'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR',
            'Washington Nationals': 'WSH'
        }

    def fetch_splits(self):
        """
        Attempts to scrape live splits from ScoresAndOdds.
        """
        print("  [CONSENSUS]: Attempting ScoresAndOdds live scrape (Mirror Unfreeze)...")
        live_data = self._scrape_scoresandodds()

        if live_data and len(live_data) > 2:
            print(f"  [CONSENSUS]: SUCCESS - Scraped {len(live_data)} teams from ScoresAndOdds.")
            self._save_cache(live_data)
            return live_data

        # Fallback to local cache
        print("  [CONSENSUS]: ScoresAndOdds scrape returned empty. Loading local cache...")
        return self._load_cache()

    def _scrape_scoresandodds(self):
        """
        Scrapes ScoresAndOdds Consensus Picks page.
        """
        try:
            # v5.2.8: Using more realistic headers to avoid blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers, timeout=15)
            response.raise_for_status()
            return self._parse_table(response.text)
        except Exception as e:
            print(f"  [CONSENSUS]: Scrape error: {e}")
            return {}



    def _parse_table(self, html):
        """
        [OMEGA v5.2.9]: Card-Based Side Isolation Parser
        Ensures Visitor (a) and Home (b) percentages are correctly attributed.
        """
        soup = BeautifulSoup(html, 'html.parser')
        splits = {}
        found_matchups = 0

        # Scan each game card
        cards = soup.select('div.trend-card.consensus')
        for card in cards:
            try:
                # 1. Extract Teams (Visitor first, then Home)
                side_container = card.select_one('.trend-graph-sides')
                if not side_container: continue
                sides = side_container.find_all('strong')
                if len(sides) < 2: continue
                
                v_name = sides[0].get_text(strip=True).upper()
                h_name = sides[1].get_text(strip=True).upper()
                
                # Fuzzy Mapping
                v_abbr, h_abbr = None, None
                for full_name, abbr in self.team_abbrev.items():
                    full_upper = full_name.upper()
                    if v_name in full_upper or full_upper in v_name:
                        v_abbr = abbr
                    if h_name in full_upper or full_upper in h_name:
                        h_abbr = abbr
                
                # Check for direct Abbreviation match
                if not v_abbr:
                     for abbr in self.team_abbrev.values():
                         if abbr in v_name: v_abbr = abbr
                if not h_abbr:
                     for abbr in self.team_abbrev.values():
                         if abbr in h_name: h_abbr = abbr

                # 2. Extract Percentage Rows (Row 1: Bets, Row 2: Money)
                pct_rows = card.select('.trend-graph-percentage')
                if len(pct_rows) < 2: continue
                
                # Bets Row
                bets_v = int(pct_rows[0].select_one('.percentage-a').get_text(strip=True).replace('%', ''))
                bets_h = int(pct_rows[0].select_one('.percentage-b').get_text(strip=True).replace('%', ''))
                
                # Money Row
                money_v = int(pct_rows[1].select_one('.percentage-a').get_text(strip=True).replace('%', ''))
                money_h = int(pct_rows[1].select_one('.percentage-b').get_text(strip=True).replace('%', ''))
                
                if v_abbr:
                    splits[v_abbr] = {'ticket': bets_v, 'money': money_v}
                if h_abbr:
                    splits[h_abbr] = {'ticket': bets_h, 'money': money_h}
                
                if v_abbr or h_abbr:
                    found_matchups += 1
            except Exception as e:
                continue

        if found_matchups > 0:
             print(f"  [CONSENSUS]: Synchronized {found_matchups} side-isolated matchups.")
        return splits






    def _save_cache(self, data):
        """Saves scraped splits to local cache file."""
        try:
            with open(self.cache_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"  [CONSENSUS]: Cache save error: {e}")

    def _load_cache(self):
        """Loads splits from local cache file."""
        if not os.path.exists(self.cache_path):
            print("  [CONSENSUS]: No cache file found. Returning empty splits.")
            return {}
        try:
            with open(self.cache_path, 'r') as f:
                data = json.load(f)
            print(f"  [CONSENSUS]: Loaded {len(data)} teams from cache.")
            return data
        except Exception as e:
            print(f"  [CONSENSUS]: Cache load error: {e}")
            return {}

    def get_team_split(self, team_full_name, splits_data):
        """
        Looks up a team's split data by full name.
        Returns {'ticket': int, 'money': int} or None.
        """
        abbrev = self.team_abbrev.get(team_full_name)
        if not abbrev:
            return None
        return splits_data.get(abbrev)

    def get_divergence(self, team_full_name, splits_data):
        """
        Calculates divergence: Money % - Ticket %.
        """
        split = self.get_team_split(team_full_name, splits_data)
        if not split:
            return 0
        return split.get('money', 0) - split.get('ticket', 0)

    def detect_whale(self, team_full_name, splits_data):
        """
        OMEGA v5.2: WHALE Signal.
        Fires if divergence is >= 15% AND absolute money is significant (> 25%).
        """
        split = self.get_team_split(team_full_name, splits_data)
        if not split: return False
        
        div = split.get('money', 0) - split.get('ticket', 0)
        return div >= 15 and split.get('money', 0) >= 25

    def is_sharp_consensus(self, team_full_name, splits_data):
        """
        OMEGA v5.2: SHARP CONSENSUS Signal.
        Fires if big money is concentrated (> 65%) REGARDLESS of tickets.
        """
        split = self.get_team_split(team_full_name, splits_data)
        if not split: return False
        return split.get('money', 0) >= 65

    def detect_shark(self, team_full_name, splits_data, ml_move=0.0):
        """
        OMEGA v5.2: SHARK (Reverse Line Movement) Detection.
        
        A SHARK signal fires when ALL THREE conditions are met:
        1. The team has < 40% of public TICKETS (public is clearly fading them)
        2. The team has disproportionately MORE MONEY than tickets (divergence >= 10)
        3. The moneyline has moved at least 10 cents IN FAVOR of this team despite the public fade.
        
        Returns True if SHARK conditions are met.
        """
        split = self.get_team_split(team_full_name, splits_data)
        if not split:
            return False

        ticket_pct = split.get('ticket', 50)
        money_pct = split.get('money', 50)

        # Condition 1: Public is clearly NOT on this team (< 40% tickets)
        if ticket_pct >= 40:
            return False

        # Condition 2: Sharp money divergence (big money, few tickets)
        divergence = money_pct - ticket_pct
        if divergence < 10:
            return False

        # Condition 3: Line has actively moved IN FAVOR of this team by at least 10 cents
        if ml_move < 10:
            return False

        return True


if __name__ == "__main__":
    fetcher = ConsensusFetcher()
    data = fetcher.fetch_splits()
    print(json.dumps(data, indent=2))

    # Test SHARK detection with cached data
    test_teams = ['San Diego Padres', 'Milwaukee Brewers', 'Boston Red Sox', 'New York Yankees']
    for team in test_teams:
        is_shark = fetcher.detect_shark(team, data)
        split = fetcher.get_team_split(team, data)
        print(f"  {team}: {split} -> SHARK: {is_shark}")
