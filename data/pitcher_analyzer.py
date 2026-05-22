import json
import os
import sys

# Standalone execution support
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import statistics
from config import config
from engine.sharps_weighting import SharpsWeighting
from utils.normalization import normalize_player_name
from utils.market_utils import get_market_prices, calculate_ml_move
from utils.pitcher_trap import resolve_pitcher_trap

class PitcherAnalyzer:
    def __init__(self):
        self.config = config
        self.analyzer = SharpsWeighting()
        self.team_map = {
            'Minnesota Twins': 'Twins', 'Colorado Rockies': 'Rockies', 'Washington Nationals': 'Nationals',
            'St. Louis Cardinals': 'Cardinals', 'New York Yankees': 'Yankees', 'Athletics': 'Athletics',
            'Texas Rangers': 'Rangers', 'Seattle Mariners': 'Mariners', 'Houston Astros': 'Astros',
            'Los Angeles Angels': 'Angels', 'Atlanta Braves': 'Braves', 'San Francisco Giants': 'Giants',
            'Philadelphia Phillies': 'Phillies', 'Pittsburgh Pirates': 'Pirates', 'San Diego Padres': 'Padres',
            'Cleveland Guardians': 'Guardians', 'Kansas City Royals': 'Royals', 'Boston Red Sox': 'Red Sox',
            'Milwaukee Brewers': 'Brewers', 'Chicago White Sox': 'White Sox', 'Baltimore Orioles': 'Orioles',
            'New York Mets': 'Mets', 'Arizona Diamondbacks': 'Diamondbacks', 'Tampa Bay Rays': 'Rays',
            'Chicago Cubs': 'Cubs', 'Reds': 'Reds', 'Marlins': 'Marlins', 'Tigers': 'Tigers', 'Blue Jays': 'Blue Jays'
        }
        self.split_map = {
            'MIN': 'Twins', 'COL': 'Rockies', 'WSH': 'Nationals', 'STL': 'Cardinals',
            'NYY': 'Yankees', 'ATH': 'Athletics', 'TEX': 'Rangers', 'SEA': 'Mariners',
            'HOU': 'Astros', 'LAA': 'Angels', 'ATL': 'Braves', 'SF': 'Giants',
            'PHI': 'Phillies', 'PIT': 'Pirates', 'SD': 'Padres', 'CLE': 'Guardians',
            'KC': 'Royals', 'BOS': 'Red Sox', 'MIL': 'Brewers', 'CWS': 'White Sox',
            'BAL': 'Orioles', 'NYM': 'Mets', 'ARI': 'Diamondbacks', 'TB': 'Rays',
            'CHC': 'Cubs', 'CIN': 'Reds', 'MIA': 'Marlins', 'DET': 'Tigers', 'TOR': 'Blue Jays'
        }
        self.normalized_map = {
            'Chicago White Sox': 'White Sox', 'Baltimore Orioles': 'Orioles',
            'Texas Rangers': 'Rangers', 'Seattle Mariners': 'Mariners',
            'Toronto Blue Jays': 'Blue Jays', 'Los Angeles Dodgers': 'Dodgers',
            'Colorado Rockies': 'Rockies', 'Houston Astros': 'Astros',
            'San Francisco Giants': 'Giants', 'Philadelphia Phillies': 'Phillies',
            'Washington Nationals': 'Nationals', 'St. Louis Cardinals': 'Cardinals',
            'Los Angeles Angels': 'Angels', 'Atlanta Braves': 'Braves',
            'Arizona Diamondbacks': 'Diamondbacks', 'New York Mets': 'Mets',
            'Cleveland Guardians': 'Guardians', 'Boston Red Sox': 'Red Sox',
            'Tampa Bay Rays': 'Rays', 'Milwaukee Brewers': 'Brewers',
            'Cincinnati Reds': 'Reds', 'Miami Marlins': 'Marlins',
            'Detroit Tigers': 'Tigers', 'New York Yankees': 'Yankees',
            'Minnesota Twins': 'Twins', 'Oakland Athletics': 'Athletics',
            'Chicago Cubs': 'Cubs', 'Pittsburgh Pirates': 'Pirates',
            'San Diego Padres': 'Padres', 'Kansas City Royals': 'Royals'
        }
        # OMEGA v6.8: Dynamic Opponent Discovery (Alpha Scaling)
        self.opponent_k_boosts = self.calculate_dynamic_k_rates()
        # OMEGA v3.2.3.2: Starter Matrix Restored as LAST RESORT.
        # OMEGA v5.2: Deleted Hallucination Matrix. Return TBD if API falls back.

    def load_external_worksheet_props(self, ks_path, outs_path):
        import csv
        external_props = {}
        def _load_market(path, market_key, prop_key, default_val):
            if not os.path.exists(path): return
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    header = f.readline()
                    f.seek(0)
                    delimiter = '\t' if '\t' in header else ','
                    reader = csv.DictReader(f, delimiter=delimiter)
                    for row in reader:
                        if row.get('market') == market_key:
                            p_name = normalize_player_name(row.get('description', ''))
                            try:
                                point = float(row.get('point', default_val))
                                if p_name not in external_props: external_props[p_name] = {}
                                external_props[p_name][prop_key] = point
                            except Exception:
                                continue
            except Exception as e:
                print(f"[ERROR]: Worksheet prop load failure: {e}")
        _load_market(ks_path, 'pitcher_strikeouts', 'ks', 5.5)
        _load_market(outs_path, 'pitcher_outs', 'outs', 15.5)
        return external_props

    def analyze_slate(self, snapshot_path, opening_path, splits_data=None, props_data=None, rosters=None, weather_fetcher=None, umpire_fetcher=None, confirmed_list=[], movement_data=None, previous_results=None):
        if props_data is None: props_data = {}
        if rosters is None: rosters = {}
        if splits_data is None: splits_data = {}
        if movement_data is None: movement_data = []
        
        # OFFICIATING / WEATHER SENTIMENT INGESTION
        ump_assignments = {} if not umpire_fetcher else umpire_fetcher.fetch_daily_assignments()
        
        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)
            
        if os.path.exists(opening_path):
            with open(opening_path, "r", encoding="utf-8") as f:
                opening = json.load(f)
        else:
            opening = []
            print(f"  - [WARNING]: No opening lines file at {opening_path}; using live-line fallback.")
        self.opening_lookup = {o.get("game_id"): o for o in opening if o.get("game_id")}
            
        ext_props = self.load_external_worksheet_props(
            os.path.join(self.config.DATA_DIR, "manual_props.csv"),
            os.path.join(self.config.DATA_DIR, "manual_props.csv")
        )
            
        # OMEGA v5.4: Load Master Probables (The Verified Truth)
        probables_path = os.path.join(self.config.DATA_DIR, "probable_pitchers.json")
        probables = {}
        if os.path.exists(probables_path):
            with open(probables_path, 'r') as f:
                probables = json.load(f)

        # OMEGA v10.2: Load Pitcher Recent Form Cache
        form_cache_path = os.path.join(self.config.DATA_DIR, "pitcher_form_cache.json")
        form_cache = {}
        if os.path.exists(form_cache_path):
            try:
                with open(form_cache_path, 'r') as f:
                    form_cache = json.load(f)
            except Exception:
                pass

        pitcher_reports = []
        
        allowed_teams = self.config.get_slate_filter()
        for game in snapshot.get('odds', []):
            if allowed_teams and game['home_team'] not in allowed_teams and game['away_team'] not in allowed_teams:
                continue
            gid = game['id']
            open_data = self.opening_lookup.get(gid)
            
            home = game['home_team']
            away = game['away_team']

            if not open_data:
                open_data = next(
                    (o for o in opening if home in [o.get('team_home'), o.get('team_away')]),
                    None,
                )

            if not open_data:
                away_ml, _ = get_market_prices(game, away)
                home_ml, total = get_market_prices(game, home)
                open_data = {
                    'game_id': gid,
                    'team_home': home,
                    'team_away': away,
                    'home_opening_ml': home_ml,
                    'away_opening_ml': away_ml,
                    'opening_total': total or 8.5,
                }
                print(f"  - [OPEN-FALLBACK]: No stored opens for {away} @ {home}; using current lines.")
            
            # Check if game has commenced to prevent live-betting/in-progress odds shifts
            game_started = False
            commence_str = game.get('commence_time')
            if commence_str:
                try:
                    from datetime import datetime
                    commence_dt = datetime.strptime(commence_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                    if datetime.utcnow() >= commence_dt:
                        game_started = True
                except Exception:
                    pass
            
            for side in ['home', 'away']:
                team_name = game[f'{side}_team']
                vi_name = self.team_map.get(team_name)
                pitcher_name = probables.get(team_name, rosters.get(team_name, "TBD"))
                
                # Market Discovery
                key_prefix = 'home' if side == 'home' else 'away'
                open_ml = open_data.get(f'{key_prefix}_opening_ml', -110)
                open_total = open_data.get('opening_total', 8.5)
                curr_ml, curr_total = get_market_prices(game, team_name)
                
                # Shielding
                open_ml = float(open_ml or -110)
                curr_ml = float(curr_ml or open_ml)
                open_total = float(open_total or 8.5)
                curr_total = float(curr_total or open_total)
                
                # Splits / Divergence Ingestion
                from data.consensus_fetcher import ConsensusFetcher
                fetcher = ConsensusFetcher()
                split = fetcher.get_team_split(team_name, splits_data)
                pub_bets = float(split.get('ticket', 50)) if split else 50.0
                money_handle = float(split.get('money', 50)) if split else 50.0
                money_gap = money_handle - pub_bets
                
                if not pitcher_name or pitcher_name == "TBD":
                    pitcher_name = self.discover_starter_from_props(props_data, gid, team_name, opponent=(away if side == 'home' else home))
                
                # OMEGA v9.8: Try to preserve exact pre-game metrics from disk (latest_results.json)
                prev_pitcher_data = None
                if previous_results and pitcher_name:
                    p_norm = normalize_player_name(pitcher_name)
                    for k, v in previous_results.items():
                        if normalize_player_name(k) == p_norm:
                            prev_pitcher_data = v
                            break

                has_prev = prev_pitcher_data is not None

                k_line = None 
                outs_line = None
                k_odds = None
                outs_odds = None
                is_juiced_target = False
                is_trap = False
                trap_type = None
                is_death_sentence = False
                trap_prop_note = None
                props_feed_status = "ok"
                divergence = 0

                # Recover props and movement only if game has not started or we have no pre-game snapshot
                if game_started and has_prev:
                    ml_move = float(prev_pitcher_data.get('ml_move', 0.0))
                    tt_move = float(prev_pitcher_data.get('tt_move', 0.0))
                    divergence = int(prev_pitcher_data.get('divergence', 0))
                    is_sharp = bool(prev_pitcher_data.get('is_sharp', False))
                    is_shark = bool(prev_pitcher_data.get('is_shark', False))
                    is_whale = bool(prev_pitcher_data.get('is_whale', False))
                    k_line = prev_pitcher_data.get('k_line')
                    outs_line = prev_pitcher_data.get('outs_line')
                    is_juiced_target = bool(prev_pitcher_data.get('is_juiced_target', False))
                    is_trap = bool(prev_pitcher_data.get('is_trap', False))
                    trap_type = prev_pitcher_data.get('trap_type')
                    is_death_sentence = bool(prev_pitcher_data.get('is_death_sentence', False))
                    curr_ml = open_ml + ml_move if (open_ml is not None and ml_move is not None) else -110
                    curr_total = open_total + tt_move if (open_total is not None and tt_move is not None) else 8.5
                else:
                    ml_move = calculate_ml_move(open_ml, curr_ml)
                    tt_move = curr_total - open_total
                    divergence = fetcher.get_divergence(team_name, splits_data)
                    
                    gid_props = props_data.get(gid, {})
                    
                    # Strikeouts recovery
                    if 'pitcher_strikeouts' in gid_props:
                        p_k = [o for o in gid_props['pitcher_strikeouts'] if normalize_player_name(o.get('player_name', '')) == normalize_player_name(pitcher_name)]
                        if p_k:
                            points = [o.get('point', 0) for o in p_k if o.get('point')]
                            if points: 
                                k_line = statistics.median(points)
                                o_odds = next((o.get('price') for o in p_k if o.get('point') == k_line and o.get('side') == 'Over'), None)
                                if o_odds: k_odds = o_odds
                            
                            for o in p_k:
                                if o.get('side') == 'Over':
                                    o_price = o.get('price', 0)
                                    book = o.get('bookmaker')
                                    pt = o.get('point')
                                    matching = [u for u in p_k if u.get('side') == 'Under' and u.get('bookmaker') == book and u.get('point') == pt]
                                    if matching:
                                        u_price = matching[0].get('price', 0)
                                        if o_price < u_price: 
                                            is_juiced_target = True
                                            break
                    
                    # Outs recovery
                    if 'pitcher_outs' in gid_props:
                        p_outs = [o for o in gid_props['pitcher_outs'] if normalize_player_name(o.get('player_name', '')) == normalize_player_name(pitcher_name)]
                        if p_outs:
                            points = [o.get('point', 0) for o in p_outs if o.get('point')]
                            if points: 
                                outs_line = statistics.median(points)
                                o_odds = next((o.get('price') for o in p_outs if o.get('point') == outs_line and o.get('side') == 'Over'), None)
                                if o_odds: outs_odds = o_odds
                    
                    norm_pitcher = normalize_player_name(pitcher_name)
                    if k_line is None and ext_props.get(norm_pitcher):
                        k_line = ext_props[norm_pitcher].get('ks')
                    if outs_line is None and ext_props.get(norm_pitcher):
                        outs_line = ext_props[norm_pitcher].get('outs')
                    
                    if k_line is None: k_line = 4.5
                    if outs_line is None: outs_line = 14.5
                    
                    p_move = next((m for m in movement_data if m.get('player') == pitcher_name), None)
                    k_move = p_move.get('k_move', 0) if p_move else 0
                    trap_res = resolve_pitcher_trap(
                        prev_pitcher=prev_pitcher_data,
                        ml_move=ml_move,
                        k_move=k_move,
                        k_line=k_line,
                        k_odds=k_odds,
                        outs_line=outs_line,
                        outs_odds=outs_odds,
                    )
                    is_trap = trap_res["is_trap"]
                    trap_type = trap_res["trap_type"]
                    is_death_sentence = trap_res["is_death_sentence"]
                    trap_prop_note = trap_res.get("trap_prop_note")
                    props_feed_status = trap_res.get("props_feed_status", "ok")
                    sticky_trap = trap_res.get("sticky_trap", is_trap)
                    if k_odds is None and prev_pitcher_data and prev_pitcher_data.get("k_odds") is not None:
                        k_odds = prev_pitcher_data.get("k_odds")

                    is_shark = fetcher.detect_shark(team_name, splits_data, ml_move)
                    is_whale = (divergence >= 15)
                    is_sharp = fetcher.is_sharp_consensus(team_name, splits_data)

                physics = self.fetch_pitcher_physics(pitcher_name)
                venue_team = home 
                base_stadium_factor = self.config.PARK_FACTORS.get(venue_team, 1.00)
                ump_data = ump_assignments.get(venue_team, {"factor": 1.0, "name": "TBD"})
                ump_boost = (ump_data['factor'] - 1.0) * 100.0 
                
                weather_boost = 0
                weather_label = "TBD"
                if weather_fetcher:
                    w_res = weather_fetcher.get_alpha_modifier(venue_team)
                    weather_boost = w_res['boost']
                    weather_label = w_res['label']
                
                park_factor = (base_stadium_factor * 100.0) + ump_boost + weather_boost
                opponent = away if side == 'home' else home
                opponent_k_boost = self.opponent_k_boosts.get(opponent, 5.0) 
                is_low_ceiling = (k_line is not None and float(k_line) <= 4.5)

                # OMEGA v10.2: Pitcher Recent Form Assessment (Conservative)
                p_form = form_cache.get(normalize_player_name(pitcher_name))
                recent_k9 = None
                recent_era = None
                form_boost = 0.0
                form_status = None
                
                if p_form and p_form.get('recent_ip', 0) >= 8.0:
                    recent_k9 = p_form.get('recent_k9', 0)
                    recent_era = p_form.get('recent_era', 0)
                    # Get baseline from our statcast physics dict (cached during ingest)
                    s_k = physics.get('k', 0)
                    s_ip = physics.get('ip', 1.0)
                    season_k9 = (s_k / s_ip) * 9.0 if s_ip > 0 else 7.0
                    
                    if recent_k9 >= (season_k9 + 1.5) and recent_era < 3.50:
                        form_boost = 5.0
                        form_status = "SURGING"
                    elif recent_k9 <= (season_k9 - 1.5) and recent_era > 5.00:
                        form_boost = -5.0
                        form_status = "COLD"

                # Scoring (v7.8 Trap-Aware)
                alpha_results = self.analyzer.calculate_pitcher_score(
                    pitcher_name, ml_move, tt_move, money_gap, k_line,
                    siera=physics['siera'], csw=physics['csw'],
                    is_target=is_juiced_target,
                    park_factor=park_factor,
                    divergence=divergence,
                    is_shark=is_shark,
                    is_whale=is_whale,
                    opponent_k_boost=opponent_k_boost,
                    is_low_ceiling=is_low_ceiling,
                    projected_outs=float(outs_line),
                    is_trap=is_trap,
                    is_sharp=is_sharp,
                    curr_ml=curr_ml
                )

                if is_death_sentence:
                    alpha_results['final'] = round(alpha_results['final'] * 0.85, 1)
                    
                # Apply conservative form boost to final score
                alpha_results['final'] = round(alpha_results['final'] + form_boost, 1)
                
                pitcher_reports.append({
                    'pitcher': pitcher_name,
                    'team': team_name,
                    'opponent': opponent,
                    'event_id': gid,
                    'k_line': k_line,
                    'outs_line': outs_line,
                    'k_odds': k_odds,
                    'outs_odds': outs_odds,
                    'alpha_score': alpha_results,
                    'csw': physics['csw'],
                    'siera': physics['siera'],
                    'bm_score': physics['bm_score'],
                    'confidence': physics.get('confidence', 'low'),
                    'is_confirmed': team_name in confirmed_list,
                    'is_juiced_target': is_juiced_target,
                    'is_shark': is_shark,
                    'is_whale': is_whale,
                    'is_sharp': is_sharp,
                    'ml_move': ml_move,
                    'tt_move': tt_move,
                    'money_gap': money_gap,
                    'divergence': divergence,
                    'weather_label': weather_label,
                    'umpire_name': ump_data['name'],
                    'umpire_factor': ump_data.get('factor', 1.0),
                    'trap_type': trap_type if is_trap else None,
                    'trap_prop_note': trap_prop_note,
                    'props_feed_status': props_feed_status,
                    'sticky_trap': sticky_trap,
                    'form_status': form_status,
                    'recent_k9': recent_k9,
                    'recent_era': recent_era,
                    'is_home': side == 'home',
                    'side': side
                })
        
        return pitcher_reports

    def calculate_dynamic_k_rates(self):
        """
        [OMEGA v6.8]: Dynamic Team K-Rate Indexing.
        Aggregates player-level K/PA stats from the unified cache, applies a 70/30 
        Season/Rolling blend, and scales the alpha boost to a 15% cap for the league leader.
        """
        cache_path = os.path.join(self.config.DATA_DIR, "statcast_cache.json")
        if not os.path.exists(cache_path): 
            print("[WARNING]: No statcast cache found. Dynamic K-scaling disabled.")
            return {}
        
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
        except Exception as e:
            print(f"[ERROR]: Statcast cache parse failure: {e}")
            return {}
            
        team_stats = {}
        for name, data in cache.items():
            if data.get('type') == 'hitter':
                team = data.get('team')
                if not team or team == "UNK": continue
                
                if team not in team_stats:
                    team_stats[team] = {'k': 0, 'pa': 0}
                
                # 70/30 Season/Rolling Blend for momentum sensitivity
                k_val = (data.get('k', 0) * 0.7) + (data.get('rolling_k', 0) * 0.3)
                pa_val = (data.get('pa', 0) * 0.7) + (data.get('rolling_pa', 0) * 0.3)
                
                team_stats[team]['k'] += k_val
                team_stats[team]['pa'] += pa_val
        
        rates = {}
        for team, stats in team_stats.items():
            if stats['pa'] > 50: # Min sample gate per team
                rates[team] = stats['k'] / stats['pa']
        
        if not rates: return {}
        
        # Scaling Logic: Average-Centered Two-Pole Scaling
        # avg = 0%, max = +15%, min = -15%
        avg_rate = sum(rates.values()) / len(rates)
        max_rate = max(rates.values())
        min_rate = min(rates.values())
        
        boosts = {}
        for team, rate in rates.items():
            if rate >= avg_rate:
                # Target Scaling (+15% max boost for elite K-targets)
                denom = (max_rate - avg_rate)
                boosts[team] = round(15.0 * (rate - avg_rate) / (denom if denom > 0 else 1.0), 1)
            else:
                # Avoid Scaling (Dampened to -10.0% max penalty for elite contact hitters)
                denom = (avg_rate - min_rate)
                boosts[team] = round(-10.0 * (avg_rate - rate) / (denom if denom > 0 else 1.0), 1)
        
        # Log Top/Bottom for audit trace
        sorted_boosts = sorted(boosts.items(), key=lambda x: x[1], reverse=True)
        if sorted_boosts:
            print(f"[OMEGA]: Dynamic K-Boosts Recalibrated. Target: {sorted_boosts[0][0]} (+{sorted_boosts[0][1]}%) | Avoid: {sorted_boosts[-1][0]} ({sorted_boosts[-1][1]}%)")
            
        return boosts

    def find_starter_in_leaderboard(self, team_name):
        """OMEGA v5.2: Last Resort Ace Fallback Eradicated. Return TBD."""
        return "TBD"

    def discover_starter_from_props(self, props_data, game_id, team_name, opponent=None):
        """
        [OMEGA v6.2.2]: Process of Elimination Resolver.
        Extracts name from prop markets, matching against known hitter anchors, side metadata, 
        or resolving via exclusion of the opponent starter.
        """
        gid_props = props_data.get(game_id, {})
        potential_pitchers = set()
        
        # 1. Collect all pitcher names for this game
        for m_key in ['pitcher_strikeouts', 'pitcher_outs', 'pitcher_record_an_out']:
            if m_key in gid_props:
                for outcome in gid_props[m_key]:
                    pn = outcome.get('player_name')
                    if pn: potential_pitchers.add(pn)
        
        if not potential_pitchers: return "TBD"
        
        # 2. Check Side Metadata (Highest Confidence Prop Ingestion)
        for m_key in ['pitcher_strikeouts', 'pitcher_outs']:
            for outcome in gid_props.get(m_key, []):
                p_name = outcome.get('player_name')
                side = outcome.get('side', '').lower()
                # Direct Side Match
                if side:
                    if (side == 'home' and team_name == outcome.get('home_team')) or \
                       (side == 'away' and team_name == outcome.get('away_team')):
                        return p_name

        # 3. Resolve via Anchor Teams
        from data.hitter_prop_analyzer import HitterPropAnalyzer
        hitter_analyzer = HitterPropAnalyzer()
        anchors = hitter_analyzer.get_anchor_teams()
        
        resolved_ours = []
        resolved_theirs = []
        
        for p in potential_pitchers:
            p_norm = normalize_player_name(p)
            found_team = None
            for t, roster in anchors.items():
                if any(normalize_player_name(member) == p_norm for member in roster):
                    found_team = t
                    break
            
            if found_team == team_name:
                resolved_ours.append(p)
            elif found_team == opponent:
                resolved_theirs.append(p)
        
        if resolved_ours:
            return resolved_ours[0]

        # 4. Process of Elimination (Mutual Exclusion)
        # If we have two pitchers and one is identified as the opponent, the other is ours.
        if len(potential_pitchers) == 2 and resolved_theirs:
            ours = [p for p in potential_pitchers if p not in resolved_theirs]
            if ours: return ours[0]

        return "TBD"


    def _calculate_proxy_physics(self, era, k, ip, bb=0, hr=0, whip=1.20):
        """
        OMEGA v10.0: Enhanced Sabermetric Proxy Physics Calculator.
        Derives SIERA, CSW, and FIP estimates using K, BB, HR, WHIP, and ERA.
        
        Blends:
        - Sabermetric FIP (Fielding Independent Pitching) to isolate pitcher-controlled outcomes
        - WHIP to capture baserunner congestion stress and physical volatility
        - K/IP ratio and Season ERA
        
        Returns: (proxy_siera, proxy_csw, confidence)
        """
        era = float(era or 4.00)
        k = float(k or 0)
        ip = float(ip or 0)
        bb = float(bb or 0)
        hr = float(hr or 0)
        whip = float(whip or 1.20)
        
        if ip > 5.0:
            # 1. Sabermetric FIP (Fielding Independent Pitching)
            # FIP = (13*HR + 3*BB - 2*K) / IP + Constant (centered around 3.15 to regress to average)
            raw_fip = ((13.0 * hr) + (3.0 * bb) - (2.0 * k)) / ip + 3.15
            fip = max(2.00, min(6.00, raw_fip))
            
            # 2. Skill-Interactive ERA (SIERA) proxy blending FIP, WHIP, and ERA
            siera_est = (0.5 * fip) + (0.3 * era) + (0.2 * (whip * 3.0))
            proxy_siera = max(2.20, min(5.80, siera_est))
            
            # 3. CSW% estimate adjusted for control/congestion (WHIP)
            k_per_ip = k / ip
            proxy_csw = 0.25 + (k_per_ip - 0.85) * 0.1 - (whip - 1.20) * 0.05
            proxy_csw = max(0.15, min(0.38, proxy_csw))
            
            confidence = "high" if ip >= 20.0 else "med"
        else:
            # Insufficient sample — use league-average defaults
            proxy_siera = 4.10
            proxy_csw = 0.25
            confidence = "med"
        
        return proxy_siera, proxy_csw, confidence

    def fetch_pitcher_physics(self, pitcher_name):
        """
        OMEGA v7.2: Tiered Physics Engine.
        
        Tier 1: Master Matrix — manual overrides for pitchers where API data is misleading
                (e.g., returning from injury with 0 IP, or known elite arms with small 2026 samples)
        Tier 2: StatsAPI Cache — 100+ pitchers with real 2026 ERA/K/IP from MLB.com
        Tier 3: Live MLB API — on-demand fetch for anyone missing from cache
        Tier 4: FanGraphs CSV — legacy cache from any prior successful pybaseball run
        Tier 5: League-average defaults — absolute last resort
        """
        p_norm = normalize_player_name(pitcher_name)
        
        # OMEGA v7.2: Trimmed Master Matrix — OVERRIDE ONLY
        # Only keep pitchers where the API proxy would be inaccurate:
        # - Returning from injury (0 IP in 2026 but elite talent)
        # - Known elite arms with small early-season samples
        # These values should be reviewed periodically.
        master_matrix = {
            "Jacob deGrom": {"siera": 2.45, "csw": 0.36},      # Injury return, limited 2026 data
            "Paul Skenes": {"siera": 2.85, "csw": 0.33},       # Elite stuff, proxy undersells
            "Tarik Skubal": {"siera": 2.95, "csw": 0.32},      # Reigning Cy Young
            "Tyler Glasnow": {"siera": 2.90, "csw": 0.315},    # Elite stuff metrics
            "Cole Ragans": {"siera": 3.15, "csw": 0.312},      # Elite CSW the proxy misses
            "Chris Sale": {"siera": 3.15, "csw": 0.29},        # HOF-caliber, proxy unreliable early
            "Kodai Senga": {"siera": 3.15, "csw": 0.29},       # Injury return
            "Spencer Arrighetti": {"siera": 3.48, "csw": 0.29}, # 0 IP in cache
            "Garrett Crochet": {"siera": 3.30, "csw": 0.30},   # High K stuff, ERA inflated
            "Emmet Sheehan": {"siera": 3.65, "csw": 0.31},     # 0 IP in cache
            "Lance McCullers Jr.": {"siera": 3.45, "csw": 0.28}, # Injury return
            "Bubba Chandler": {"siera": 3.65, "csw": 0.29},    # 0 IP in cache
            "Casey Mize": {"siera": 4.10, "csw": 0.24},        # 0 IP in cache
            "German Marquez": {"siera": 4.25, "csw": 0.24},    # Injury return
            "Germán Márquez": {"siera": 4.25, "csw": 0.24},    # Accent variant
        }
        
        # --- TIER 1: Master Matrix (manual overrides) ---
        for name, stats in master_matrix.items():
            if normalize_player_name(name) == p_norm:
                siera = stats['siera']
                csw = stats['csw']
                bm_score = max(0, min(25, (csw / 0.30) * 25))
                return {"siera": siera, "csw": csw, "bm_score": bm_score, "confidence": "high"}
        
        # --- TIER 2: StatsAPI Cache (real 2026 ERA/K/IP from MLB.com) ---
        statcast_path = os.path.join(self.config.DATA_DIR, "statcast_cache.json")
        if os.path.exists(statcast_path):
            try:
                with open(statcast_path, 'r') as f:
                    cache = json.load(f)
                p_data = cache.get(p_norm)
                if p_data and p_data.get('type') == 'pitcher':
                    ip_26 = float(p_data.get('ip', 0.0))
                    era_26 = float(p_data.get('era', 4.00))
                    k_26 = float(p_data.get('k', 0))
                    bb_26 = float(p_data.get('bb', 0))
                    hr_26 = float(p_data.get('hr', 0))
                    whip_26 = float(p_data.get('whip', 1.20))
                    
                    # 2025 seasonal stats for stabilization
                    ip_25 = float(p_data.get('ip_25', 0.0))
                    era_25 = float(p_data.get('era_25', 4.00))
                    k_25 = float(p_data.get('k_25', 0))
                    bb_25 = float(p_data.get('bb_25', 0))
                    hr_25 = float(p_data.get('hr_25', 0))
                    whip_25 = float(p_data.get('whip_25', 1.20))
                    
                    # Stabilized Empirical Blend
                    if ip_26 < 30.0 and ip_25 > 5.0:
                        total_ip = ip_26 + ip_25
                        w_26 = ip_26 / total_ip
                        w_25 = ip_25 / total_ip
                        
                        blended_era = (era_26 * w_26) + (era_25 * w_25)
                        blended_k = k_26 + k_25
                        blended_bb = bb_26 + bb_25
                        blended_hr = hr_26 + hr_25
                        blended_whip = (whip_26 * w_26) + (whip_25 * w_25)
                        
                        siera, csw, confidence = self._calculate_proxy_physics(
                            blended_era, blended_k, total_ip, bb=blended_bb, hr=blended_hr, whip=blended_whip
                        )
                        confidence = "med" # blended sample is stabilized but multi-year
                    elif ip_26 > 0:
                        siera, csw, confidence = self._calculate_proxy_physics(
                            era_26, k_26, ip_26, bb=bb_26, hr=hr_26, whip=whip_26
                        )
                    else:
                        # Fallback if both 2026 and 2025 are missing from cache
                        siera, csw, confidence = 4.10, 0.25, "low"
                        
                    bm_score = max(0, min(25, (csw / 0.30) * 25))
                    return {"siera": siera, "csw": csw, "bm_score": bm_score, "confidence": confidence}
            except Exception:
                pass
        
        # --- TIER 3: Direct MLB StatsAPI Lookup (on-demand for missing pitchers) ---
        try:
            import requests
            resp = requests.get(
                "https://statsapi.mlb.com/api/v1/people/search",
                params={"names": pitcher_name, "sportId": 1},
                timeout=10
            )
            if resp.status_code == 200:
                people = resp.json().get('people', [])
                if people:
                    player_id = people[0]['id']
                    stats_resp = requests.get(
                        f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats",
                        params={"stats": "season", "season": 2026, "group": "pitching"},
                        timeout=10
                    )
                    if stats_resp.status_code == 200:
                        splits = stats_resp.json().get('stats', [{}])[0].get('splits', [])
                        if splits:
                            stat = splits[0].get('stat', {})
                            era = float(stat.get('era', '4.00'))
                            k = int(stat.get('strikeOuts', 0))
                            ip = float(stat.get('inningsPitched', '0.0'))
                            bb = int(stat.get('baseOnBalls', 0))
                            hr = int(stat.get('homeRuns', 0))
                            whip = float(stat.get('whip', '1.20'))
                            
                            siera, csw, confidence = self._calculate_proxy_physics(
                                era, k, ip, bb=bb, hr=hr, whip=whip
                            )
                            print(f"  - LIVE API: Fetched physics for {pitcher_name} (ERA: {era:.2f}, K: {k}, IP: {ip}, BB: {bb}, HR: {hr}, WHIP: {whip:.2f})")
                            
                            bm_score = max(0, min(25, (csw / 0.30) * 25))
                            return {"siera": siera, "csw": csw, "bm_score": bm_score, "confidence": confidence}
        except Exception:
            pass
        
        # --- TIER 4: FanGraphs CSV Cache (legacy) ---
        cache_file_2026 = os.path.join(self.config.DATA_DIR, "physics_leaderboard_2026.csv")
        cache_file_2025 = os.path.join(self.config.DATA_DIR, "physics_leaderboard_2025.csv")
        
        for cache_file in [cache_file_2026, cache_file_2025]:
            if os.path.exists(cache_file) and os.path.getsize(cache_file) > 100:
                try:
                    df = pd.read_csv(cache_file)
                    if 'Name' in df.columns:
                        mask = df['Name'].apply(lambda x: normalize_player_name(str(x))) == p_norm
                        match = df[mask]
                        if not match.empty:
                            siera = match.iloc[0].get('SIERA', 4.10)
                            csw = match.iloc[0].get('CSW%', 0.25)
                            if csw > 1: csw /= 100.0
                            ip = match.iloc[0].get('IP', 0)
                            confidence = "high" if ip >= 20.0 else ("med" if ip >= 10.0 else "low")
                            bm_score = max(0, min(25, (csw / 0.30) * 25))
                            return {"siera": siera, "csw": csw, "bm_score": bm_score, "confidence": confidence}
                except Exception:
                    pass
        
        # --- TIER 5: Absolute fallback ---
        print(f"  - FALLBACK: No physics data found for {pitcher_name}. Using league-average defaults.")
        bm_score = max(0, min(25, (0.25 / 0.30) * 25))
        return {"siera": 4.10, "csw": 0.25, "bm_score": bm_score, "confidence": "low"}


    def _ml_to_prob(self, ml):
        if ml == 0: return 0.5
        if ml < 0: return abs(ml) / (abs(ml) + 100)
        return 100 / (ml + 100)
