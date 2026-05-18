import os
import json
import argparse
import subprocess
import math
import statistics
import time
import datetime
from data.pitcher_analyzer import PitcherAnalyzer
from engine.hitter_alpha import HitterAlpha
from data.hitter_prop_analyzer import HitterPropAnalyzer
from data.movement_tracker import MovementTracker
from data.weather_fetcher import WeatherFetcher
from data.consensus_fetcher import ConsensusFetcher
from data.umpire_fetcher import UmpireFetcher
from data.bullpen_analyzer import BullpenAnalyzer
from data.lineup_fetcher import LineupFetcher
from data.statcast_bridge import StatcastBridge

# OMEGA v3.2.1.8: Hard Revert - Shielding Strip
# No more shield_float or defaults. Raw data only.

from engine.sharps_weighting import SharpsWeighting
from engine.matchup_radar import MatchupRadar
from utils.dashboard_generator import DashboardGenerator
from utils.audit_engine import AuditEngine
from utils.slate_report_generator import SlateReportGenerator
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

def cleanup_old_snapshots():
    """OMEGA v5: Soft-Gate Cache Clearing (12-hour stickiness)"""
    print("[INIT]: Syncing v5.0 Master Convergence...")
    now = time.time()
    for f in os.listdir(config.DATA_DIR):
        f_path = os.path.join(config.DATA_DIR, f)
        if f.startswith("snapshot_") and f.endswith(".json"):
            # Only delete if older than 4 hours (14400s)
            if now - os.path.getmtime(f_path) > 14400:
                try: 
                    os.remove(f_path)
                except Exception:
                    pass

def run_full_analysis():
    cleanup_old_snapshots()

    print("\n" + "="*50)
    print("      MLB Omega DFS + Betting engine v.5.0")
    print("="*50)
    
    # 1. Initialize
    p_analyzer = PitcherAnalyzer()
    h_prop_analyzer = HitterPropAnalyzer()
    sharps_weighting = SharpsWeighting()
    matchup_radar = MatchupRadar()
    
    # OMEGA v7.8: Sunday Automation Trigger
    import datetime
    if datetime.datetime.now().weekday() == 6: # Sunday
        matchup_radar.refresh_data()
    dash_gen = DashboardGenerator()
    weather_fetcher = WeatherFetcher()
    consensus_fetcher = ConsensusFetcher()
    umpire_fetcher = UmpireFetcher()
    bullpen_analyzer = BullpenAnalyzer()
    
    # Pre-fetch live sentiment data
    print("[INIT]: Syncing atmospheric and officiating sentiment...")
    umpire_assignments = umpire_fetcher.fetch_daily_assignments()
    
    # OMEGA v6.8.5: Fetch Confirmed Lineups
    lineup_fetcher = LineupFetcher()
    confirmed_lineups = lineup_fetcher.fetch_confirmed_lineups()
    
    snapshot_path = _get_resilient_snapshot()
    if not snapshot_path:
        print("ERROR: No snapshot found.")
        return
    
    print(f"[INIT]: Loading OMEGA Snapshot: {os.path.basename(snapshot_path)}")
    
    with open(snapshot_path, 'r') as f:
        snapshot = json.load(f)
    print(f"[INIT]: Analysis targeting {len(snapshot.get('odds', []))} Night Slate matchups.")
    
    # OMEGA v6.9: Applied Date-Aware Slate Filter
    allowed_teams = config.get_slate_filter()
    if allowed_teams:
        original_count = len(snapshot.get('odds', []))
        snapshot['odds'] = [
            g for g in snapshot.get('odds', []) 
            if g['home_team'] in allowed_teams or g['away_team'] in allowed_teams
        ]
        print(f"[SLATE]: FILTER ACTIVE ({datetime.date.today()}). Isolated {len(snapshot['odds'])} of {original_count} matchups.")

    opening_lines_path = os.path.join(config.DATA_DIR, "opening_lines.json")
    with open(opening_lines_path, 'r') as f:
        opening_lines = json.load(f)
        
    # OMEGA v5.2: Load Consensus Splits for SHARK Detection
    splits_data = snapshot.get('splits', {})
    if not splits_data or splits_data == {"notes": "Scraper initialized. Real-time parsing logic pending."}:
        splits_data = consensus_fetcher._load_cache()

    # OMEGA v6.8: Load Totals Divergence (Visual-only, isolated from scoring)
    totals_data = consensus_fetcher.load_totals_cache()
    
    # Roster Mapping
    rosters = {}
    for entry in snapshot.get('odds', []):
        rosters[entry['home_team']] = entry.get('home_pitcher') or "TBD"
        rosters[entry['away_team']] = entry.get('away_pitcher') or "TBD"

    # Movement Tracker (v7.8 Trap Detector Support)
    movement_tracker = MovementTracker()
    movement_data = movement_tracker.calculate_movement() or []

    # 2. Ranking Pitcher Alpha
    p_reports = _get_pitcher_alpha(
        p_analyzer, snapshot_path, opening_lines_path, splits_data, 
        snapshot.get('props', {}), rosters, weather_fetcher, umpire_fetcher,
        movement_data=movement_data
    )
    
    # OMEGA v6.21: The Integrity Gate
    p_integrity_map = {(r['event_id'], r['team']): r for r in p_reports}
 
    # Trend Analysis Initialization
    previous_results = {}
    results_path = os.path.join(config.REPORTS_DIR, "latest_results.json")
    if os.path.exists(results_path):
        try:
            with open(results_path, 'r') as f:
                prev_data = json.load(f)
                previous_results = {t['team']: t for t in prev_data.get('teams', [])}
        except Exception:
            print("[WARNING]: Could not load previous results for trend analysis.")

    # 3. Extract Hitters Early for Team Analysis (v6.8)
    raw_hitters = h_prop_analyzer.extract_top_hitters(snapshot_path, confirmed_lineups=confirmed_lineups)
    
    # OMEGA v6.9.7: Fuzzy Franchise Purge
    # Purge any hitter not in the confirmed starters using fuzzy team matching.
    if confirmed_lineups:
        from utils.normalization import normalize_player_name
        purged_hitters = []
        for h in raw_hitters:
            h_team = h['team'].lower()
            # Find the confirmed lineup by looking for a fuzzy match in the keys
            confirmed = None
            for lineup_team, players in confirmed_lineups.items():
                if h_team in lineup_team.lower() or lineup_team.lower() in h_team:
                    confirmed = players
                    break
            
            if confirmed:
                if normalize_player_name(h['name']) in confirmed:
                    purged_hitters.append(h)
            else:
                purged_hitters.append(h) # Keep projected if no official data exists
        raw_hitters = purged_hitters
        print(f"[PURGE]: Cleaned hitter pool via Fuzzy Matching. Bench players removed.")

    # 4. Analyze Teams
    team_reports = _get_team_reports(
        snapshot, opening_lines, rosters, p_analyzer, p_integrity_map, 
        bullpen_analyzer, consensus_fetcher, splits_data, 
        umpire_assignments, weather_fetcher, previous_results, totals_data,
        raw_hitters=raw_hitters, confirmed_lineups=confirmed_lineups
    )

    # 5. Analyze Hitters
    h_reports = _get_hitter_alpha(h_prop_analyzer, snapshot_path, team_reports, sharps_weighting, matchup_radar, raw_hitters=raw_hitters)

    # 5.5 OMEGA v6.8.5: Paradox Resolution
    # We run this after Hitters (who depend on Teams) but before the Dashboard.
    p_reports = _resolve_pitcher_team_conflicts(p_reports, team_reports)

    # 6. Generate Analysis Report (Must come BEFORE Dashboard)
    SlateReportGenerator().generate(p_reports, team_reports, h_reports)

    # 7. Generate Dashboard
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


    # OMEGA v7.1: Archive results for multi-day post-mortem
    archive_dir = os.path.join(config.REPORTS_DIR, "archive")
    os.makedirs(archive_dir, exist_ok=True)
    archive_path = os.path.join(archive_dir, f"results_{datetime.date.today().isoformat()}.json")
    with open(archive_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=4)
    print(f"[ARCHIVE]: Results archived to {archive_path}")

def _get_pitcher_alpha(p_analyzer, snapshot_path, opening_lines_path, splits_data, props_data, rosters, weather_fetcher, umpire_fetcher, movement_data=None):
    """STEP 1: Ranking Pitcher Alpha (Hybrid Core)"""
    print("[STEP 1]: Ranking Pitcher Alpha...")
    p_reports = p_analyzer.analyze_slate(
        snapshot_path, 
        opening_lines_path, 
        splits_data=splits_data,
        props_data=props_data,
        rosters=rosters,
        weather_fetcher=weather_fetcher,
        umpire_fetcher=umpire_fetcher,
        movement_data=movement_data
    )
    
    # OMEGA v4.5: Component Translation
    for report in p_reports:
        res = report['alpha_score']
        report['pitcher'] = report['pitcher'].title() # Aesthetic Fix: Capitalization
        report['alpha_score'] = res['final'] # Flatten for display
        report['physics_score'] = res['physics']
        report['market_score'] = res['market']
        report['is_trap'] = res.get('is_trap', False)
        report['siera'] = report.get('siera', 4.10)
        report['is_coors'] = res.get('is_coors', False)
        report['is_paradox'] = False # Initial state
        report['is_hazard'] = False  # Initial state
        report['is_trap'] = res.get('is_trap', False)
        report['is_low_ceiling'] = False # Initial state
        report['is_sharp'] = report.get('is_sharp', False)
        report['is_whale'] = report.get('is_whale', False)
        report['is_shark'] = report.get('is_shark', False)
    
    # OMEGA v4.6.1: Backfill rosters with discovered pitchers
    for report in p_reports:
        if report['pitcher'] != "TBD":
            rosters[report['team']] = report['pitcher']
    
    # OMEGA v3.2.3.2: Improved Duplicate Purge
    seen_pitchers = set()
    cleaned_p_reports = []
    
    # OMEGA v6.1: Debut & Visibility Logic + Deduplication
    for report in p_reports:
        # If we have a real name, but no lines/odds, it is likely a late callup/debut
        if report['pitcher'] != "TBD" and (not report.get('k_line') or report.get('k_line') == '-'):
            report['is_debut'] = True
            report['alpha_score'] = round(report['alpha_score'] * 1.10, 1) # 10% Visibility boost for debuts
        else:
            report['is_debut'] = False

        # Deduplication
        if report['pitcher'] == "TBD":
            cleaned_p_reports.append(report)
        elif report['pitcher'] not in seen_pitchers:
            seen_pitchers.add(report['pitcher'])
            cleaned_p_reports.append(report)
            
    cleaned_p_reports.sort(key=lambda x: x['alpha_score'], reverse=True)
    return cleaned_p_reports

def _resolve_pitcher_team_conflicts(p_reports, team_reports):
    """
    [OMEGA v6.8.5]: The Paradox Resolver & Ceiling Monitor.
    Downgrades pitchers facing Top-3 offensive stacks and flags Hazards/Ceilings.
    """
    print("[STEP 4.5]: Resolving Pitcher-Stack Paradoxes...")
    
    # Identify the elite stacks (Top 3)
    sorted_teams = sorted(team_reports, key=lambda x: x['stack_score'], reverse=True)
    top_stack_names = [t['team'] for t in sorted_teams[:3]]
    high_power_teams = [t['team'] for t in team_reports if t['physics_score'] >= 22.0] # 22+ is elite raw power

    for p in p_reports:
        # 1. Paradox Check (Facing a Top 3 stack)
        if p['opponent'] in top_stack_names:
            p['is_paradox'] = True
            # OMEGA v7.5: The Veteran Paradox Shield
            # If a pitcher is a proven veteran (SIERA < 3.80), soften the penalty.
            is_veteran = float(p.get('siera', 4.10)) < 3.80
            penalty = 0.925 if is_veteran else 0.85 # -7.5% for vets, -15% for others
            p['alpha_score'] = round(p['alpha_score'] * penalty, 1)
            shield_label = " (SHIELDED)" if is_veteran else ""
            print(f"  - PARADOX: {p['pitcher']} ({p['team']}) penalized{shield_label} for facing Top-3 Stack {p['opponent']}")

        # 2. Power Hazard Check (Facing high raw physics)
        if p['opponent'] in high_power_teams:
            p['is_hazard'] = True
            print(f"  - HAZARD: {p['pitcher']} ({p['team']}) flagged for facing High-Power opponent {p['opponent']}")
            
        # 3. K-Ceiling Check (Low K-upside warning only, no cap)
        if p.get('k_line') and float(p['k_line']) <= 4.5:
            p['is_low_ceiling'] = True

    # Re-sort after penalties
    p_reports.sort(key=lambda x: x['alpha_score'], reverse=True)
    return p_reports

def _get_team_reports(snapshot, opening_lines, rosters, p_analyzer, p_integrity_map, bullpen_analyzer, consensus_fetcher, splits_data, umpire_assignments, weather_fetcher, previous_results, totals_data=None, raw_hitters=None, confirmed_lineups=None):
    """STEP 2: Ranking Team Omega (Multiplicative Core)"""
    print("\n[STEP 2]: Ranking Team Omega...")
    confirmed_lineups = confirmed_lineups or {}
    if totals_data is None:
        totals_data = {}
    team_reports = []
    processed_teams = set()
    
    for game in snapshot.get('odds', []):
        home = game['home_team']
        away = game['away_team']
        gid = game['id']
        
        for team in [home, away]:
            if team in processed_teams: continue
            processed_teams.add(team)
            
            prices = get_market_prices(game, team)
            curr_ml, curr_total = prices[0], prices[1]
            
            # Opening Price Lookup (v5.3 ID-Based Master)
            open_data = next((o for o in opening_lines if o.get('game_id') == gid), {})
            
            # Fallback for teams without ID match
            if not open_data:
                sh_team = p_analyzer.normalized_map.get(team, team)
                open_data = next((o for o in opening_lines 
                                if any(name == team or name == sh_team for name in [o['team_away'], o['team_home']])), {})
            
            field_key = 'away' if (open_data.get('team_away') in [team]) else 'home'
            opponent = away if team == home else home
            
            open_ml = open_data.get(f'{field_key}_opening_ml')
            open_total = open_data.get('opening_total')
            
            # Delta Calc
            ml_move = calculate_ml_move(open_ml, curr_ml)
            tt_move = (curr_total - open_total) if (open_total and curr_total) else 0.0
            
            # ITT Calc
            prob = p_analyzer._ml_to_prob(curr_ml if curr_ml else -110)
            curr_itt = (curr_total if curr_total else 8.5) * prob
            
            # OMEGA v6.9.2: Location-Aware Park Factors
            # Both teams inherit the environment of the home_team's stadium.
            home_team_for_game = game.get('home_team')
            park_factor = config.PARK_FACTORS.get(home_team_for_game, 1.0)
            opp_bullpen = bullpen_analyzer.get_fatigue_score(opponent)
            
            # Market Divergence & Signal Detection
            divergence = consensus_fetcher.get_divergence(team, splits_data)
            is_shark = consensus_fetcher.detect_shark(team, splits_data, ml_move)
            is_whale = consensus_fetcher.detect_whale(team, splits_data)
            is_sharp = consensus_fetcher.is_sharp_consensus(team, splits_data)
            is_storm = (divergence >= 10 and tt_move >= 0.3)
            is_steam = consensus_fetcher.detect_steam(team, splits_data, ml_move)

            # Opponent Physics discovery
            opp_pitcher_physics = 0.0
            opp_pitcher_rep = p_integrity_map.get((gid, opponent))
            if opp_pitcher_rep:
                opp_pitcher_physics = opp_pitcher_rep['physics_score']
                
                # OMEGA v8.1: NEUTRALIZE ELITE SUPPRESSOR
                if opp_pitcher_rep.get('is_trap', False):
                    prev_physics = opp_pitcher_physics
                    opp_pitcher_physics = min(opp_pitcher_physics, 65.0)
                    if prev_physics > 65.0:
                        print(f"  - NEUTRALIZED: Capped {opp_pitcher_rep['pitcher']} physics score to 65.0 (was {prev_physics:.1f}) due to TRAP/DEATH SENTENCE flag")
                    
                opp_pitcher_name = opp_pitcher_rep['pitcher']
            else:
                opp_pitcher_name = rosters.get(opponent, "TBD")
                # Secondary lookup
                api_opp_pitcher = next((e.get('home_pitcher' if opponent == e['home_team'] else 'away_pitcher') 
                                      for e in snapshot.get('odds', []) if e['id'] == gid), None)
                if api_opp_pitcher: opp_pitcher_name = api_opp_pitcher
                
                # If we have a name but no report, try a fresh fetch
                if opp_pitcher_name != "TBD":
                    print(f"  [RESCUE]: Attempting fresh physics fetch for {opp_pitcher_name}...")
                    physics = p_analyzer.fetch_pitcher_physics(opp_pitcher_name)
                    opp_pitcher_physics = round(physics['bm_score'] * 1.8, 1) # v6.8 scale
                    opp_pitcher_rep = {
                        'pitcher': opp_pitcher_name,
                        'physics_score': opp_pitcher_physics,
                        'confidence': physics.get('confidence', 'low')
                    }

            # OMEGA v7.0: Power Concentration Discovery
            team_h = [h for h in (raw_hitters or []) if h['team'] == team]
            confirmed = None
            for lineup_team, players in confirmed_lineups.items():
                if team.lower() in lineup_team.lower() or lineup_team.lower() in team.lower():
                    confirmed = players
                    break
            lineup_status = "CONFIRMED" if confirmed else "PROJECTED"

            team_xwoba = 0.330
            power_concentration = 0.330
            if team_h:
                # Sort by matchup_xwoba descending
                sorted_h = sorted(team_h, key=lambda x: x.get('matchup_xwoba', 0.330), reverse=True)
                # For confirmed lineups, we use all confirmed players. For projected, top 5.
                sample_size = 5 if not confirmed else len(sorted_h)
                target_h = sorted_h[:sample_size]
                team_xwoba = statistics.mean([h.get('matchup_xwoba', 0.330) for h in target_h])
                
                # Weighted Concentration (Top 2: 40%, 3-4: 30%, Rest: 30%)
                top_2 = statistics.mean([h.get('matchup_xwoba', 0.330) for h in sorted_h[:2]])
                next_2 = statistics.mean([h.get('matchup_xwoba', 0.330) for h in sorted_h[2:4]]) if len(sorted_h) >= 4 else top_2
                rest = statistics.mean([h.get('matchup_xwoba', 0.330) for h in sorted_h[4:]]) if len(sorted_h) > 4 else next_2
                power_concentration = (top_2 * 0.4) + (next_2 * 0.3) + (rest * 0.3)
                
                print(f"  - Calculated {team} xwOBA: {team_xwoba:.3f} | Conc: {power_concentration:.3f} ({lineup_status})")

            from engine.sharps_weighting import SharpsWeighting
            sharps_weighting = SharpsWeighting()
            
            # Confidence and Leash Discovery
            opp_confidence = opp_pitcher_rep.get('confidence', 'low') if opp_pitcher_rep else 'low'
            opp_outs = opp_pitcher_rep.get('outs_line', 15.5) if opp_pitcher_rep else 15.5
            
            # OMEGA v8.0: Evaluate Burst Pre-Scoring
            is_burst = (power_concentration > 0.355 or (opp_bullpen['score'] >= 80 and float(opp_outs) < 15.5))
            
            res = sharps_weighting.calculate_stack_score(
                team, ml_move, tt_move, curr_itt=curr_itt, team_xwoba=team_xwoba,
                power_concentration=power_concentration,
                park_factor=park_factor, bullpen_fatigue=opp_bullpen['score'],
                divergence=divergence, is_whale=is_whale, is_sharp=is_sharp,
                is_storm=is_storm, is_shark=is_shark, is_steam=is_steam,
                opp_pitcher_physics=opp_pitcher_physics,
                confidence=opp_confidence, pitcher_outs=float(opp_outs),
                is_burst=is_burst
            )
            
            # Sentiment Divergence (Venue-Based)
            ump_data = umpire_assignments.get(home, {"factor": 1.0, "name": "Unknown"})
            weather_data = weather_fetcher.get_alpha_modifier(home)
            
            # Dampened Environmental Synergy
            sentiment_mod = (1.0 / ump_data.get('factor', 1.0))
            env_synergy = 1.0 + (weather_data['boost'] / 100.0)
            
            # Dominance Penalty
            dominance_penalty = 0.0
            if opp_pitcher_rep:
                alpha = opp_pitcher_rep.get('alpha_score', 0)
                opp_pitcher_alpha = alpha.get('final', 0) if isinstance(alpha, dict) else alpha
                if opp_pitcher_alpha > 80:
                    dominance_penalty = (opp_pitcher_alpha - 80) * 0.5
            
            final_stack_score = round((res['final'] - dominance_penalty) * sentiment_mod * env_synergy, 1)
            if is_shark: final_stack_score = round(final_stack_score * 1.15, 1)

            # Trend Analysis (OMEGA v6.3: Velocity-Gated Momentum)
            # PATCH (4/19/26): SURGING/FADING now requires BOTH a meaningful delta
            # AND a directionally-consistent current divergence to prevent false
            # signals near zero (e.g. -8 → -5 delta firing SURGING on a net-fade).
            trend = "STABLE"
            prev_div = previous_results.get(team, {}).get('divergence')
            if prev_div is not None:
                delta = divergence - prev_div
                # Must have velocity (delta) AND current divergence must confirm direction
                if delta >= 3.0 and divergence >= 5:
                    trend = "SURGING"
                elif delta <= -3.0 and divergence <= -5:
                    trend = "FADING"
            
            # OMEGA v7.6: Total Divergence Signal (Active Scoring Suppression)
            total_signal = ""
            ud_penalty = 0.0
            od_boost = 0.0
            if totals_data:
                # Match game by searching for both team names in the key
                home_key = home.split()[-1].upper()  # e.g. 'DODGERS'
                away_key = away.split()[-1].upper()  # e.g. 'ROCKIES'
                for gk, gv in totals_data.items():
                    gk_up = gk.upper()
                    if home_key in gk_up or away_key in gk_up:
                        od = gv.get('over_divergence', 0)
                        ud = gv.get('under_divergence', 0)
                        
                        if ud >= 15:
                            ud_penalty = 0.15 # OMEGA v8.1: 15% multiplier
                        elif ud >= 10:
                            ud_penalty = 0.05
                            
                        # OMEGA v8.0: Mechanicalize O-DIV
                        if od >= 15:
                            od_boost = 8.0
                        elif od >= 8:
                            od_boost = 5.0
                            
                        if od >= 8:
                            total_signal = f"📈 O-DIV +{od}"
                        elif ud >= 8:
                            total_signal = f"📉 U-DIV +{ud}"
                        elif od >= 4:
                            total_signal = f"↑ OVER {gv.get('over_money', '')}%$"
                        break
            
            # OMEGA v9.1: Apply +10% Stack Boost against uncalibrated Debut/Rookie pitchers
            is_opp_debut = False
            if opp_pitcher_rep and opp_pitcher_rep.get('is_debut', False):
                is_opp_debut = True
                final_stack_score = round(final_stack_score * 1.10, 1)
                print(f"  - DEBUT BOOST: Applied +10% stack multiplier vs. debut pitcher {opp_pitcher_name} (new score: {final_stack_score})")

            # OMEGA v8.0: Apply U-DIV as multiplier
            final_stack_score = max(0.0, round((final_stack_score + od_boost) * (1.0 - ud_penalty), 1))

            team_reports.append({
                'team': team, 'opponent': opponent, 'opp_pitcher': opp_pitcher_name,
                'ml_move': ml_move, 'tt_move': tt_move, 'stack_score': final_stack_score,
                'physics_score': res['physics'], 'market_score': res['market'],
                'team_xwoba': res.get('team_xwoba', 0.330),
                'power_concentration': power_concentration,
                'weather_label': weather_data['label'], 'umpire_name': ump_data.get('name', 'Unknown'),
                'bullpen_fatigue': opp_bullpen['score'], 'is_gassed': opp_bullpen['is_gassed'],
                'is_fatigued': opp_bullpen.get('is_fatigued', False), 'is_shark': is_shark,
                'is_whale': is_whale, 'is_sharp': is_sharp, 'is_storm': is_storm,
                'is_steam': is_steam, 'divergence': divergence, 'trend': trend,
                'confidence': res.get('confidence', 'low'),
                'is_burst': is_burst,
                'is_opp_debut': is_opp_debut,
                'opp_pitcher_physics': opp_pitcher_physics,
                'implied_total': round(curr_itt, 2),  # v6.3: ITT exported for trend validation
                'total_signal': total_signal  # v8.0: Now applies Mechanical Boosts
            })

    team_reports.sort(key=lambda x: x['stack_score'], reverse=True)

    # OMEGA v6.3: Auto-log SURGING/FADING tags to trend_tag_log.csv for validation
    import csv
    tagged = [t for t in team_reports if t.get('trend') in ('SURGING', 'FADING')]
    if tagged:
        log_path = os.path.join(config.LOG_DIR, "trend_tag_log.csv")
        file_exists = os.path.exists(log_path)
        slate_date = datetime.date.today().isoformat()
        slate_ts   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        with open(log_path, 'a', newline='') as csvfile:
            fieldnames = [
                'date', 'slate_timestamp', 'team', 'opponent', 'tag',
                'divergence', 'prev_divergence', 'delta',
                'ml_move', 'tt_move', 'implied_total',
                'actual_runs', 'hit'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for t in tagged:
                prev_div = previous_results.get(t['team'], {}).get('divergence')
                delta    = round(t['divergence'] - prev_div, 1) if prev_div is not None else ''
                writer.writerow({
                    'date':           slate_date,
                    'slate_timestamp': slate_ts,
                    'team':           t['team'],
                    'opponent':       t['opponent'],
                    'tag':            t['trend'],
                    'divergence':     t['divergence'],
                    'prev_divergence': prev_div if prev_div is not None else '',
                    'delta':          delta,
                    'ml_move':        t['ml_move'],
                    'tt_move':        t['tt_move'],
                    'implied_total':  t['implied_total'],
                    'actual_runs':    '',  # fill in post-game
                    'hit':            ''   # fill in post-game
                })
        print(f"[TRENDS]: {len(tagged)} tag(s) logged to trend_tag_log.csv")

    return team_reports

def _get_hitter_alpha(h_prop_analyzer, snapshot_path, team_reports, sharps_weighting, matchup_radar, raw_hitters=None):
    """STEP 3: Ranking Hitter Alpha"""
    print("\n[STEP 3]: Ranking Hitter Alpha...")
    if raw_hitters is None:
        raw_hitters = h_prop_analyzer.extract_top_hitters(snapshot_path)
    h_reports = []
    
    for h in raw_hitters:
        team_score = 50.0
        team_data = next((tr for tr in team_reports if tr['team'] == h['team']), None)
        if team_data: team_score = team_data['stack_score']
        
        venue_team = next((tr['team'] if tr.get('is_home') else tr['opponent'] 
                          for tr in team_reports if tr['team'] == h['team']), h['team'])
        park_factor = config.PARK_FACTORS.get(venue_team, 1.0)
        
        # Momentum & Vision
        is_hot = False
        vision_boost = 1.0
        mom = h_prop_analyzer.statcast.get_player_momentum(h['name'])
        if mom:
            if mom.get('ops', 0) > 0.900: is_hot = True
            if mom.get('s_k_rate', 0) > 0 and mom.get('r_k_rate', 0) < (mom.get('s_k_rate', 0) * 0.8):
                vision_boost = 1.10
        
        # Protection synergy
        protection_boost = 1.05 if (team_data and team_data.get('stack_score', 0) >= 75) else 1.0

        # OMEGA v7.7: Matchup Radar Synergy
        opp_pitcher = team_data['opp_pitcher'] if team_data else "TBD"
        matchup_radar_boost = matchup_radar.get_matchup_boost(h['name'], opp_pitcher)

        res = sharps_weighting.calculate_individual_hitter_score(
            h['name'], team_score, h.get('matchup_xwoba', 0.330), h.get('ahr_price', 400),
            park_factor=park_factor, is_target=h.get('is_juiced_target', False),
            is_speed_target=h.get('is_speed_target', False), is_hot=is_hot,
            vision_boost=vision_boost, protection_boost=protection_boost,
            matchup_radar_boost=matchup_radar_boost
        )

        # OMEGA v8.0: ICE_COLD_MARKET penalty
        try:
            if float(h.get('hit_line', 0)) >= 0.5 and float(h.get('hits_price', 0)) >= 100:
                res['final'] = round(res['final'] * 0.80, 1)
        except (ValueError, TypeError):
            pass

        h_reports.append({
            'name': h['name'].title(), 'team': h['team'], 
            'opponent': team_data['opponent'] if team_data else "TBD",
            'opp_pitcher': team_data['opp_pitcher'].title() if team_data else "TBD",
            'player_score': res['final'], 'physics_score': res['physics'],
            'market_score': res['market'], 'matchup_xwoba': h.get('matchup_xwoba', 0.330),
            'ahr_price': h.get('ahr_price', 400), 'hit_line': h.get('hit_line', '-'),
            'hits_price': h.get('hits_price', 0), 'bullpen_fatigue': team_data['bullpen_fatigue'] if team_data else 0,
            'is_hot': is_hot, 'is_juiced_target': h.get('is_juiced_target', False),
            'is_speed_target': h.get('is_speed_target', False)
        })

    h_reports.sort(key=lambda x: x['player_score'], reverse=True)
    
    # Deduplication
    seen_hitters = set()
    cleaned_h_reports = []
    for hr in h_reports:
        if hr['name'] not in seen_hitters:
            seen_hitters.add(hr['name'])
            cleaned_h_reports.append(hr)
    return cleaned_h_reports

if __name__ == "__main__":
    run_full_analysis()
