import os
import json
import argparse
import subprocess
import math
import statistics
from data.pitcher_analyzer import PitcherAnalyzer
from engine.hitter_alpha import HitterAlpha
from data.hitter_prop_analyzer import HitterPropAnalyzer
from data.movement_tracker import MovementTracker
from data.weather_fetcher import WeatherFetcher
from data.consensus_fetcher import ConsensusFetcher
from data.umpire_fetcher import UmpireFetcher

# OMEGA v3.2.1.8: Hard Revert - Shielding Strip
# No more shield_float or defaults. Raw data only.

from engine.sharps_weighting import SharpsWeighting
from utils.dashboard_generator import DashboardGenerator
from utils.audit_engine import AuditEngine
from config import config
from utils.normalization import normalize_player_name
from utils.market_utils import get_market_prices, calculate_ml_move

def _get_resilient_snapshot():
    """OMEGA v5: Soft-Gate Snapshot Recovery."""
    files = [f for f in os.listdir(config.DATA_DIR) if f.startswith("snapshot_") and f.endswith(".json")]
    if not files: return None
    files.sort(reverse=True)
    
    # Try the newest first
    for f in files:
        f_path = os.path.join(config.DATA_DIR, f)
        # If file is valid JSON, return it
        try:
            with open(f_path, 'r') as check:
                json.load(check)
            return f_path
        except:
            continue
    return None

def run_full_analysis():
    # OMEGA v5: Soft-Gate Cache Clearing (12-hour stickiness)
    print("[INIT]: Syncing v5.0 Master Convergence...")
    import time
    now = time.time()
    for f in os.listdir(config.DATA_DIR):
        f_path = os.path.join(config.DATA_DIR, f)
        if f.startswith("snapshot_") and f.endswith(".json"):
            # Only delete if older than 4 hours (14400s)
            if now - os.path.getmtime(f_path) > 14400:
                try: os.remove(f_path)
                except: pass

    print("\n" + "="*50)
    print("      MLB Omega DFS + Betting engine v.5.0")
    print("="*50)
    
    # 1. Initialize
    p_analyzer = PitcherAnalyzer()
    h_prop_analyzer = HitterPropAnalyzer()
    sharps_weighting = SharpsWeighting()
    dash_gen = DashboardGenerator()
    weather_fetcher = WeatherFetcher()
    consensus_fetcher = ConsensusFetcher()
    umpire_fetcher = UmpireFetcher()
    from data.bullpen_analyzer import BullpenAnalyzer
    bullpen_analyzer = BullpenAnalyzer()
    
    # Pre-fetch live sentiment data
    print("[INIT]: Syncing atmospheric and officiating sentiment...")
    umpire_assignments = umpire_fetcher.fetch_daily_assignments()
    
    snapshot_path = _get_resilient_snapshot()
    if not snapshot_path:
        print("ERROR: No snapshot found.")
        return
    
    print(f"[INIT]: Loading OMEGA Snapshot: {os.path.basename(snapshot_path)}")
    
    with open(snapshot_path, 'r') as f:
        snapshot = json.load(f)
    
    print(f"[INIT]: Analysis targeting {len(snapshot.get('odds', []))} Night Slate matchups.")

        
    opening_lines_path = os.path.join(config.DATA_DIR, "opening_lines.json")
    with open(opening_lines_path, 'r') as f:
        opening_lines = json.load(f)
        
    # OMEGA v5.2: Load Consensus Splits for SHARK Detection
    splits_data = snapshot.get('splits', {})
    if not splits_data or splits_data == {"notes": "Scraper initialized. Real-time parsing logic pending."}:
        splits_data = consensus_fetcher._load_cache()
    
    # OMEGA v5: Load External Probables (Singer/Drohan Source of Truth)
    probables_path = os.path.join(config.DATA_DIR, "probable_pitchers.json")
    probables = {}
    if os.path.exists(probables_path):
        with open(probables_path, 'r') as f:
            probables = json.load(f)
    
    # Roster Mapping (v3.2.1.10 Direct Recovery with Probable Overlay)
    rosters = {}
    for e in snapshot.get('odds', []):
        home = e['home_team']
        away = e['away_team']
        # OMEGA v4.6.0: Discovery strictly from API odds or TBD for Prop Discovery
        rosters[home] = e.get('home_pitcher') or "TBD"
        rosters[away] = e.get('away_pitcher') or "TBD"

    # 2. Ranking Pitcher Alpha (Hybrid Core)
    print("[STEP 1]: Ranking Pitcher Alpha...")
    p_reports = p_analyzer.analyze_slate(
        snapshot_path, 
        opening_lines_path, 
        splits_data=splits_data,
        props_data=snapshot.get('props', {}),
        rosters=rosters,
        weather_fetcher=weather_fetcher,
        umpire_fetcher=umpire_fetcher
    )
    
    # OMEGA v4.5: Component Translation
    for r in p_reports:
        res = r['alpha_score']
        r['alpha_score'] = res['final'] # Flatten for display
        r['physics_score'] = res['physics']
        r['market_score'] = res['market']
    
    # OMEGA v4.6.1: Backfill rosters with discovered pitchers
    for r in p_reports:
        if r['pitcher'] != "TBD":
            rosters[r['team']] = r['pitcher']
    
    # OMEGA v3.2.3.2: Improved Duplicate Purge
    seen_pitchers = set()
    cleaned_p_reports = []
    
    # OMEGA v6.1: Debut & Visibility Logic + Deduplication
    for r in p_reports:
        # If we have a real name, but no lines/odds, it is likely a late callup/debut
        if r['pitcher'] != "TBD" and (not r.get('k_line') or r.get('k_line') == '-'):
            r['is_debut'] = True
            r['alpha_score'] = round(r['alpha_score'] * 1.10, 1) # 10% Visibility boost for debuts
        else:
            r['is_debut'] = False

        # Deduplication
        if r['pitcher'] == "TBD":
            cleaned_p_reports.append(r)
        elif r['pitcher'] not in seen_pitchers:
            seen_pitchers.add(r['pitcher'])
            cleaned_p_reports.append(r)
            
    p_reports = cleaned_p_reports
    p_reports.sort(key=lambda x: x['alpha_score'], reverse=True)
 
    # 3. Analyze Teams (Team Omega Multiplicative Core)
    print("\n[STEP 2]: Ranking Team Omega...")
    team_reports = []
    processed_teams = set()
    
    for game in snapshot.get('odds', []):
        home = game['home_team']
        away = game['away_team']
        
        for team in [home, away]:
            if team in processed_teams: continue
            processed_teams.add(team)
            
            prices = get_market_prices(game, team)
            curr_ml = prices[0]
            curr_total = prices[1]
            
            # Opening Price Lookup (v5.3 ID-Based Master)
            gid = game['id']
            open_data = next((o for o in opening_lines if o.get('game_id') == gid), {})
            
            # Fallback for teams without ID match (transition support)
            if not open_data:
                sh_team = p_analyzer.normalized_map.get(team, team)
                open_data = next((o for o in opening_lines 
                                if any(name == team or name == sh_team for name in [o['team_away'], o['team_home']])), {})
            
            field_key = 'away' if (open_data.get('team_away') in [team]) else 'home'
            
            # Identify Opponent for OMEGA v5 Signals
            opponent = away if team == home else home
            sh_opp = p_analyzer.normalized_map.get(opponent, opponent)
            
            open_ml = open_data.get(f'{field_key}_opening_ml')
            open_total = open_data.get('opening_total')
            
            # Match discovered pitcher if metadata is missing
            identified_pitcher = rosters.get(team)
            if not identified_pitcher:
                for rep in p_reports:
                    if rep['team'] == team:
                        identified_pitcher = rep['pitcher']
                        break
            
            # Delta Calc (v5.0.5 Math Fix)
            ml_move = calculate_ml_move(open_ml, curr_ml)
            tt_move = (curr_total - open_total) if (open_total and curr_total) else 0.0
            
            # ITT Calc
            prob = p_analyzer._ml_to_prob(curr_ml if curr_ml else -110)
            curr_itt = (curr_total if curr_total else 8.5) * prob
            
            # OMEGA v5 Master Convergence: Environment & Fatigue
            park_factor = config.PARK_FACTORS.get(team, 1.0)
            opp_bullpen = bullpen_analyzer.get_fatigue_score(opponent)
            
            # OMEGA v5.2: Market Divergence & Signal Detection
            divergence = consensus_fetcher.get_divergence(team, splits_data)
            is_shark = consensus_fetcher.detect_shark(team, splits_data, ml_move)
            is_whale = consensus_fetcher.detect_whale(team, splits_data)
            is_sharp = consensus_fetcher.is_sharp_consensus(team, splits_data)
            
            # OMEGA v5.5: Correlated Momentum (Perfect Storm)
            is_storm = (divergence >= 10 and tt_move >= 0.3)
            
            res = sharps_weighting.calculate_stack_score(
                team, ml_move, tt_move, curr_itt=curr_itt, 
                park_factor=park_factor, bullpen_fatigue=opp_bullpen['score'],
                divergence=divergence, is_whale=is_whale, is_sharp=is_sharp,
                is_storm=is_storm, is_shark=is_shark
            )
            stack_score = res['final']
            physics_score = res['physics']
            market_score = res['market']
            
            # OMEGA v3.2.3: Strict Matchup Discovery
            opp_pitcher_name = rosters.get(opponent, "TBD")
            
            # v3.2.3 Fix: Correct the Giants Matchup (ensure Nola vs SFG)
            # If the API rosters have specific names, prioritize them.
            api_opp_pitcher = next((e.get('home_pitcher' if opponent == e['home_team'] else 'away_pitcher') 
                                  for e in snapshot.get('odds', []) if e['id'] == game['id']), None)
            if api_opp_pitcher: opp_pitcher_name = api_opp_pitcher
 
            # OMEGA v4.5.3: Sentiment Divergence (Venue-Based)
            venue_team = home # The team currently in the 'home' side of the iteration
            ump_data = umpire_assignments.get(venue_team, {"factor": 1.0, "name": "Unknown"})
            weather_data = weather_fetcher.get_alpha_modifier(venue_team)
            weather_boost = weather_data['boost']
            
            # OMEGA v6.1: Dampened Environmental Synergy
            # Umpire Factor: > 1.0 = Pitcher Friendly. So 1.0/factor = Hitter Mod.
            sentiment_mod = (1.0 / ump_data.get('factor', 1.0))
            
            # Dampened Synergy: Treatments weather as a 1% nudge per boost unit
            env_synergy = 1.0 + (weather_boost / 100.0)
            final_stack_score = round(stack_score * sentiment_mod * env_synergy, 1)
            
            # OMEGA v5.2: SHARK Conviction Boost
            if is_shark:
                final_stack_score = round(final_stack_score * 1.15, 1)  # +15% RLM conviction boost


            
            team_reports.append({
                'team': team,
                'opponent': opponent,
                'opp_pitcher': opp_pitcher_name,
                'ml_move': ml_move,
                'tt_move': tt_move,
                'stack_score': final_stack_score,
                'physics_score': physics_score,
                'market_score': market_score,
                'weather_label': weather_data['label'],
                'umpire_name': ump_data.get('name', 'Unknown'),
                'bullpen_fatigue': opp_bullpen['score'],
                'is_gassed': opp_bullpen['is_gassed'],
                'is_fatigued': opp_bullpen.get('is_fatigued', False),
                'is_shark': is_shark,
                'is_whale': is_whale,
                'is_sharp': is_sharp,
                'is_storm': is_storm,
                'divergence': divergence
            })

    # Mandatory Omega Sorting
    team_reports.sort(key=lambda x: x['stack_score'], reverse=True)

    # 4. Analyze Individual Hitters
    print("\n[STEP 3]: Ranking Hitter Alpha...")
    raw_hitters = h_prop_analyzer.extract_top_hitters(snapshot_path)
    h_reports = []
    
    for h in raw_hitters:
        team_score = 50.0
        for tr in team_reports:
            if tr['team'] == h['team']:
                team_score = tr['stack_score']
                break
        
        # - [x] Implement Hybrid Scoring Model in `sharps_weighting.py`
        # - [x] Implement Cache Clear hook in `main.py`
        # - [x] Restore Starter Matrix and Fallback in `pitcher_analyzer.py`
        # - [x] Fix TBD filtering and deduplication in `main.py`
        # - [/] Verify Dashboard Visibility
        # - [x] Update Scoring Model with 100.0 Cap in `sharps_weighting.py`
        # - [x] Refine Matchup Mapping and Drop Duplicates in `main.py`
        # - [/] Verify OMEGA v3.2.3 results
        # OMEGA v5 Environment & Fatigue Signals
        venue_team = next((tr['team'] if tr.get('is_home') else tr['opponent'] 
                          for tr in team_reports if tr['team'] == h['team']), h['team'])
        park_factor = config.PARK_FACTORS.get(venue_team, 1.0)
        
        # Determine opponent bullpen fatigue
        opp_bullpen_score = next((tr['bullpen_fatigue'] for tr in team_reports if tr['team'] == h['team']), 0)

        # OMEGA v6.0 SE: Momentum Signal Enrichment (Moved up for tiered scoring)
        is_hot = False
        mom = h_prop_analyzer.statcast.get_player_momentum(h['name'])
        if mom and mom.get('ops', 0) > 0.900: is_hot = True

        res = sharps_weighting.calculate_individual_hitter_score(
            h['name'], team_score, h.get('matchup_xwoba', 0.330), h.get('ahr_price', 400),
            park_factor=park_factor,
            is_target=h.get('is_juiced_target', False),
            is_speed_target=h.get('is_speed_target', False),
            is_hot=is_hot
        )

        # Extract matchup info for rendering
        opp_pitcher = next((tr['opp_pitcher'] for tr in team_reports if tr['team'] == h['team']), "TBD")
        opp_team = next((tr['opponent'] for tr in team_reports if tr['team'] == h['team']), "TBD")

        h_reports.append({
            'name': h['name'],
            'team': h['team'],
            'opponent': opp_team,
            'opp_pitcher': opp_pitcher,
            'player_score': res['final'],


            'physics_score': res['physics'],
            'market_score': res['market'],
            'matchup_xwoba': h.get('matchup_xwoba', 0.330),
            'ahr_price': h.get('ahr_price', 400),
            'hit_line': h.get('hit_line', '-'),
            'hits_price': h.get('hits_price', 0),
            'bullpen_fatigue': opp_bullpen_score,
            'is_hot': is_hot,
            'is_juiced_target': h.get('is_juiced_target', False),
            'is_speed_target': h.get('is_speed_target', False)
        })

    h_reports.sort(key=lambda x: x['player_score'], reverse=True)
    
    # OMEGA v3.2.3: Final Deduplication Purge
    seen_hitters = set()
    cleaned_h_reports = []
    for hr in h_reports:
        if hr['name'] not in seen_hitters:
            seen_hitters.add(hr['name'])
            cleaned_h_reports.append(hr)
    h_reports = cleaned_h_reports

    # 5. Generate Dash
    dash_gen.generate_report(p_reports, team_reports, h_reports)
    
    # OMEGA v4.5: Export Summary for Bot/Sentry
    summary = {
        "timestamp": datetime.datetime.now().isoformat(),
        "pitchers": p_reports,
        "teams": team_reports,
        "hitters": h_reports
    }
    results_path = os.path.join(config.REPORTS_DIR, "latest_results.json")
    with open(results_path, 'w') as f:
        json.dump(summary, f, indent=4)
        
    print(f"\n[SUMMARY]: Results exported to {results_path}")
    print(f"VIEW DASHBOARD v4.5: {dash_gen.output_path}")

if __name__ == "__main__":
    import datetime
    run_full_analysis()
