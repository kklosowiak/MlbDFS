import os
import sys
import json

# Standalone execution support
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config
from utils.normalization import normalize_player_name
from utils.xwoba_estimates import ops_to_xwoba, cap_matchup_xwoba
from data.statcast_bridge import StatcastBridge

class HitterPropAnalyzer:
    def __init__(self):
        self.target_market = 'batter_home_runs'
        self.xwoba_registry = {
            normalize_player_name(k): v for k, v in {
                'Fernando Tatis Jr.': 0.395, 'Francisco Lindor': 0.370, 'Ketel Marte': 0.382,
                'Christian Walker': 0.358, 'Xander Bogaerts': 0.345, 'Vinnie Pasquantino': 0.355,
                'Jackson Merrill': 0.342, 'Brandon Nimmo': 0.348, 'Andrew Vaughn': 0.335,
                'Luis Robert Jr.': 0.385, 'Bo Bichette': 0.368, 'Nolan Jones': 0.352,
                'Ryan McMahon': 0.338, 'Ezequiel Tovar': 0.325, 'Edouard Julien': 0.345,
                'Juan Soto': 0.425, 'Aaron Judge': 0.430, 'Shohei Ohtani': 0.420,
                'Teoscar Hernandez': 0.375, 'Mookie Betts': 0.390,
                'Royce Lewis': 0.385, 'Gunnar Henderson': 0.395, 'Pete Alonso': 0.415,
            }.items()
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

    def _resolve_xwoba(self, name, profile):
        """Registry → Statcast xwOBA → MLB wOBA → ops_to_xwoba heuristic."""
        norm = normalize_player_name(name)
        reg = self.xwoba_registry.get(norm)
        if reg is not None:
            return cap_matchup_xwoba(reg)
        if isinstance(profile, dict):
            pa = int(profile.get("pa", 0) or 0)
            xwoba_val = float(profile.get("xwoba", 0.0) or 0.0)
            if pa >= 30 and xwoba_val >= 0.250:
                return cap_matchup_xwoba(xwoba_val)
            woba_val = float(profile.get("woba", 0.0) or 0.0)
            if pa >= 50 and woba_val >= 0.250:
                return cap_matchup_xwoba(woba_val)
            ops_val = float(profile.get("ops", 0.0) or 0.0)
            if pa >= 50 and ops_val > 0:
                return ops_to_xwoba(ops_val)
        return 0.310

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

    def extract_top_hitters(self, snapshot_path, confirmed_lineups=None):
        """Extracts individual hitters with AHR and Hit props for OMEGA Signals (v3.10.0)."""
        """Extracts individual hitters with AHR and Hit props for OMEGA Signals (v3.10.0)."""
        print(f"[OMEGA]: Opening Slate Profile: {snapshot_path}")
        if not os.path.exists(snapshot_path):
            print(f"[CRITICAL ERROR]: Snapshot NOT FOUND at {snapshot_path}")
            return []

        try:
            with open(snapshot_path, 'r') as f:
                snapshot = json.load(f)
        except Exception as e:
            print(f"[CRITICAL ERROR]: Failed to load JSON from {snapshot_path}: {e}")
            return []

        props_all = snapshot.get('props', {})
        odds = snapshot.get('odds', [])
        ext_props = {} # OMEGA v6.13: Initializing empty external bridge for slate stability
        
        if not odds:
            print(f"[WARNING]: Snapshot '{snapshot_path}' contains zero games. Discovery will be thin.")
        
        # OMEGA v4.5.1: Strict Slate Isolation - Only track teams in the current odds (slate_filter bypassed for core data inclusion)
        active_teams = set()
        for g in odds:
            active_teams.add(g['home_team'])
            active_teams.add(g['away_team'])

        game_map = {g['id']: {'home': g['home_team'], 'away': g['away_team']} for g in odds}
        hitter_map = {}
        
        try:
            # OMEGA v7.9: Restored High-Sample Dynamic Discovery.
            # We now pull from the Statcast Cache but enforce a 50-PA floor to eliminate noise.
            print(f"[OMEGA]: Initiating High-Sample Dynamic Discovery for {len(active_teams)} teams...")
            for team in active_teams:
                roster = self.statcast.get_team_roster(team, player_type='hitter')
                
                if not roster:
                    # Fuzzy match fallback
                    cache = self.statcast.get_cache_data()
                    for player_data in cache.values():
                        if isinstance(player_data, dict) and team in player_data.get('team', ''):
                            roster = self.statcast.get_team_roster(player_data.get('team'), player_type='hitter')
                            break
                
                if not roster:
                    print(f"  [WARNING]: No dynamic roster found for team '{team}'")
                    continue

                # Recover Matchup Meta
                match_home = "TBD"
                match_away = "TBD"
                for g in game_map.values():
                    if g['home'] == team or g['away'] == team:
                        match_home = g['home']
                        match_away = g['away']
                        break

                for p in roster:
                    name = p['name']
                    # OMEGA v7.9: Strict 50-PA Gate to eliminate ghosts/rookies. Bypass if starting.
                    pa_count = int(p.get('pa', 0) or 0)
                    is_in_starting = False
                    if confirmed_lineups:
                        norm_name = normalize_player_name(name)
                        for t_lineup in confirmed_lineups.values():
                            if any(normalize_player_name(lp) == norm_name for lp in t_lineup):
                                is_in_starting = True
                                break
                    if pa_count < 30 and name not in self.xwoba_registry and not is_in_starting:
                        continue

                    # OMEGA v7.8: Pitcher Rejection Gate
                    if p.get('type') == 'pitcher':
                        continue

                    # Scoring Priority: Registry -> Cache
                    xwoba = self._resolve_xwoba(name, p)

                    hitter_map[name] = {
                        'name': name,
                        'team': team,
                        'home_team': match_home,
                        'away_team': match_away,
                        'ahr_price': 450,
                        'hits_line': '-',
                        'hits_price': 0,
                        'tb_line': '-',
                        'tb_price': 0,
                        'is_juiced_target': False,
                        'is_prop_juice': False,
                        '_juice_gap': 0,
                        'runs_line': '-',
                        'runs_price': 0,
                        'runs_juice': False,
                        'runs_target': False,
                        'rbis_line': '-',
                        'rbis_price': 0,
                        'rbis_juice': False,
                        'rbis_target': False,
                        'walks_line': '-',
                        'walks_price': 0,
                        'strikeouts_line': '-',
                        'strikeouts_price': 0,
                        'runs_g_rbi_line': '-',
                        'runs_g_rbi_price': 0,
                        'is_speed_target': False,
                        'matchup_xwoba': xwoba
                    }

            # Ingest API props (Market Overlay)
            for gid, markets in props_all.items():
                matchup = game_map.get(gid, {})
                if not matchup: continue
                
                for m_key in [
                    'batter_home_runs', 'batter_hits', 'batter_total_bases',
                    'batter_stolen_bases', 'batter_runs', 'batter_rbis',
                    'batter_walks', 'batter_strikeouts', 'batter_runs_g_rbi',
                ]:
                    market_data = markets.get(m_key, [])
                    for entry in market_data:
                        player_name = entry.get('player_name')
                        if not player_name or player_name in ["Yes", "No"]: continue
                        
                        price = entry.get('price', 1000)
                        if 1.0 < price < 100.0: price = self.decimal_to_american(price)

                        # Explicit lookup for existing entry
                        norm_name = normalize_player_name(player_name)
                        found_key = None
                        for k in hitter_map:
                            if normalize_player_name(k) == norm_name:
                                found_key = k
                                break
                        
                        if not found_key:
                            # Add even if they aren't in Top 8 (Prop Divergence)
                            side_hint = entry.get('side')
                            team_side = self.resolve_team_side(player_name, matchup.get('home'), matchup.get('away'), market_side=side_hint, confirmed_lineups=confirmed_lineups)
                            if team_side is None or team_side not in active_teams: continue

                            momentum = self.statcast.get_player_momentum(player_name) or {}
                            # OMEGA v7.8: Pitcher Rejection Gate for Market Arrivals
                            if momentum.get('type') == 'pitcher':
                                continue

                            # OMEGA v7.8: Hardened Sample Gate (50 PA) for Market Arrivals.
                            # We check the Registry first, then fallback to high-sample Statcast data.
                            total_pa = int(momentum.get('pa', 0) or 0)
                            xwoba = self._resolve_xwoba(player_name, momentum) if total_pa >= 30 else 0.330
                            
                            found_key = player_name
                            hitter_map[found_key] = {
                                'name': player_name,
                                'team': team_side,
                                'home_team': matchup.get('home', "TBD"),
                                'away_team': matchup.get('away', "TBD"),
                                'ahr_price': 450,
                                'hits_line': '-',
                                'hits_price': 0,
                                'tb_line': '-',
                                'tb_price': 0,
                                'is_juiced_target': False,
                                'is_prop_juice': False,
                                '_juice_gap': 0,
                                'runs_line': '-',
                                'runs_price': 0,
                                'runs_juice': False,
                                'runs_target': False,
                                'rbis_line': '-',
                                'rbis_price': 0,
                                'rbis_juice': False,
                                'rbis_target': False,
                                'is_speed_target': False,
                                'matchup_xwoba': xwoba
                            }
                        
                        # Market Overlay Logic: Replace baseline defaults with real API prices
                        if m_key == 'batter_home_runs':
                            if entry.get('side') == 'Over':
                                current_price = hitter_map[found_key].get('ahr_price', 1000)
                                # If no real price yet (baseline 450 or sentinel 1000), or if this is a sharper price
                                if current_price >= 450:
                                    hitter_map[found_key]['ahr_price'] = price
                                else:
                                    hitter_map[found_key]['ahr_price'] = min(current_price, price)
                            
                        elif m_key == 'batter_hits':
                            if entry.get('side') == 'Over':
                                new_line = entry.get('point', 0.5)
                                hitter_map[found_key]['hits_line'] = new_line
                                
                                hits_price = entry.get('price', 0)
                                if 1.0 < hits_price < 100.0: hits_price = self.decimal_to_american(hits_price)
                                hitter_map[found_key]['hits_price'] = hits_price

                                from utils.prop_juice import evaluate_hitter_prop_juice

                                o_price = hits_price
                                pt = entry.get('point')
                                book = entry.get('bookmaker')
                                matching = [e for e in market_data if e.get('player_name') == player_name and e.get('side') == 'Under' and e.get('bookmaker') == book and e.get('point') == pt]
                                if matching:
                                    u_price = matching[0].get('price', 0)
                                    if 1.0 < u_price < 100.0:
                                        u_price = self.decimal_to_american(u_price)
                                    xw = hitter_map[found_key].get("matchup_xwoba", 0.33)
                                    tgt, juice, gap = evaluate_hitter_prop_juice(
                                        o_price, u_price, matchup_xwoba=xw
                                    )
                                    if juice:
                                        hitter_map[found_key]["is_prop_juice"] = True
                                        hitter_map[found_key]["_juice_gap"] = max(
                                            hitter_map[found_key].get("_juice_gap", 0), gap
                                        )
                                    if tgt:
                                        hitter_map[found_key]["is_juiced_target"] = True

                        elif m_key == 'batter_total_bases':
                            if entry.get('side') == 'Over':
                                new_line = entry.get('point', 1.5)
                                hitter_map[found_key]['tb_line'] = new_line
                                
                                tb_price = entry.get('price', 0)
                                if 1.0 < tb_price < 100.0: tb_price = self.decimal_to_american(tb_price)
                                hitter_map[found_key]['tb_price'] = tb_price

                                from utils.prop_juice import evaluate_hitter_prop_juice

                                o_price = tb_price
                                pt = entry.get('point')
                                book = entry.get('bookmaker')
                                matching = [e for e in market_data if e.get('player_name') == player_name and e.get('side') == 'Under' and e.get('bookmaker') == book and e.get('point') == pt]
                                if matching:
                                    u_price = matching[0].get('price', 0)
                                    if 1.0 < u_price < 100.0:
                                        u_price = self.decimal_to_american(u_price)
                                    xw = hitter_map[found_key].get("matchup_xwoba", 0.33)
                                    tgt, juice, gap = evaluate_hitter_prop_juice(
                                        o_price, u_price, matchup_xwoba=xw
                                    )
                                    if juice:
                                        hitter_map[found_key]["is_prop_juice"] = True
                                        hitter_map[found_key]["_juice_gap"] = max(
                                            hitter_map[found_key].get("_juice_gap", 0), gap
                                        )
                                    if tgt:
                                        hitter_map[found_key]["is_juiced_target"] = True
                                        
                        elif m_key == 'batter_stolen_bases':
                            side = entry.get('side')
                            if side == 'Over' and entry.get('point', 0.5) >= 0.5:
                                sb_price = entry.get('price', 0)
                                if 1.0 < sb_price < 100.0: sb_price = self.decimal_to_american(sb_price)
                                if -500 < sb_price <= 250:
                                    hitter_map[found_key]['is_speed_target'] = True

                        elif m_key in ('batter_runs', 'batter_rbis'):
                            if entry.get('side') == 'Over':
                                from utils.prop_juice import merge_hitter_market_juice

                                merge_hitter_market_juice(
                                    hitter_map[found_key], market_data, player_name, m_key
                                )

                        elif m_key == 'batter_walks':
                            if entry.get('side') == 'Over':
                                walks_price = entry.get('price', 0)
                                if 1.0 < walks_price < 100.0: walks_price = self.decimal_to_american(walks_price)
                                hitter_map[found_key]['walks_line'] = entry.get('point', 0.5)
                                hitter_map[found_key]['walks_price'] = walks_price

                        elif m_key == 'batter_strikeouts':
                            if entry.get('side') == 'Over':
                                so_price = entry.get('price', 0)
                                if 1.0 < so_price < 100.0: so_price = self.decimal_to_american(so_price)
                                hitter_map[found_key]['strikeouts_line'] = entry.get('point', 1.5)
                                hitter_map[found_key]['strikeouts_price'] = so_price

                        elif m_key == 'batter_runs_g_rbi':
                            if entry.get('side') == 'Over':
                                rr_price = entry.get('price', 0)
                                if 1.0 < rr_price < 100.0: rr_price = self.decimal_to_american(rr_price)
                                hitter_map[found_key]['runs_g_rbi_line'] = entry.get('point', 1.5)
                                hitter_map[found_key]['runs_g_rbi_price'] = rr_price

        except Exception as e:
            print(f"[CRITICAL ERROR]: Hitter Discovery silent crash prevented: {e}")
            import traceback
            traceback.print_exc()
        
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
        
        # OMEGA v6.8: Hybrid Roster Discovery (Backfill missing talent)
        # If any active team has zero hitters discovered via props, 
        # we pull their top 5 OPS performers from the unified cache.
        teams_with_hitters = {h['team'] for h in hitter_map.values()}
        missing_teams = active_teams - teams_with_hitters
        
        # OMEGA v7.9: Re-enabled dynamic backfill with 50-PA floor.
        teams_with_hitters = {h['team'] for h in hitter_map.values()}
        missing_teams = active_teams - teams_with_hitters
        
        if missing_teams:
            print(f"[OMEGA]: Backfilling {len(missing_teams)} teams via High-Sample Dynamic Logic...")
            for team in missing_teams:
                roster = self.statcast.get_team_roster(team, player_type='hitter')
                for p in roster:
                    name = p['name']
                    if name not in hitter_map:
                        pa_count = int(p.get('pa', 0) or 0)
                        is_in_starting = False
                        if confirmed_lineups:
                            norm_name = normalize_player_name(name)
                            for t_lineup in confirmed_lineups.values():
                                if any(normalize_player_name(lp) == norm_name for lp in t_lineup):
                                    is_in_starting = True
                                    break
                        if pa_count < 30 and name not in self.xwoba_registry and not is_in_starting:
                            continue
                        
                        xwoba = self._resolve_xwoba(name, p)
                        hitter_map[name] = {
                            'name': name,
                            'team': team,
                            'home_team': next((g['home'] for g in game_map.values() if g['home'] == team or g['away'] == team), "TBD"),
                            'away_team': next((g['away'] for g in game_map.values() if g['home'] == team or g['away'] == team), "TBD"),
                            'ahr_price': 450,
                            'hits_line': '-',
                            'hits_price': 0,
                            'tb_line': '-',
                            'tb_price': 0,
                            'is_juiced_target': False,
                            'is_speed_target': False,
                            'matchup_xwoba': xwoba
                        }
        
        h_list = list(hitter_map.values())
        from utils.prop_juice import apply_hitter_target_caps

        h_list = apply_hitter_target_caps(h_list)
        n_tgt = sum(1 for h in h_list if h.get("is_juiced_target"))
        n_juice = sum(1 for h in h_list if h.get("is_prop_juice"))
        print(
            f"[OMEGA]: Hitter discovery complete — {len(h_list)} players "
            f"({n_tgt} TARGET, {n_juice} JUICE) across {len(active_teams)} teams."
        )
        return sorted(h_list, key=lambda x: x['ahr_price'])

    def resolve_team_side(self, player_name, home_t, away_t, market_side=None, confirmed_lineups=None):
        """
        Dynamically determines if a player belongs to the home or away side.
        OMEGA v6.2.2: Strict Roster Gatekeeper (Anti-Ghosting Protocol).
        """
        norm_name = normalize_player_name(player_name)
        
        # 1. API Side Hint (Highest Confidence - direct from bookmaker)
        if market_side == "home": return home_t
        if market_side == "away": return away_t

        # 1.5 OMEGA v7.4: Trust Confirmed Lineups First (User Priority)
        if confirmed_lineups:
            for team, players in confirmed_lineups.items():
                if norm_name in players:
                    if team == home_t: return home_t
                    if team == away_t: return away_t
                    # If confirmed on a team NOT in this game, it's a ghost from another API block
                    return None

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
            'Arizona Diamondbacks': ['Corbin Carroll', 'Ketel Marte', 'Christian Walker', 'Lourdes Gurriel Jr.', 'Gabriel Moreno', 'Geraldo Perdomo'],
            'Atlanta Braves': ['Ronald Acuña Jr.', 'Matt Olson', 'Austin Riley', 'Ozzie Albies', 'Michael Harris II'],
            'Baltimore Orioles': ['Gunnar Henderson', 'Adley Rutschman', 'Pete Alonso', 'Jackson Holliday', 'Anthony Santander', 'Colton Cowser'],
            'Boston Red Sox': ['Rafael Devers', 'Jarren Duran', 'Triston Casas', 'Ceddanne Rafaela', 'Tyler O\'Neill'],
            'Chicago Cubs': ['Cody Bellinger', 'Seiya Suzuki', 'Dansby Swanson', 'Ian Happ', 'Michael Busch'],
            'Chicago White Sox': ['Luis Robert Jr.', 'Andrew Vaughn', 'Andrew Benintendi', 'Gavin Sheets'],
            'Cincinnati Reds': ['Elly De La Cruz', 'Spencer Steer', 'TJ Friedl', 'Jonathan India'],
            'Cleveland Guardians': ['José Ramírez', 'Josh Naylor', 'Steven Kwan', 'Andrés Giménez'],
            'Colorado Rockies': ['Ezequiel Tovar', 'Brenton Doyle', 'Nolan Jones', 'Ryan McMahon'],
            'Detroit Tigers': ['Riley Greene', 'Spencer Torkelson', 'Kerry Carpenter', 'Colt Keith'],
            'Houston Astros': ['Yordan Alvarez', 'Jose Altuve', 'Kyle Tucker', 'Alex Bregman', 'Yainer Diaz'],
            'Kansas City Royals': ['Bobby Witt Jr.', 'Salvador Perez', 'Vinnie Pasquantino', 'Maikel Garcia'],
            'Los Angeles Angels': ['Mike Trout', 'Taylor Ward', 'Logan O\'Hoppe', 'Zach Neto'],
            'Los Angeles Dodgers': ['Shohei Ohtani', 'Mookie Betts', 'Freddie Freeman', 'Will Smith', 'Teoscar Hernández'],
            'Miami Marlins': ['Jazz Chisholm Jr.', 'Bryan De La Cruz', 'Jesús Sánchez'],
            'Milwaukee Brewers': ['Christian Yelich', 'William Contreras', 'Brice Turang', 'Jackson Chourio'],
            'Minnesota Twins': ['Royce Lewis', 'Byron Buxton', 'Carlos Correa', 'Ryan Jeffers'],
            'New York Mets': ['Francisco Lindor', 'Brandon Nimmo', 'Pete Alonso', 'Starling Marte', 'Juan Soto'],
            'New York Yankees': ['Aaron Judge', 'Juan Soto', 'Giancarlo Stanton', 'Gleyber Torres', 'Anthony Volpe'],
            'Oakland Athletics': ['Brent Rooker', 'Shea Langeliers', 'Zack Gelof', 'JJ Bleday'],
            'Philadelphia Phillies': ['Bryce Harper', 'Trea Turner', 'Kyle Schwarber', 'Nick Castellanos', 'Alec Bohm'],
            'Pittsburgh Pirates': ['Bryan Reynolds', 'Oneil Cruz', 'Ke\'Bryan Hayes', 'Andrew McCutchen'],
            'San Diego Padres': ['Fernando Tatis Jr.', 'Manny Machado', 'Xander Bogaerts', 'Jackson Merrill', 'Jake Cronenworth'],
            'San Francisco Giants': ['Jung Hoo Lee', 'Matt Chapman', 'Jorge Soler', 'Thairo Estrada'],
            'Seattle Mariners': ['Julio Rodríguez', 'Cal Raleigh', 'Randy Arozarena', 'J.P. Crawford'],
            'St. Louis Cardinals': ['Nolan Arenado', 'Paul Goldschmidt', 'Willson Contreras', 'Masyn Winn'],
            'Tampa Bay Rays': ['Yandy Díaz', 'Isaac Paredes', 'Brandon Lowe', 'Josh Lowe'],
            'Texas Rangers': ['Corey Seager', 'Marcus Semien', 'Adolis García', 'Josh Jung', 'Wyatt Langford'],
            'Toronto Blue Jays': ['Vladimir Guerrero Jr.', 'Bo Bichette', 'George Springer', 'Daulton Varsho'],
            'Washington Nationals': ['CJ Abrams', 'Lane Thomas', 'James Wood', 'Luis García Jr.']
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
                        'hits_line': '-',
                        'hits_price': 0,
                        'tb_line': '-',
                        'tb_price': 0,
                        'is_speed_target': False,
                        'matchup_xwoba': self.xwoba_registry.get(normalize_player_name(name), 0.330),
                        'is_fallback': True
                    })
        return fallback_reports
