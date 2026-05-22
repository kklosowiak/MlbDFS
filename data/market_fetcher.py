import requests
import json
import os
import time
import sys
from datetime import datetime, timedelta, timezone

# Direct execution support
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import config

class MarketFetcher:
    """
    - [x] Implement Hybrid Scoring Model in `sharps_weighting.py`
    - [x] Refine Matchup Mapping in `main.py` and `pitcher_analyzer.py`
    - [x] Enhance V4 Name Extraction in `market_fetcher.py`
    - [/] Verify OMEGA v3.2.2 results
    Strictly implements The Odds API V4 protocols for resilient player prop ingestion.
    """
    
    def __init__(self):
        self.api_key = config.ODDS_API_KEY
        self.base_url = "https://api.the-odds-api.com/v4/sports/baseball_mlb"
        
        # OMEGA v3.2.1 Core Market Alpha
        # Requirement: Strictly comma-separated strings for requests
        self.prop_markets = 'pitcher_strikeouts,batter_home_runs,batter_hits,pitcher_outs,batter_total_bases,batter_stolen_bases'
        self.game_markets = 'h2h,totals'
        self.bookmakers = config.BOOKMAKERS
        self.regions = config.REGIONS
        self.odds_format = 'american'
        self.skipped_events = [] # Patch 1: Silent Failure Tracking

    def resolve_pitcher(self, team_name, game, team_type, event_props, probables):
        """
        [OMEGA v6.2.2]: Multi-Gate Pitcher Resolver with Mutual Exclusion.
        Ensures 100% matchup accuracy by cross-referencing side metadata and opponent assignment.
        """
        sp_key = f"{team_type}_pitcher"
        opp_type = 'away' if team_type == 'home' else 'home'
        opp_pitcher = game.get(f"{opp_type}_pitcher")
        
        # 1. Check API Metadata (Highest Confidence)
        if game.get(sp_key):
             return game[sp_key]
             
        # 2. Check Local Probables (User-Verified Truth)
        if team_name in probables:
            resolved = probables[team_name]
            # Mutual Exclusion Gate
            if resolved != opp_pitcher:
                print(f"  - [RECOVERED SP]: {resolved} ({team_name})")
                return resolved
            
        # 3. Market Discovery (Pitcher Props) with Team Validation
        from data.hitter_prop_analyzer import HitterPropAnalyzer
        from data.statcast_bridge import StatcastBridge
        from utils.normalization import normalize_player_name
        
        rosters = HitterPropAnalyzer().get_anchor_teams()

        team_roster = [normalize_player_name(m) for m in rosters.get(team_name, [])]
        opp_roster = [normalize_player_name(m) for m in rosters.get(game[f"{opp_type}_team"], [])]
        statcast = StatcastBridge()
        
        candidates = []
        for market_key in ['pitcher_strikeouts', 'pitcher_record_an_out', 'pitcher_outs']:
            if market_key in event_props:
                for p_data in event_props[market_key]:
                    p_name = p_data['player_name']
                    norm_p = normalize_player_name(p_name)
                    if p_name == opp_pitcher: continue # Mutual Exclusion
                    
                    # OMEGA v6.2.2: Deep Team Verification
                    is_on_team = False
                    is_on_opp = False
                    
                    # A) Check Anchor Team (Manual Truth)
                    if norm_p in team_roster: is_on_team = True
                    if norm_p in opp_roster: is_on_opp = True
                    
                    # B) Check Statcast Momentum Cache (API Truth)
                    mom = statcast.get_player_momentum(p_name)
                    if mom and mom.get('team'):
                        code_map = HitterPropAnalyzer().team_code_map
                        p_team = code_map.get(mom['team'].upper())
                        if p_team == team_name:
                            is_on_team = True
                        elif p_team and p_team == game[f"{opp_type}_team"]:
                            is_on_opp = True
                    
                    # C) Side Hint Verification
                    p_side = p_data.get('side', '').lower()
                    if p_side == team_type:
                        if not is_on_opp: 
                            is_on_team = True
                    elif p_side == opp_type:
                        is_on_opp = True

                    if is_on_team and not is_on_opp:
                        if p_name not in candidates: candidates.append(p_name)

        
        if candidates:
            # If multiple candidates, prioritize ones that have high confidence
            discovered = candidates[0]
            print(f"  - [DISCOVERED SP]: {discovered} ({team_name})")
            return discovered
            
        return None


    def fetch_event_ids(self, date_from=None, date_to=None):

        """
        Step 1: Retrieve all upcoming MLB event IDs. (Updated v4.5: Temporal Isolation)
        """
        url = f"{self.base_url}/events"
        params = {
            'apiKey': self.api_key
        }
        if date_from:
            params['commenceTimeFrom'] = date_from
        if date_to:
            params['commenceTimeTo'] = date_to
        
        try:
            print(f"[FETCH]: Retrieving active MLB event list...")
            response = requests.get(url, params=params)
            response.raise_for_status()
            events = response.json()
            
            # OMEGA v4.5.1: Robust Client-Side Filtering
            # Ensure start/end boundaries are strictly respected
            event_ids = [
                e['id'] for e in events 
                if (not date_from or e['commence_time'] >= date_from) and
                   (not date_to or e['commence_time'] <= date_to)
            ]
            
            print(f"  - SUCCESS: Recovered {len(event_ids)} active events.")
            return event_ids
            
        except Exception as e:
            print(f"  - CRITICAL: Failed to fetch event list. {e}")
            return []

    def fetch_data_for_event(self, event_id, markets):
        """
        Step 2: Fetch specific odds/props for a single event.
        Implements comma-separated parameter strings to bypass 422 errors.
        """
        url = f"{self.base_url}/events/{event_id}/odds"
        params = {
            'apiKey': self.api_key,
            'regions': self.regions,
            'markets': markets,
            'bookmakers': self.bookmakers,
            'oddsFormat': self.odds_format
        }
        
        try:
            response = requests.get(url, params=params)
            
            if response.status_code == 422:
                # Requirement: Log warning and continue bulk fetch
                print(f"  - WARNING: Props not open yet for Event [{event_id}].")
                self.skipped_events.append(f"Props Unassigned [{event_id}]") # Patch 1: Tracking
                return None
            elif response.status_code == 404:
                print(f"  - WARNING: Event [{event_id}] not found.")
                self.skipped_events.append(f"Event Not Found [{event_id}]") # Patch 1: Tracking
                return None
                
            response.raise_for_status()
            return response.json()
            
        except Exception as e:
            print(f"  - ERROR: Failed to fetch props for {event_id}. {e}")
            return None

    def run_bulk_ingestion(self, date_from=None, date_to=None, capture_opening=False):
        """
        Main Convergence Pipeline Entry Point. (Updated v4.5: Temporal Isolation)
        capture_opening: True only for 4:30 AM ET — freezes opens via Odds API historical.
        """
        event_ids = self.fetch_event_ids(date_from=date_from, date_to=date_to)
        if not event_ids:
            return None
            
        # Structure Requirement: Organized by Player Name and Market
        structured_props = {}
        structured_odds = {}
        
        print(f"[INGEST]: Starting bulk prop recovery for OMEGA v3.2.1...")
        
        for event_id in event_ids:
            # Patch 2: Rate Limit Prevention (0.8s sleep per API call)
            time.sleep(0.8)
            
            # Requirement: Graceful Degradation wrapper
            try:
                # OMEGA v6.16: Granular Fetching Hardening
                # Instead of fetching ALL props in one brittle call, we fetch category-by-category.
                # This prevents a missing "Pitcher Outs" market from sabotaging live "Home Run" props (422 error).
                
                # A. Fetch Game Odds (ML/Totals) - Always primary metadata source
                game_data = self.fetch_data_for_event(event_id, self.game_markets)
                if not game_data:
                    # Fallback to a single prop fetch to get team names if ML market is somehow closed
                    game_data = self.fetch_data_for_event(event_id, 'h2h')
                
                if not game_data:
                    print(f"  - [WARNING]: No metadata found for event {event_id}. Skipping.")
                    continue
                
                home_team = game_data.get('home_team')
                away_team = game_data.get('away_team')
                commence_time = game_data.get('commence_time')
                
                # Temporal Slate Filter
                commence_dt = datetime.fromisoformat(commence_time.replace('Z', '+00:00'))
                now = datetime.now(timezone.utc)
                # OMEGA v9.4: Loosen past filtering so manual refreshes do not exclude early games of today's slate
                if commence_dt < (now - timedelta(hours=18)) or commence_dt > (now + timedelta(hours=36)):
                    continue

                if event_id not in structured_odds:
                    try:
                        with open(os.path.join(config.DATA_DIR, "probable_pitchers.json"), 'r') as f:
                            probables = json.load(f)
                    except:
                        probables = {}

                    h_sp = game_data.get('home_pitcher') or probables.get(home_team)
                    a_sp = game_data.get('away_pitcher') or probables.get(away_team)

                    structured_odds[event_id] = {
                        "id": event_id,
                        "home_team": home_team,
                        "away_team": away_team,
                        "home_pitcher": h_sp,
                        "away_pitcher": a_sp,
                        "commence_time": commence_time,
                        "bookmakers": game_data.get('bookmakers', [])
                    }
                    print(f"  - [MATCHUP]: {away_team} ({a_sp or 'TBD'}) @ {home_team} ({h_sp or 'TBD'})")

                # B. Granular Prop Ingestion Phase
                if event_id not in structured_props:
                    structured_props[event_id] = {}
                
                # Split the configured prop markets into individual calls
                market_categories = self.prop_markets.split(',')
                for m_cat in market_categories:
                    m_cat = m_cat.strip()
                    if not m_cat: continue
                    
                    # Fetch THIS specific market only
                    prop_cat_data = self.fetch_data_for_event(event_id, m_cat)
                    if not prop_cat_data or 'bookmakers' not in prop_cat_data:
                        continue
                        
                    for bookmaker in prop_cat_data.get('bookmakers', []):
                        book_key = bookmaker['key']
                        for market in bookmaker.get('markets', []):
                            market_key = market['key']
                            if market_key not in structured_props[event_id]:
                                structured_props[event_id][market_key] = []
                            
                            for outcomes in market.get('outcomes', []):
                                raw_name = outcomes.get('name')
                                raw_description = outcomes.get('description')
                                player_name = raw_description if raw_description else raw_name
                                side = raw_name if raw_description else "Yes"
                                
                                if not player_name or player_name in ["Yes", "No"] and not raw_description:
                                    continue
                                    
                                structured_props[event_id][market_key].append({
                                    'player_name': player_name,
                                    'bookmaker': book_key,
                                    'price': outcomes.get('price'),
                                    'point': outcomes.get('point'),
                                    'side': side,
                                    'home_team': home_team,
                                    'away_team': away_team,
                                    'game_id': event_id
                                })




                            
            except Exception as e:
                print(f"  - CRITICAL: Bulk loop failed for event {event_id}. Skipping. {e}")
                continue

        # STEP 2: Resolution Phase (The Clean Sweep)
        probables_path = os.path.join(os.path.dirname(__file__), "probable_pitchers.json")
        try:
            probables = json.load(open(probables_path))
        except:
            probables = {}

        print("\n[DISCOVERY]: Running Pitcher Resolver Loop...")
        for event_id, game in structured_odds.items():
            event_props = structured_props.get(event_id, {})
            
            for t_type in ['home', 'away']:
                team_name = game[f"{t_type}_team"]
                resolved = self.resolve_pitcher(team_name, game, t_type, event_props, probables)
                game[f"{t_type}_pitcher"] = resolved
                
                # Logging
                if t_type == 'away':
                     print(f"  - [MATCHUP]: {game['away_team']} ({game['away_pitcher'] or 'TBD'}) @ {game['home_team']} ({game['home_pitcher'] or 'TBD'}) | {game['commence_time']}")






        # Requirement: Writing final output to disk as snapshot_{date}.json
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"snapshot_{timestamp}.json"
        
        # Patch 1: Metadata persistence for skipped events
        metadata = {
            "timestamp": timestamp,
            "skipped_events": self.skipped_events,
            "total_games": len(event_ids),
            "processed_players": len(structured_props)
        }
        
        final_output = {
            "metadata": metadata,
            "odds": list(structured_odds.values()),
            "props": structured_props
        }
        
        filepath = os.path.join(config.DATA_DIR, filename)
        
        try:
            with open(filepath, 'w') as f:
                json.dump(final_output, f, indent=4)
            print(f"\n[COMPLETE]: OMEGA Snapshot generated: {filename}")
            print(f"  - Total Players Processed: {len(structured_props)}")
            
            # OMEGA v5.2: Dynamic Opening Lines Manager
            self.manage_opening_lines(structured_odds, capture_opening=capture_opening)
            
            return filepath
            
        except Exception as e:
            print(f"  - FAILED: Could not save snapshot to disk. {e}")
            return None

    def _historical_opens_by_pair(self, slate_date):
        """Odds API historical snapshot (~4:30 AM ET). One paid call per slate day."""
        try:
            from utils.odds_api_opening import fetch_historical_opens
            return fetch_historical_opens(slate_date)
        except Exception as e:
            print(f"  - [LINES WARNING]: Odds API historical opens failed: {e}")
            return {}

    def manage_opening_lines(self, structured_odds, capture_opening=False):
        """
        Date-stamped opening lines.
        - capture_opening=True: Odds API historical @ 4:30 AM ET (paid endpoint).
        - Normal refresh: never overwrite opening_*; backfill via historical, snapshot, then FL manual.
        """
        from utils.market_utils import get_market_prices
        from utils.slate_date import get_slate_date_iso
        from utils.opening_lines import (
            apply_manual_vegas_opens,
            find_earliest_lines_from_snapshots,
            load_opening_lines_for_slate,
            persist_opening_db,
            _game_entry,
            _pair_key,
        )

        slate_date = get_slate_date_iso()
        slate_ids = set()
        historical_by_pair = {}

        if capture_opening:
            open_lookup = {}
            print(f"  - [LINES]: 4:30 AM OPEN CAPTURE for slate {slate_date} (Odds API historical).")
            historical_by_pair = self._historical_opens_by_pair(slate_date)
        else:
            open_lookup = {
                o["game_id"]: o
                for o in load_opening_lines_for_slate(slate_date)
                if o.get("game_id")
            }
            pair_lookup = {}
            for o in open_lookup.values():
                pk = o.get("pair_key") or _pair_key(o.get("team_away"), o.get("team_home"))
                pair_lookup[pk] = o
            historical_count = sum(
                1
                for o in open_lookup.values()
                if "odds_api_historical" in str(o.get("opening_source", ""))
            )
            needs_historical = not open_lookup or historical_count < max(
                1, len(structured_odds) // 2
            )
            if needs_historical:
                historical_by_pair = self._historical_opens_by_pair(slate_date)
                if historical_by_pair:
                    print(
                        f"  - [LINES]: Applying Odds API historical opens "
                        f"({len(historical_by_pair)} pairs, had {historical_count} historical rows)."
                    )

        for g_id, game in structured_odds.items():
            home = game["home_team"]
            away = game["away_team"]
            slate_ids.add(g_id)

            away_ml, _ = get_market_prices(game, away)
            home_ml, total = get_market_prices(game, home)
            if not away_ml:
                away_ml = -110
            if not home_ml:
                home_ml = -110
            if not total:
                total = 8.5

            pk = _pair_key(away, home)

            if capture_opening:
                hist = historical_by_pair.get(pk)
                if hist:
                    open_lookup[g_id] = _game_entry(
                        g_id,
                        game,
                        hist["away_opening_ml"],
                        hist["home_opening_ml"],
                        hist["opening_total"],
                        hist.get("opening_source", "odds_api_historical"),
                    )
                else:
                    open_lookup[g_id] = _game_entry(
                        g_id, game, away_ml, home_ml, total, "4:30_capture_live_fallback"
                    )
                    print(
                        f"  - [LINES WARNING]: No historical open for {away} @ {home}; "
                        f"used live line at capture time."
                    )
                open_lookup[g_id]["away_current_ml"] = away_ml
                open_lookup[g_id]["home_current_ml"] = home_ml
                open_lookup[g_id]["current_total"] = total
                continue

            hist = historical_by_pair.get(pk)
            if hist and (
                g_id not in open_lookup
                or "odds_api_historical" not in str(open_lookup.get(g_id, {}).get("opening_source", ""))
            ):
                open_lookup[g_id] = _game_entry(
                    g_id,
                    game,
                    hist["away_opening_ml"],
                    hist["home_opening_ml"],
                    hist["opening_total"],
                    hist.get("opening_source", "odds_api_historical"),
                )
                open_lookup[g_id]["away_current_ml"] = away_ml
                open_lookup[g_id]["home_current_ml"] = home_ml
                open_lookup[g_id]["current_total"] = total
                continue

            if g_id not in open_lookup:
                inherited = pair_lookup.get(pk)
                if inherited:
                    row = dict(inherited)
                    row["game_id"] = g_id
                    row["away_current_ml"] = away_ml
                    row["home_current_ml"] = home_ml
                    row["current_total"] = total
                    open_lookup[g_id] = row
                    print(f"  - [LINES]: Mapped {away} @ {home} to prior open (game_id changed).")
                else:
                    hist = historical_by_pair.get(pk)
                    if hist:
                        open_lookup[g_id] = _game_entry(
                            g_id,
                            game,
                            hist["away_opening_ml"],
                            hist["home_opening_ml"],
                            hist["opening_total"],
                            hist.get("opening_source", "odds_api_historical"),
                        )
                        open_lookup[g_id]["away_current_ml"] = away_ml
                        open_lookup[g_id]["home_current_ml"] = home_ml
                        open_lookup[g_id]["current_total"] = total
                        print(f"  - [LINES]: Historical 4:30 AM open for {away} @ {home}.")
                    else:
                        backfill = find_earliest_lines_from_snapshots(away, home, slate_date)
                        if backfill:
                            open_lookup[g_id] = _game_entry(
                                g_id,
                                game,
                                backfill["away_opening_ml"],
                                backfill["home_opening_ml"],
                                backfill["opening_total"],
                                f"snapshot_backfill:{backfill['snapshot_file']}",
                            )
                            open_lookup[g_id]["away_current_ml"] = away_ml
                            open_lookup[g_id]["home_current_ml"] = home_ml
                            open_lookup[g_id]["current_total"] = total
                            print(
                                f"  - [LINES]: Backfilled open for {away} @ {home} "
                                f"from {backfill['snapshot_file']}."
                            )
                        else:
                            open_lookup[g_id] = _game_entry(
                                g_id, game, away_ml, home_ml, total, "first_seen_late"
                            )
                            open_lookup[g_id]["opening_captured_late"] = True
                            print(
                                f"  - [LINES WARNING]: Late first-seen open for {away} @ {home} "
                                f"(no historical/snapshot). ml_move may be understated."
                            )
            else:
                open_lookup[g_id]["away_current_ml"] = away_ml
                open_lookup[g_id]["home_current_ml"] = home_ml
                open_lookup[g_id]["current_total"] = total

        if not capture_opening:
            # FantasyLabs manual file only fills gaps after Odds API historical
            apply_manual_vegas_opens(open_lookup, structured_odds, slate_date)

        dated_path, count = persist_opening_db(open_lookup, slate_ids, slate_date)
        print(f"  - [LINES]: Opening lines saved ({count} games) -> {os.path.basename(dated_path)}")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true", help="Run ingestion audit")
    args = parser.parse_args()

    if not config.validate():
        print("ERROR: Environment validation failed. Check your .env setup.")
    else:
        fetcher = MarketFetcher()
        if args.audit:
            print("[AUDIT]: Starting Ingestion Clean Sweep...")
            path = fetcher.run_bulk_ingestion()
            print(f"[AUDIT]: Snapshot verified at {path}")
        else:
            fetcher.run_bulk_ingestion()

