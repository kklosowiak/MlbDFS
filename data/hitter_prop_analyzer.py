import os
import sys

# Standalone execution support
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from utils.normalization import normalize_player_name
from data.statcast_bridge import StatcastBridge

class HitterPropAnalyzer:
    def __init__(self):
        self.target_market = 'batter_home_runs'
        self.xwoba_registry = {
            'Fernando Tatis Jr.': 0.395, 'Francisco Lindor': 0.370, 'Ketel Marte': 0.382,
            'Christian Walker': 0.358, 'Xander Bogaerts': 0.345, 'Vinnie Pasquantino': 0.355,
            'Jackson Merrill': 0.342, 'Brandon Nimmo': 0.348, 'Andrew Vaughn': 0.335,
            'Luis Robert Jr.': 0.385, 'Bo Bichette': 0.368, 'Nolan Jones': 0.352,
            'Ryan McMahon': 0.338, 'Ezequiel Tovar': 0.325, 'Edouard Julien': 0.345,
            'Juan Soto': 0.425, 'Aaron Judge': 0.430, 'Shohei Ohtani': 0.420,
            'Teoscar Hernandez': 0.375, 'Mookie Betts': 0.390,
            'Royce Lewis': 0.385, 'Gunnar Henderson': 0.395, 'Pete Alonso': 0.415
        }
        self.team_code_map = {
            'BAL': 'Baltimore Orioles', 'NYM': 'New York Mets', 'SF': 'San Francisco Giants', 'SFG': 'San Francisco Giants',
            'LAD': 'Los Angeles Dodgers', 'ATL': 'Atlanta Braves', 'ARI': 'Arizona Diamondbacks',
            'PHI': 'Philadelphia Phillies', 'NYY': 'New York Yankees', 'BOS': 'Boston Red Sox',
            'TOR': 'Toronto Blue Jays', 'TB': 'Tampa Bay Rays', 'TBR': 'Tampa Bay Rays', 'TBA': 'Tampa Bay Rays',
            'CLE': 'Cleveland Guardians', 'MIN': 'Minnesota Twins', 'DET': 'Detroit Tigers', 'KC': 'Kansas City Royals', 'KCR': 'Kansas City Royals',
            'CHW': 'Chicago White Sox', 'CWS': 'Chicago White Sox', 'HOU': 'Houston Astros', 'SEA': 'Seattle Mariners',
            'TEX': 'Texas Rangers', 'LAA': 'Los Angeles Angels', 'OAK': 'Oakland Athletics',
            'MIL': 'Milwaukee Brewers', 'CHC': 'Chicago Cubs', 'CIN': 'Cincinnati Reds',
            'STL': 'St. Louis Cardinals', 'PIT': 'Pittsburgh Pirates', 'SD': 'San Diego Padres', 'SDP': 'San Diego Padres',
            'COL': 'Colorado Rockies', 'MIA': 'Miami Marlins', 'WSH': 'Washington Nationals', 'WSN': 'Washington Nationals'
        }
        self.statcast = StatcastBridge()

    def decimal_to_american(self, decimal):
        """Converts decimal odds to American format."""
        if decimal >= 2.0:
            return int((decimal - 1) * 100)
        else:
            return int(-100 / (decimal - 1))

    def load_external_worksheet_props(self, filepath):
        """Bridge to user's local Downloads worksheet (v3.10.0)."""
        import os, csv
        external_props = {}
        if not os.path.exists(filepath): return external_props
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('market') == 'batter_home_runs':
                        p_name = row.get('description')
                        try:
                            raw_price = float(row.get('price', 0))
                            if raw_price > 0:
                                # Convert to American if decimal, else keep as is
                                clean_price = self.decimal_to_american(raw_price) if raw_price < 100 else int(raw_price)
                                if p_name not in external_props:
                                    external_props[p_name] = clean_price
                        except: continue
        except: pass
        return external_props

    def extract_top_hitters(self, snapshot_path):
        """Extracts individual hitters with AHR and Hit props for OMEGA Signals (v3.10.0)."""
        # OMEGA v3.10.0: External Bridge
        external_file = r"C:\Users\konra\Downloads\batter over_under - Sheet1.csv"
        ext_props = self.load_external_worksheet_props(external_file)
        
        try:
            with open(snapshot_path, 'r') as f:
                snapshot = json.load(f)
        except: return []

        props_all = snapshot.get('props', {})
        odds = snapshot.get('odds', [])
        
        # OMEGA v4.5.1: Strict Slate Isolation - Only track teams in the current odds
        active_teams = set()
        for g in odds:
            active_teams.add(g['home_team'])
            active_teams.add(g['away_team'])

        game_map = {g['id']: {'home': g['home_team'], 'away': g['away_team']} for g in odds}
        hitter_map = {}
        
        # Ingest API props
        for gid, markets in props_all.items():
            matchup = game_map.get(gid, {})
            if not matchup: continue
            
            for m_key in ['batter_home_runs', 'batter_hits', 'batter_total_bases', 'batter_stolen_bases']:
                market_data = markets.get(m_key, [])
                for entry in market_data:
                    player_name = entry.get('player_name')
                    if not player_name or player_name in ["Yes", "No"]: continue
                    
                    price = entry.get('price', 1000)
                    if 1.0 < price < 100.0:
                        price = self.decimal_to_american(price)

                    if player_name not in hitter_map:
                        # OMEGA v4.5.9: Pass 'side' metadata for discovery
                        side_hint = entry.get('side')
                        team_side = self.resolve_team_side(player_name, matchup['home'], matchup['away'], market_side=side_hint)
                        
                        # OMEGA v4.5.6: Zero-Ghost Roster Gate
                        if team_side is None or team_side not in active_teams:
                            continue

                        # OMEGA v6.5: Dynamic Momentum Priority (Rolling 10-Day fallback)
                        momentum = self.statcast.get_player_momentum(player_name) or {}
                        if momentum.get('rolling_pa', 0) > 15:
                            momentum_ops = momentum.get('rolling_ops',0)
                        else:
                            momentum_ops = momentum.get('ops', 0)
                            
                        hitter_map[player_name] = {
                            'name': player_name,
                            'team': team_side,
                            'home_team': matchup['home'],
                            'away_team': matchup['away'],
                            'event_id': gid,
                            'ahr_price': price if m_key == 'batter_home_runs' else 1000,
                            'hit_line': 0.5,
                            'hits_price': 0,
                            'is_juiced_target': False,
                            'is_speed_target': False,
                            'matchup_xwoba': momentum_ops / 2.5 if momentum_ops > 0 else self.xwoba_registry.get(player_name, 0.330)
                        }
                    
                    if m_key == 'batter_home_runs':
                        current_best = hitter_map[player_name].get('ahr_price', 1000)
                        if price < current_best:
                            hitter_map[player_name]['ahr_price'] = price
                            
                    elif m_key in ['batter_hits', 'batter_total_bases']:
                        # OMEGA v5.0.2: Juice Target Detection & Hit-Seeker Logic
                        new_line = entry.get('point', 0.5)
                        current_line = hitter_map[player_name].get('hit_line', 1.5)
                        if current_line > 0.5:
                            hitter_map[player_name]['hit_line'] = new_line
                        
                        hits_price = entry.get('price', 0)
                        if 1.0 < hits_price < 100.0: hits_price = self.decimal_to_american(hits_price)
                        hitter_map[player_name]['hits_price'] = hits_price

                        # Detection
                        side = entry.get('side')
                        if side == 'Over':
                            o_price = hits_price
                            pt = entry.get('point')
                            book = entry.get('bookmaker')
                            # Match with Under in same market list
                            matching = [e for e in market_data if e.get('player_name') == player_name and e.get('side') == 'Under' and e.get('bookmaker') == book and e.get('point') == pt]
                            if matching:
                                u_price = matching[0].get('price', 0)
                                if 1.0 < u_price < 100.0: u_price = self.decimal_to_american(u_price)
                                if o_price < u_price:
                                    hitter_map[player_name]['is_juiced_target'] = True
                                    
                    elif m_key == 'batter_stolen_bases':
                        side = entry.get('side')
                        if side == 'Over' and entry.get('point', 0.5) >= 0.5:
                            sb_price = entry.get('price', 0)
                            if 1.0 < sb_price < 100.0: sb_price = self.decimal_to_american(sb_price)
                            # THIEF Metric: Stolen Base Over 0.5 price is aggressive (e.g. better than +250 odds)
                            # Typically SB props are +300 or +400. If it's +220 or +180, sharp money expects a steal.
                            if -500 < sb_price <= 250:
                                hitter_map[player_name]['is_speed_target'] = True
        
        # OMEGA v3.2.1: Weighted Worksheet Bridge
        for p_ext, price_ext in ext_props.items():
            norm_ext = normalize_player_name(p_ext)
            
            # Use normalized matching for the hitter_map bridge
            found_key = None
            for hm_key in hitter_map:
                if normalize_player_name(hm_key) == norm_ext:
                    found_key = hm_key
                    break
            
            if found_key:
                hitter_map[found_key]['ahr_price'] = price_ext
                
        # OMEGA v6.2: Final Convergence Validation
        # Add hitters discoverable via pitcher matchups in the snapshot
        # (This is handled dynamically in the extract_top_hitters loop now)
        
        # Convert map to sorted list by AHR price
        h_list = list(hitter_map.values())
        return sorted(h_list, key=lambda x: x['ahr_price'])

    def resolve_team_side(self, player_name, home_t, away_t, market_side=None):
        """
        Dynamically determines if a player belongs to the home or away side.
        OMEGA v6.2.2: Strict Roster Gatekeeper (Anti-Ghosting Protocol).
        """
        norm_name = normalize_player_name(player_name)
        
        # 1. API Side Hint (Highest Confidence - direct from bookmaker)
        if market_side == "home": return home_t
        if market_side == "away": return away_t

        # 2. Identify the player's "Official" Team (Cache or Anchor)
        momentum = self.statcast.get_player_momentum(player_name)
        cached_code = momentum.get('team', '').upper() if momentum else None
        cached_team = self.team_code_map.get(cached_code) if cached_code else None
        
        anchors = self.get_anchor_teams()
        anchor_team = None
        for t, roster in anchors.items():
            if any(normalize_player_name(member) == norm_name for member in roster):
                anchor_team = t
                break
        
        official_team = cached_team or anchor_team

        # 3. THE PURGE GATE: If the player is a known member of a different active team,
        # and that team is NOT part of this game, we REJECT them as a prop-leak/ghost.
        if official_team:
            if official_team == home_t: return home_t
            if official_team == away_t: return away_t
            
            # If the player is on a verified team that IS NOT in this matchup, 
            # they are a "Ghost" from another API block.
            return None

        # 4. Final Blind Resolution (Only for "Unfiltered Arrivals" with no anchor record)
        # We only do this if we have no reason to believe they belong elsewhere.
        # Note: This allows rookies or extremely new players to be mapped to the slate.
        # But for 2026, we lean on Mutual Exclusion ONLY if they aren't 'Zombies'.
        return None 

    def get_anchor_teams(self):
        """
        OMEGA v6.2.2 Roster Repository (2026 Monday Slate Sync).
        Updated with verified 2026 pitcher assignments to ensure dynamic discovery alignment.
        """
        return {
            'Arizona Diamondbacks': ['Corbin Carroll', 'Ketel Marte', 'Christian Walker', 'Eugenio Suárez', 'Lourdes Gurriel Jr.', 'Gabriel Moreno', 'Trea Turner', 'Nolan Arenado', 'Zac Gallen', 'Merrill Kelly'],
            'Atlanta Braves': ['Ronald Acuña Jr.', 'Matt Olson', 'Austin Riley', 'Ozzie Albies', 'Max Fried', 'Spencer Strider'],
            'Baltimore Orioles': ['Gunnar Henderson', 'Adley Rutschman', 'Pete Alonso', 'Colton Cowser', 'Jackson Holliday', 'Corbin Burnes', 'Grayson Rodriguez'],
            'Boston Red Sox': ['Triston Casas', 'Jarren Duran', 'Tyler O\'Neill', 'Lucas Giolito', 'Nick Pivetta'],
            'Chicago Cubs': ['Dansby Swanson', 'Cody Bellinger', 'Seiya Suzuki', 'Ian Happ', 'Justin Steele', 'Shota Imanaga'],
            'Chicago White Sox': ['Andrew Vaughn', 'Eloy Jiménez', 'Andrew Benintendi', 'Munetaka Murakami', 'Luis Robert Jr.', 'Garrett Crochet'],
            'Cincinnati Reds': ['Elly De La Cruz', 'Spencer Steer', 'TJ Friedl', 'Jeimer Candelario', 'Hunter Greene', 'Nick Lodolo'],
            'Cleveland Guardians': ['José Ramírez', 'Josh Naylor', 'Steven Kwan', 'Andrés Giménez', 'Shane Bieber', 'Tanner Bibee'],
            'Colorado Rockies': ['Nolan Jones', 'Ezequiel Tovar', 'Ryan McMahon', 'Kris Bryant', 'Brendan Rodgers', 'Germán Márquez'],
            'Detroit Tigers': ['Riley Greene', 'Spencer Torkelson', 'Kerry Carpenter', 'Colt Keith', 'Tarik Skubal', 'Casey Mize'],
            'Houston Astros': ['Yordan Alvarez', 'Jose Altuve', 'Kyle Tucker', 'Alex Bregman', 'Framber Valdez', 'Justin Verlander'],
            'Kansas City Royals': ['Bobby Witt Jr.', 'Salvador Perez', 'Vinnie Pasquantino', 'MJ Melendez', 'Maikel Garcia', 'Cole Ragans', 'Seth Lugo'],
            'Los Angeles Angels': ['Mike Trout', 'Logan O\'Hoppe', 'Anthony Rendon', 'Zach Neto', 'Patrick Sandoval', 'Reid Detmers', 'Tyler Anderson'],
            'Los Angeles Dodgers': ['Shohei Ohtani', 'Mookie Betts', 'Freddie Freeman', 'Teoscar Hernández', 'Yoshinobu Yamamoto', 'Tyler Glasnow'],
            'Miami Marlins': ['Jazz Chisholm Jr.', 'Bryan De La Cruz', 'Jesús Sánchez', 'Eury Pérez', 'Jesús Luzardo', 'Braxton Garrett', 'Sandy Alcantara'],
            'Milwaukee Brewers': ['Christian Yelich', 'William Contreras', 'Jackson Chourio', 'Freddy Peralta'],
            'Minnesota Twins': ['Royce Lewis', 'Byron Buxton', 'Carlos Correa', 'Pablo Lopez', 'Edouard Julien', 'Matt Wallner', 'Joe Ryan', 'Bailey Ober'],
            'New York Mets': ['Francisco Lindor', 'Brandon Nimmo', 'Starling Marte', 'Jeff McNeil', 'Edwin Díaz', 'Kodai Senga', 'Luis Severino'],
            'New York Yankees': ['Aaron Judge', 'Juan Soto', 'Giancarlo Stanton', 'Gleyber Torres', 'Anthony Volpe', 'Clay Holmes', 'Gerrit Cole', 'Carlos Rodón', 'Marcus Stroman', 'Will Warren', 'Luis Gil'],
            'Oakland Athletics': ['Brent Rooker', 'Shea Langeliers', 'Zack Gelof', 'JJ Bleday', 'Luis Severino', 'JP Sears', 'Ross Stripling'],
            'Philadelphia Phillies': ['Bryce Harper', 'Kyle Schwarber', 'Trea Turner', 'Nick Castellanos', 'Taijuan Walker', 'Zack Wheeler', 'Aaron Nola'],
            'Pittsburgh Pirates': ['Bryan Reynolds', 'Oneil Cruz', 'Ke\'Bryan Hayes', 'Paul Skenes', 'Mitch Keller', 'Jared Jones'],
            'San Diego Padres': ['Fernando Tatis Jr.', 'Manny Machado', 'Xander Bogaerts', 'Jackson Merrill', 'Luis Campusano', 'Jake Cronenworth', 'Joe Musgrove', 'Yu Darvish', 'Dylan Cease'],
            'San Francisco Giants': ['Rafael Devers', 'Willy Adames', 'Matt Chapman', 'Jung Hoo Lee', 'Logan Webb', 'Thairo Estrada', 'Kyle Harrison', 'Blake Snell'],
            'Seattle Mariners': ['Julio Rodríguez', 'Cal Raleigh', 'Randy Arozarena', 'J.P. Crawford', 'Luis Castillo', 'George Kirby', 'Logan Gilbert'],
            'St. Louis Cardinals': ['Nolan Arenado', 'Paul Goldschmidt', 'Willson Contreras', 'Sonny Gray', 'Miles Mikolas'],
            'Tampa Bay Rays': ['Yandy Díaz', 'Isaac Paredes', 'Jose Siri', 'Brandon Lowe', 'Zach Eflin', 'Shane Baz'],
            'Texas Rangers': ['Corey Seager', 'Adolis García', 'Marcus Semien', 'Josh Jung', 'Jack Leiter', 'Nathan Eovaldi', 'Jacob deGrom'],
            'Toronto Blue Jays': ['Vladimir Guerrero Jr.', 'George Springer', 'Kevin Gausman', 'Bo Bichette', 'Eric Lauer', 'José Berríos', 'Chris Bassitt'],
            'Washington Nationals': ['CJ Abrams', 'Lane Thomas', 'James Wood', 'MacKenzie Gore', 'Josiah Gray']
        }


    def extract_fallback_hitters(self, snapshot_path):
        """Mandatory v3.2.1.7 Roster Injection if Props Blackout occurs."""
        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)
            odds = snapshot.get('odds', [])
        
        anchors = self.get_anchor_teams()
        fallback_reports = []
        
        for game in odds:
            for side in ['home_team', 'away_team']:
                team = game[side]
                h_names = anchors.get(team, [])
                for name in h_names:
                    fallback_reports.append({
                        'name': name,
                        'team': team,
                        'home_team': game['home_team'],
                        'away_team': game['away_team'],
                        'ahr_price': 800, # Conservative neutral baseline
                        'hit_line': 0.5,
                        'hits_price': -110,
                        'is_speed_target': False,
                        'matchup_xwoba': self.xwoba_registry.get(name, 0.330),
                        'is_fallback': True
                    })
        return fallback_reports
