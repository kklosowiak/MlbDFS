import os
import json
import argparse
import subprocess
import math
import statistics
import time
import datetime
from data.pitcher_analyzer import PitcherAnalyzer
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
from utils.xwoba_estimates import xwoba_to_phy_score, cap_matchup_xwoba
from utils.matchup_physics import pitcher_physics_0_100
from utils.platoon_math import compute_platoon_multiplier
from utils.team_signals import apply_team_blind_spot, evaluate_burst_signal, apply_sneaky_stack, evaluate_sneaky_stack, apply_signal_exclusions

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
    
    # OMEGA v6.8.5: Fetch Confirmed and Projected Lineups
    lineup_fetcher = LineupFetcher()
    confirmed_lineups = lineup_fetcher.fetch_confirmed_lineups()
    projected_lineups = lineup_fetcher.fetch_projected_lineups()
    active_lineups = {}
    active_lineups.update(projected_lineups)
    active_lineups.update(confirmed_lineups)

    
    snapshot_path = _get_resilient_snapshot()
    if not snapshot_path:
        raise RuntimeError(
            "No odds snapshot found. Market ingest failed — check ODDS_API_KEY and /api/data-health."
        )
    
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

    from utils.opening_lines import load_opening_lines_for_slate
    from utils.slate_date import get_slate_date_iso

    opening_lines = load_opening_lines_for_slate(get_slate_date_iso())
    opening_lines_path = os.path.join(config.DATA_DIR, "opening_lines.json")
    try:
        with open(opening_lines_path, "w", encoding="utf-8") as f:
            json.dump(opening_lines, f, indent=2)
    except Exception as e:
        print(f"[WARNING]: Could not write opening lines cache: {e}")
        
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

    # OMEGA v9.8: Load Previous Results Early for Both Pitchers and Teams
    prev_pitcher_results = {}
    previous_results = {}
    results_path = os.path.join(config.REPORTS_DIR, "latest_results.json")
    if os.path.exists(results_path):
        try:
            with open(results_path, 'r') as f:
                prev_data = json.load(f)
                prev_pitcher_results = {p['pitcher']: p for p in prev_data.get('pitchers', [])}
                previous_results = {t['team']: t for t in prev_data.get('teams', [])}
        except Exception:
            print("[WARNING]: Could not load previous results for trend analysis.")

    print(f"[INIT]: Pitchers will analyze after ingest; hitters/teams follow snapshot.")

    # 2. Ranking Pitcher Alpha
    p_reports = _get_pitcher_alpha(
        p_analyzer, snapshot_path, opening_lines_path, splits_data, 
        snapshot.get('props', {}), rosters, weather_fetcher, umpire_fetcher,
        movement_data=movement_data, previous_results=prev_pitcher_results
    )
    print(f"[STEP 1 DONE]: {len(p_reports)} pitcher rows.")
    
    # OMEGA v6.21: The Integrity Gate
    p_integrity_map = {(r['event_id'], r['team']): r for r in p_reports}
 
    # 3. Extract Hitters Early for Team Analysis (v6.8)
    raw_hitters = h_prop_analyzer.extract_top_hitters(snapshot_path, confirmed_lineups=active_lineups)
    print(f"[STEP 2a]: {len(raw_hitters)} hitters before lineup purge.")
    
    # OMEGA v6.9.7: Fuzzy Franchise Purge
    # Purge any hitter not in the active starting lineup using fuzzy team matching.
    if active_lineups:
        from utils.normalization import normalize_player_name
        purged_hitters = []
        for h in raw_hitters:
            h_team = h['team'].lower()
            # Find the active lineup by looking for a fuzzy match in the keys
            confirmed = None
            for lineup_team, players in active_lineups.items():
                if h_team in lineup_team.lower() or lineup_team.lower() in h_team:
                    confirmed = players
                    break
            
            if confirmed and len(confirmed) >= 7:
                if normalize_player_name(h['name']) in confirmed:
                    purged_hitters.append(h)
            else:
                purged_hitters.append(h)
        raw_hitters = purged_hitters
        print(f"[PURGE]: Hitter pool {len(raw_hitters)} after lineup filter (from {len(active_lineups)} team keys).")

    # 4. Analyze Teams
    team_reports = _get_team_reports(
        snapshot, opening_lines, rosters, p_analyzer, p_integrity_map, 
        bullpen_analyzer, consensus_fetcher, splits_data, 
        umpire_assignments, weather_fetcher, previous_results, totals_data,
        raw_hitters=raw_hitters, confirmed_lineups=confirmed_lineups,
        projected_lineups=projected_lineups, matchup_radar=matchup_radar
    )


    # 5. Analyze Hitters
    h_reports = _get_hitter_alpha(
        h_prop_analyzer, snapshot_path, team_reports, sharps_weighting, matchup_radar,
        raw_hitters=raw_hitters, pitcher_reports=p_reports,
    )
    print(f"[STEP 3 DONE]: {len(h_reports)} hitter rows, {len(team_reports)} team rows.")

    # 5.5 OMEGA v6.8.5: Paradox Resolution
    # We run this after Hitters (who depend on Teams) but before the Dashboard.
    p_reports = _resolve_pitcher_team_conflicts(p_reports, team_reports)

    from utils.team_prop_pressure import attach_team_prop_pressure
    from utils.dqi import calculate_dqi

    attach_team_prop_pressure(team_reports, raw_hitters, active_lineups)
    for t in team_reports:
        try:
            dqi_score, dqi_status, dqi_pos, dqi_warn = calculate_dqi(t, pitchers=p_reports)
            if dqi_score is not None:
                t["dqi_score"] = dqi_score
                t["dqi_status"] = dqi_status
                t["dqi_pos_factors"] = dqi_pos
                t["dqi_warn_factors"] = dqi_warn
        except Exception as dqi_e:
            print(f"[WARNING]: DQI pre-attack skipped for {t.get('team')}: {dqi_e}")

    try:
        from utils.slate_signal_history import mark_volatile_preview

        mark_volatile_preview(config.REPORTS_DIR, team_reports, p_reports)
    except Exception as vol_e:
        print(f"[WARNING]: Volatile preview skipped: {vol_e}")

    # OMEGA: Compute GPP Leverage Index (GLI) for Team Stacks
    try:
        from utils.gpp_leverage import compute_gpp_leverage
        compute_gpp_leverage(team_reports, p_reports)
    except Exception as gli_e:
        print(f"[WARNING]: GPP Leverage Index calculation failed: {gli_e}")

    # 6. Generate Analysis Report (Must come BEFORE Dashboard)
    SlateReportGenerator().generate(p_reports, team_reports, h_reports)

    # OMEGA: Calculate Blended Stack Rating for all teams
    for t in team_reports:
        stack_score = float(t.get('stack_score', 0) or 0)
        attack_conf = float(t.get('attack_conf', 0) or 0)
        t['blended_rating'] = round((stack_score + attack_conf) / 2, 1)

    # OMEGA: Calculate Blended Pitcher Rating
    for p in p_reports:
        alpha_score = float(p.get('alpha_score', 0) or 0)
        attack_conf = float(p.get('attack_conf', 0) or 0)
        p['blended_rating'] = round((alpha_score + attack_conf) / 2, 1)

    # OMEGA: Calculate Blended Hitter Rating
    for h in h_reports:
        player_score = float(h.get('player_score', 0) or 0)
        attack_conf = float(h.get('attack_conf', 0) or 0)
        h['blended_rating'] = round((player_score + attack_conf) / 2, 1)

    try:
        from utils.slate_signal_history import persist_slate_signals, attach_signal_deltas

        persist_slate_signals(config.REPORTS_DIR, team_reports, p_reports)
        attach_signal_deltas(config.REPORTS_DIR, team_reports, p_reports)
    except Exception as sig_e:
        print(f"[WARNING]: Signal history failed: {sig_e}")

    try:
        from utils.target_audit import log_target_counts

        log_target_counts(p_reports, h_reports)
    except Exception as audit_e:
        print(f"[WARNING]: Target audit log failed: {audit_e}")

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

    try:
        from utils.dqi import persist_dqi_history
        persist_dqi_history(
            team_reports,
            config.REPORTS_DIR,
            pitchers=p_reports,
        )
    except Exception as dqi_e:
        print(f"[WARNING]: DQI history persist failed: {dqi_e}")

def _get_pitcher_alpha(p_analyzer, snapshot_path, opening_lines_path, splits_data, props_data, rosters, weather_fetcher, umpire_fetcher, movement_data=None, previous_results=None):
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
        movement_data=movement_data,
        previous_results=previous_results
    )
    
    # OMEGA v4.5: Component Translation
    cache_path = os.path.join(config.DATA_DIR, "statcast_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            pass
    for report in p_reports:
        res = report.get('alpha_score', {})
        report['pitcher'] = (report.get('pitcher') or 'TBD').title()
        
        # Resolve throw hand
        pitcher_norm = normalize_player_name(report['pitcher'])
        p_profile = cache.get(pitcher_norm, {})
        report['pitch_hand'] = p_profile.get("pitch_hand", "R") if p_profile.get("type") == "pitcher" else "R"
        if isinstance(res, dict):
            report['alpha_score'] = res.get('final', 0)
            report['physics_score'] = res.get('physics', 0)
            report['physics_talent'] = res.get('physics_talent', 0)
            report['market_score'] = res.get('market', 0)
            report['is_trap'] = res.get('is_trap', False)
            report['is_coors'] = res.get('is_coors', False)
        else:
            report['alpha_score'] = float(res or 0)
            report['physics_score'] = report.get('physics_score', 0)
            report['physics_talent'] = report.get('physics_talent', 0)
            report['market_score'] = report.get('market_score', 0)
        report['siera'] = report.get('siera', 4.10)
        report['is_paradox'] = False
        report['is_hazard'] = False
        report['is_low_ceiling'] = False
        report['is_sharp'] = report.get('is_sharp', False)
        report['is_whale'] = report.get('is_whale', False)
        report['is_shark'] = report.get('is_shark', False)
        report['is_home'] = report.get('is_home', False)
        report['side'] = report.get('side', 'away')
    
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
            report['alpha_score'] = round(report['alpha_score'] * 1.00, 1) # Removed visibility boost for debuts
        else:
            report['is_debut'] = False

        # Deduplication
        if report['pitcher'] == "TBD":
            cleaned_p_reports.append(report)
        elif report['pitcher'] not in seen_pitchers:
            seen_pitchers.add(report['pitcher'])
            cleaned_p_reports.append(report)
            
    cleaned_p_reports.sort(key=lambda x: x['alpha_score'], reverse=True)
    from utils.prop_juice import apply_pitcher_target_caps

    apply_pitcher_target_caps(cleaned_p_reports)
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
    # HAZARD: only top-3 raw offensive teams on the slate (0.335 caught ~half the league)
    sorted_by_xwoba = sorted(
        team_reports,
        key=lambda x: float(x.get('team_xwoba', 0) or 0),
        reverse=True,
    )
    elite_power_teams = [
        t['team']
        for t in sorted_by_xwoba[:4]
        if float(t.get('team_xwoba', 0) or 0) >= 0.350
    ]

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

        # 2. Power Hazard Check (Top-3 team xwOBA on slate, min .340 elite floor)
        if p['opponent'] in elite_power_teams:
            p['is_hazard'] = True
            print(f"  - HAZARD: {p['pitcher']} ({p['team']}) flagged for facing elite offense {p['opponent']}")
            
        # 3. K-Ceiling Check (Low K-upside warning only, no cap)
        if p.get('k_line') and float(p['k_line']) <= 4.0:
            p['is_low_ceiling'] = True

    # Re-sort after penalties
    p_reports.sort(key=lambda x: x['alpha_score'], reverse=True)
    return p_reports

def _get_team_reports(snapshot, opening_lines, rosters, p_analyzer, p_integrity_map, bullpen_analyzer, consensus_fetcher, splits_data, umpire_assignments, weather_fetcher, previous_results, totals_data=None, raw_hitters=None, confirmed_lineups=None, projected_lineups=None, matchup_radar=None):
    """STEP 2: Ranking Team Omega (Multiplicative Core)"""
    print(f"\n[STEP 2]: Ranking Team Omega ({len(snapshot.get('odds', []))} games)...")
    
    # Load Statcast Cache for platoon resolution
    cache_path = os.path.join(config.DATA_DIR, "statcast_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cache = json.load(f)
        except Exception:
            pass

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
            
            # Opening Price Lookup (pair_key first — game_id changes across refreshes)
            from utils.opening_lines import _pair_key
            pk = _pair_key(away, home)
            open_data = next((o for o in opening_lines if o.get("pair_key") == pk), {})
            if not open_data:
                open_data = next((o for o in opening_lines if o.get("game_id") == gid), {})
            
            if open_data.get("team_away") == team:
                field_key = "away"
            elif open_data.get("team_home") == team:
                field_key = "home"
            else:
                field_key = "away" if team == away else "home"
            opponent = away if team == home else home
            
            open_ml = open_data.get(f'{field_key}_opening_ml')
            open_total = open_data.get('opening_total')
            
            # Check if game has commenced to prevent live-betting/in-progress odds shifts
            game_started = False
            commence_str = game.get('commence_time')
            if commence_str:
                try:
                    commence_dt = datetime.datetime.strptime(commence_str.replace('Z', ''), "%Y-%m-%dT%H:%M:%S")
                    if datetime.datetime.utcnow() >= commence_dt:
                        game_started = True
                except Exception:
                    pass

            # Try to preserve exact pre-game metrics from disk (latest_results.json)
            prev_team_data = previous_results.get(team)
            has_prev = prev_team_data is not None

            # Delta Calc — always use real opens when available (don't freeze stale 0 moves)
            if open_ml is not None and curr_ml is not None:
                ml_move = calculate_ml_move(open_ml, curr_ml)
            else:
                ml_move = 0.0
            if open_total is not None and curr_total is not None:
                tt_move = curr_total - open_total
            else:
                tt_move = 0.0
            
            # ITT Calc
            prob = p_analyzer._ml_to_prob(curr_ml if curr_ml else -110)
            curr_itt = (curr_total if curr_total else 8.5) * prob
            
            # OMEGA v6.9.2: Location-Aware Park Factors
            # Both teams inherit the environment of the home_team's stadium.
            home_team_for_game = game.get('home_team')
            # OMEGA v13.6: Dampen ballpark factors by 50% to prevent venue bias
            raw_pf = config.PARK_FACTORS.get(home_team_for_game, 1.0)
            park_factor = 1.0 + (raw_pf - 1.0) * 0.5
            print(f"  - Stack: {team} vs {opponent} (bullpen fatigue lookup)...")
            opp_bullpen = bullpen_analyzer.get_fatigue_score(opponent)
            
            # Market Divergence & Signal Detection
            if game_started:
                if has_prev:
                    divergence = prev_team_data.get('divergence', 0)
                    is_shark = prev_team_data.get('is_shark', False)
                    is_whale = prev_team_data.get('is_whale', False)
                    is_sharp = prev_team_data.get('is_sharp', False)
                    is_storm = prev_team_data.get('is_storm', False)
                    is_steam = prev_team_data.get('is_steam', False)
                    # OMEGA v10.5: Protect from in-play live betting odds shifts
                    ml_move = float(prev_team_data.get('ml_move', ml_move))
                    tt_move = float(prev_team_data.get('tt_move', tt_move))
                    curr_itt = float(prev_team_data.get('implied_total', curr_itt))
                else:
                    divergence = 0
                    is_shark = False
                    is_whale = False
                    is_sharp = False
                    is_storm = False
                    is_steam = False
            else:
                divergence = consensus_fetcher.get_divergence(team, splits_data)
                is_shark = consensus_fetcher.detect_shark(team, splits_data, ml_move)
                is_whale = consensus_fetcher.detect_whale(team, splits_data)
                is_sharp = consensus_fetcher.is_sharp_consensus(team, splits_data, ml_move)
                is_storm = (divergence >= 10 and tt_move >= 0.3)
                is_steam = consensus_fetcher.detect_steam(team, splits_data, ml_move)

            # Opponent Physics discovery
            opp_pitcher_physics = 0.0
            opp_pitcher_rep = p_integrity_map.get((gid, opponent))
            if opp_pitcher_rep:
                opp_pitcher_physics = pitcher_physics_0_100(opp_pitcher_rep)
                if opp_pitcher_rep.get('is_trap', False):
                    print(f"  - NEUTRALIZED: {opp_pitcher_rep['pitcher']} matchup physics capped at {opp_pitcher_physics:.0f} (TRAP)")
                    
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
                    rescue_phys = min(100.0, round(physics['bm_score'] * 1.8, 1))
                    opp_pitcher_physics = pitcher_physics_0_100(physics_score=rescue_phys)
                    opp_pitcher_rep = {
                        'pitcher': opp_pitcher_name,
                        'physics_score': round(rescue_phys * 0.45, 1),
                        'csw': physics.get('csw', 0.25),
                        'confidence': physics.get('confidence', 'low')
                    }

            # OMEGA v7.0: Power Concentration Discovery
            team_h = [h for h in (raw_hitters or []) if h['team'] == team]
            confirmed = None
            is_official = False
            for lineup_team, players in (confirmed_lineups or {}).items():
                if team.lower() in lineup_team.lower() or lineup_team.lower() in team.lower():
                    confirmed = players
                    is_official = True
                    break
            
            if not confirmed and projected_lineups:
                for lineup_team, players in projected_lineups.items():
                    if team.lower() in lineup_team.lower() or lineup_team.lower() in team.lower():
                        confirmed = players
                        break
            
            lineup_status = "CONFIRMED" if is_official else "PROJECTED"

            team_xwoba = 0.330
            power_concentration = 0.330
            xwoba_dampened = False

            # OMEGA v15.1: Statcast Lineup Fallback
            # When hitter props unavailable (team not in snapshot — e.g. evening games before DK
            # posts prop lines), compute xwOBA directly from lineup + statcast cache.
            # No DK snapshot needed. Eliminates blanket 0.330 defaults.
            if not team_h and confirmed:
                lineup_players = confirmed if isinstance(confirmed, list) else confirmed.get('lineup', [])
                lineup_xwobas = []
                for player_name in lineup_players[:9]:
                    pnorm = normalize_player_name(player_name)
                    p_data = cache.get(pnorm, {})
                    xw = p_data.get('xwoba')
                    if xw and isinstance(xw, (int, float)) and 0.200 <= float(xw) <= 0.500:
                        lineup_xwobas.append(float(xw))
                if len(lineup_xwobas) >= 3:
                    team_xwoba = round(sum(lineup_xwobas) / len(lineup_xwobas), 3)
                    power_concentration = team_xwoba
                    print(f"  [STATCAST FALLBACK]: {team} xwOBA={team_xwoba:.3f} ({len(lineup_xwobas)}/{len(lineup_players[:9])} players matched)")

            if team_h:
                # Resolve opposing pitcher throw hand
                pitch_hand = "R"
                if opp_pitcher_name and opp_pitcher_name != "TBD":
                    opp_pitcher_norm = normalize_player_name(opp_pitcher_name)
                    p_profile = cache.get(opp_pitcher_norm, {})
                    pitch_hand = p_profile.get("pitch_hand", "R") if p_profile.get("type") == "pitcher" else "R"

                # Apply Platoon Splits to Team Stack xwOBA Calculations
                adjusted_h_list = []
                for h in team_h:
                    hitter_norm = normalize_player_name(h['name'])
                    h_profile = cache.get(hitter_norm, {})
                    
                    platoon_multiplier = compute_platoon_multiplier(
                        h_profile, pitch_hand,
                        hitter_name=h['name'], pitcher_name=opp_pitcher_name,
                        matchup_radar=matchup_radar
                    ) if h_profile else 1.0
                    base_xwoba = h.get('matchup_xwoba', 0.310)
                    adj_xwoba = cap_matchup_xwoba(base_xwoba * platoon_multiplier)
                    adjusted_h_list.append({
                        'name': h['name'],
                        'matchup_xwoba': adj_xwoba
                    })

                # OMEGA v14.0: High-fidelity projected lineup construction
                target_h = []
                lineup_names = []
                if confirmed:
                    lineup_names = confirmed[:9]
                else:
                    # Find all hitters for this team in cache
                    team_hitters = []
                    for pname, pdata in cache.items():
                        if pdata.get('type') == 'hitter' and pdata.get('team'):
                            if team.lower() in pdata.get('team', '').lower():
                                team_hitters.append((pname, int(pdata.get('pa', 0) or 0)))
                    # Sort by season PA descending to find Everyday Starters
                    sorted_team_hitters = sorted(team_hitters, key=lambda x: x[1], reverse=True)
                    lineup_names = [p[0].title() for p in sorted_team_hitters[:9]]
                    
                    # Fallback to adjusted_h_list if cache is empty or incomplete
                    if len(lineup_names) < 9:
                        for h in adjusted_h_list:
                            hname = h['name']
                            if hname not in lineup_names and len(lineup_names) < 9:
                                lineup_names.append(hname)

                # Now compile target_h using the 9 lineup spots
                for p in lineup_names:
                    pnorm = normalize_player_name(p)
                    # Check if player has props in adjusted_h_list
                    found_h = next((h for h in adjusted_h_list if normalize_player_name(h['name']) == pnorm), None)
                    if found_h:
                        target_h.append(found_h)
                    else:
                        # Backfill from statcast cache
                        p_profile = cache.get(pnorm, {})
                        platoon_multiplier = compute_platoon_multiplier(
                            p_profile, pitch_hand,
                            hitter_name=p, pitcher_name=opp_pitcher_name,
                            matchup_radar=matchup_radar
                        ) if p_profile else 1.0
                        
                        base_xwoba = p_profile.get('xwoba') if p_profile else None
                        if not base_xwoba or not (0.200 <= float(base_xwoba) <= 0.500):
                            woba_val = p_profile.get("woba") if p_profile else None
                            ops_val = p_profile.get("ops", 0.0) if p_profile else 0.0
                            from utils.xwoba_estimates import woba_proxy_to_xwoba
                            base_xwoba = woba_proxy_to_xwoba(woba_val, ops_val)
                            
                        adj_xwoba = cap_matchup_xwoba(base_xwoba * platoon_multiplier)
                        target_h.append({
                            'name': p,
                            'matchup_xwoba': adj_xwoba
                        })

                # Sort by adjusted matchup_xwoba descending for concentration calculation
                sorted_h = sorted(target_h, key=lambda x: x.get('matchup_xwoba', 0.330), reverse=True)

                # OMEGA: Lineup Spot PA Decay (Batting Order Weighting)
                # OMEGA v14.0 Calibration: Flat weighting prevents over-valuing top-heavy lineups.
                BATTING_ORDER_WEIGHTS = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]
                weighted_xwoba_sum = 0.0
                weight_sum = 0.0
                for idx, h in enumerate(target_h[:9]):
                    weight = BATTING_ORDER_WEIGHTS[idx]
                    weighted_xwoba_sum += h.get('matchup_xwoba', 0.330) * weight
                    weight_sum += weight
                
                fresh_xwoba = (weighted_xwoba_sum / weight_sum) if weight_sum > 0 else 0.330
                from utils.xwoba_stability import resolve_team_xwoba

                team_xwoba, xwoba_dampened = resolve_team_xwoba(
                    {"lineup_status": lineup_status},
                    prev_team_data,
                    fresh_xwoba,
                )
                
                # Weighted Concentration (Top 2: 40%, 3-4: 30%, Rest: 30%)
                top_2 = statistics.mean([h.get('matchup_xwoba', 0.330) for h in sorted_h[:2]])
                next_2 = statistics.mean([h.get('matchup_xwoba', 0.330) for h in sorted_h[2:4]]) if len(sorted_h) >= 4 else top_2
                rest = statistics.mean([h.get('matchup_xwoba', 0.330) for h in sorted_h[4:]]) if len(sorted_h) > 4 else next_2
                power_concentration = (top_2 * 0.4) + (next_2 * 0.3) + (rest * 0.3)
                
                print(f"  - Calculated {team} Platoon-Adjusted xwOBA: {team_xwoba:.3f} | Conc: {power_concentration:.3f} ({lineup_status})")

            from engine.sharps_weighting import SharpsWeighting
            sharps_weighting = SharpsWeighting()
            
            # Confidence and Leash Discovery
            opp_confidence = opp_pitcher_rep.get('confidence', 'low') if opp_pitcher_rep else 'low'
            opp_outs = opp_pitcher_rep.get('outs_line', 15.5) if opp_pitcher_rep else 15.5
            
            # Calculate is_pitch_alignment
            is_pitch_alignment = False
            try:
                pitcher_data = matchup_radar.data.get('pitchers', {}).get(normalize_player_name(opp_pitcher_name))
                if pitcher_data:
                    weapons = [ptype for ptype, usage in pitcher_data.items() if usage >= 25.0]
                    if weapons and len(target_h) > 0:
                        aligned_hitters = 0
                        for h in target_h:
                            hname = h.get('name')
                            hitter_data = matchup_radar.data.get('hitters', {}).get(normalize_player_name(hname))
                            if hitter_data:
                                is_aligned = False
                                for ptype in weapons:
                                    h_stat = hitter_data.get(ptype, 0.0)
                                    l_avg = matchup_radar.data.get('league_avg', {}).get(ptype, 0.300)
                                    if h_stat > l_avg:
                                        is_aligned = True
                                        break
                                if is_aligned:
                                    aligned_hitters += 1
                        
                        alignment_rate = aligned_hitters / len(target_h)
                        is_pitch_alignment = alignment_rate >= 0.60
            except Exception:
                pass

            # Calculate is_anti_chalk_smash (OMEGA v12.1.3: Align strictly with Blue/Red cockpit SP badge tiers)
            is_anti_chalk_smash = False
            opp_sp_trap = False
            try:
                opp_sp_trap = opp_pitcher_rep.get('is_trap', False) if opp_pitcher_rep else False
                if curr_itt >= 4.5 and opp_pitcher_physics >= 50.0:
                    opp_sp_cold = (opp_pitcher_rep.get('form_status') == 'COLD') if opp_pitcher_rep else False
                    opp_sp_fade = (float(opp_pitcher_rep.get('divergence', 0) or 0) <= -20.0) if opp_pitcher_rep else False
                    
                    opp_sp_alpha = 90
                    if opp_pitcher_rep:
                        alpha = opp_pitcher_rep.get('alpha_score', 0)
                        opp_sp_alpha = alpha.get('final', 0) if isinstance(alpha, dict) else alpha
                    
                    if opp_sp_trap or opp_sp_cold or opp_sp_fade or opp_sp_alpha < 75:
                        is_anti_chalk_smash = True
            except Exception:
                pass

            
            # OMEGA v10.2: BURST — star-heavy power + targetable SP or cooked pen / short leash
            is_burst, burst_conc_gap = evaluate_burst_signal(
                power_concentration,
                team_xwoba,
                opp_bullpen['score'],
                float(opp_outs),
                opp_pitcher_physics,
            )
            
            opp_walks_line = opp_pitcher_rep.get('walks_line') if opp_pitcher_rep else None
            opp_walks_odds = opp_pitcher_rep.get('walks_odds') if opp_pitcher_rep else None
            opp_er_line = opp_pitcher_rep.get('er_line') if opp_pitcher_rep else None
            opp_er_odds = opp_pitcher_rep.get('er_odds') if opp_pitcher_rep else None

            # Calculate consolidated parameters before calling engine
            ump_data = umpire_assignments.get(home, {"factor": 1.0, "name": "Unknown"})
            weather_data = weather_fetcher.get_alpha_modifier(home)
            umpire_factor = float(ump_data.get('factor', 1.0) or 1.0)
            weather_boost = float(weather_data.get('boost', 0.0) or 0.0)

            opp_pitcher_alpha = 0.0
            if opp_pitcher_rep:
                alpha = opp_pitcher_rep.get('alpha_score', 0)
                opp_pitcher_alpha = alpha.get('final', 0) if isinstance(alpha, dict) else alpha

            is_opp_debut = False
            if opp_pitcher_rep and opp_pitcher_rep.get('is_debut', False):
                is_opp_debut = True

            under_divergence = 0
            over_divergence = 0
            total_signal = ""
            if totals_data:
                def get_clean_team_key(team_name):
                    t_up = team_name.upper()
                    if "WHITE SOX" in t_up: return "WHITE SOX"
                    if "RED SOX" in t_up: return "RED SOX"
                    return team_name.split()[-1].upper()
                
                home_key = get_clean_team_key(home)
                away_key = get_clean_team_key(away)
                for gk, gv in totals_data.items():
                    gk_up = gk.upper()
                    if home_key in gk_up and away_key in gk_up:
                        over_divergence = gv.get('over_divergence', 0)
                        under_divergence = gv.get('under_divergence', 0)
                        
                        if over_divergence >= 8:
                            total_signal = f"📈 O-DIV +{over_divergence}"
                        elif under_divergence >= 8:
                            total_signal = f"📉 U-DIV +{under_divergence}"
                        elif over_divergence >= 4:
                            total_signal = f"↑ OVER {gv.get('over_money', '')}%$"
                        break

            is_sneaky = evaluate_sneaky_stack(
                curr_itt,
                team_xwoba,
                float(opp_outs),
                is_opp_debut,
                opp_bullpen['score'],
                opp_bullpen['is_gassed'],
                opp_bullpen.get('is_fatigued', False)
            )

            res = sharps_weighting.calculate_stack_score(
                team, ml_move, tt_move, curr_itt=curr_itt, team_xwoba=team_xwoba,
                power_concentration=power_concentration,
                park_factor=park_factor, bullpen_fatigue=opp_bullpen['score'],
                divergence=divergence, is_whale=is_whale, is_sharp=is_sharp,
                is_storm=is_storm, is_shark=is_shark, is_steam=is_steam,
                opp_pitcher_physics=opp_pitcher_physics,
                confidence=opp_confidence, pitcher_outs=float(opp_outs),
                implied_total=curr_itt, is_burst=is_burst, opponent=opponent,
                is_anti_chalk_smash=is_anti_chalk_smash, is_pitch_alignment=is_pitch_alignment,
                opp_pitcher_trap=opp_sp_trap,
                opp_pitcher_name=opp_pitcher_rep.get('pitcher') if opp_pitcher_rep else None,
                opp_walks_line=opp_walks_line,
                opp_walks_odds=opp_walks_odds,
                opp_er_line=opp_er_line,
                opp_er_odds=opp_er_odds,
                umpire_factor=umpire_factor,
                weather_boost=weather_boost,
                opp_pitcher_alpha=opp_pitcher_alpha,
                is_opp_debut=is_opp_debut,
                over_divergence=over_divergence,
                under_divergence=under_divergence,
                is_sneaky=is_sneaky
            )
            
            if game_started and has_prev:
                final_stack_score = prev_team_data.get('stack_score', 50.0)
                stack_score_raw = prev_team_data.get('stack_score_raw')
                trend = prev_team_data.get('trend', 'STABLE')
                total_signal = prev_team_data.get('total_signal', '')
                is_opp_debut = prev_team_data.get('is_opp_debut', False)
                is_sneaky = prev_team_data.get('is_sneaky', False)
            else:
                final_stack_score = res['final']
                stack_score_raw = res.get('final_raw', final_stack_score)
                
                # Trend Analysis (OMEGA v6.3: Velocity-Gated Momentum)
                trend = "STABLE"
                prev_div = previous_results.get(team, {}).get('divergence')
                if prev_div is not None:
                    delta = divergence - prev_div
                    if delta <= -3.0 and divergence <= -5:
                        trend = "FADING"
            
            # Print debut boost if active inside the engine to preserve logs
            if is_opp_debut and not (game_started and has_prev):
                print(f"  - DEBUT BOOST: Applied +10% stack multiplier vs. debut pitcher {opp_pitcher_name}")

            # OMEGA v10.1: Physics Override Detection
            # When our lineup's PHY beats the opponent's PHY by 10+ pts but the market
            # (stack score) ranks them much lower, flag a potential market mispricing.
            opp_physics = opp_pitcher_physics if opp_pitcher_physics else 0
            is_physics_override = (
                res['physics_raw'] > opp_physics + 6.0 and
                res['physics_raw'] > 40.0 and
                final_stack_score < 85.0
            )



            # OMEGA v12.0: Multi-Factor Slate Momentum Index (MSMI)
            # Compare rolling K rate and rolling OPS vs season rates across confirmed lineup hitters.
            rolling_k_delta = 0.0
            rolling_ops_delta = 0.0
            is_cold_streak_msmi = False
            is_hot_run_msmi = False
            is_cold_streak = False
            
            try:
                cache_path = os.path.join(config.DATA_DIR, 'statcast_cache.json')
                if os.path.exists(cache_path):
                    with open(cache_path, 'r', encoding='utf-8') as fc:
                        hitter_cache = json.load(fc)
                    team_season_k_rates = []
                    team_rolling_k_rates = []
                    team_season_ops_list = []
                    team_rolling_ops_list = []
                    for hname, hdata in hitter_cache.items():
                        if hdata.get('type') == 'hitter' and hdata.get('team') == team:
                            pa = hdata.get('pa', 0)
                            k = hdata.get('k', 0)
                            r_pa = hdata.get('rolling_pa', 0)
                            r_k = hdata.get('rolling_k', 0)
                            s_ops = hdata.get('ops', 0.0)
                            r_ops = hdata.get('rolling_ops', 0.0)
                            if pa >= 20:
                                team_season_k_rates.append(k / pa)
                                team_season_ops_list.append(s_ops)
                            if r_pa >= 5:
                                team_rolling_k_rates.append(r_k / r_pa)
                                team_rolling_ops_list.append(r_ops)
                    
                    if team_season_k_rates and team_rolling_k_rates:
                        avg_season_k = sum(team_season_k_rates) / len(team_season_k_rates)
                        avg_rolling_k = sum(team_rolling_k_rates) / len(team_rolling_k_rates)
                        if avg_season_k > 0:
                            rolling_k_delta = round((avg_rolling_k - avg_season_k) / avg_season_k * 100, 1)
                            
                    if team_season_ops_list and team_rolling_ops_list:
                        avg_season_ops = sum(team_season_ops_list) / len(team_season_ops_list)
                        avg_rolling_ops = sum(team_rolling_ops_list) / len(team_rolling_ops_list)
                        if avg_season_ops > 0:
                            rolling_ops_delta = round((avg_rolling_ops - avg_season_ops) / avg_season_ops * 100, 1)
                            
                    # OMEGA v12.1.1: Calibrated slate-wide balance (highly selective AND trigger)
                    is_cold_streak_msmi = rolling_k_delta >= 12.0 and rolling_ops_delta <= -12.0
                    is_hot_run_msmi = rolling_ops_delta >= 12.0 and rolling_k_delta <= -10.0

                    is_cold_streak = is_cold_streak_msmi
            except Exception:
                pass


            team_row = {
                'team': team, 'opponent': opponent, 'opp_pitcher': opp_pitcher_name,
                'lineup_status': lineup_status,
                'ml_move': ml_move, 'tt_move': tt_move,
                'stack_score': final_stack_score,
                'stack_score_raw': round(stack_score_raw, 1) if (stack_score_raw is not None and stack_score_raw > 150.0) else None,
                'physics_score': xwoba_to_phy_score(res.get('team_xwoba', team_xwoba)),
                'market_score': res.get('market_raw', res['market']),
                'market_raw': res.get('market_raw'),
                'team_xwoba': team_xwoba,
                'team_xwoba_locked': team_xwoba if lineup_status == 'CONFIRMED' else None,
                'team_xwoba_dampened': xwoba_dampened if team_h else False,
                'power_concentration': res.get('power_concentration', power_concentration),
                'bullpen_boost': res.get('bullpen_boost', 0),
                'vulnerability': res.get('vulnerability', 0),
                'weather_label': weather_data['label'],
                'umpire_name': ump_data.get('name', 'Unknown'),
                'umpire_factor': ump_data.get('factor', 1.0),  # v10.1: Exposed for hitter/pitcher label
                'bullpen_fatigue': opp_bullpen['score'], 'is_gassed': opp_bullpen['is_gassed'],
                'is_fatigued': opp_bullpen.get('is_fatigued', False), 'is_shark': is_shark,
                'is_whale': is_whale, 'is_sharp': is_sharp, 'is_storm': is_storm,
                'is_steam': is_steam, 'divergence': divergence, 'trend': trend,
                'confidence': res.get('confidence', 'low'),
                'is_burst': is_burst,
                'burst_conc_gap': burst_conc_gap,
                'is_opp_debut': is_opp_debut,
                'is_trap': res.get('is_trap', False),
                'opp_pitcher_physics': opp_pitcher_physics,
                'opp_pitcher_outs': float(opp_outs),
                'implied_total': round(curr_itt, 2),
                'total_signal': total_signal,
                'is_physics_override': is_physics_override,  # v10.1: PHY beats market signal
                'is_cold_streak': is_cold_streak,            # v10.1: Rolling K% elevated 25%+
                'rolling_k_delta': rolling_k_delta,           # v10.1: % above season K rate
                'rolling_ops_delta': rolling_ops_delta,
                'is_cold_streak_msmi': is_cold_streak_msmi,
                'is_hot_run_msmi': is_hot_run_msmi,
                'is_anti_chalk_smash': is_anti_chalk_smash,
                'is_pitch_alignment': is_pitch_alignment,
                'is_fade_risk': res.get('is_fade_risk', False),
                'is_sneaky': is_sneaky
            }
            apply_team_blind_spot(team_row)
            apply_signal_exclusions(team_row)
            team_reports.append(team_row)

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

def _get_hitter_alpha(h_prop_analyzer, snapshot_path, team_reports, sharps_weighting, matchup_radar, raw_hitters=None, pitcher_reports=None):
    """STEP 3: Ranking Hitter Alpha"""
    print("\n[STEP 3]: Ranking Hitter Alpha...")
    if raw_hitters is None:
        raw_hitters = h_prop_analyzer.extract_top_hitters(snapshot_path)
    
    from utils.xwoba_estimates import ops_to_xwoba, woba_proxy_to_xwoba, cap_matchup_xwoba
    
    # OMEGA v9.5 splits update: Load Cache for splits & Handedness matching
    cache_path = os.path.join(config.DATA_DIR, "statcast_cache.json")
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            print(f"[SPLITS]: Loaded {len(cache)} profiles for dynamic matchup resolution.")
        except Exception as e:
            print(f"[WARNING]: Could not load cache for splits: {e}")
            
    # Load platoon split cache for NPAS
    platoon_path = os.path.join(config.DATA_DIR, "platoon_cache.json")
    platoon_cache = {}
    if os.path.exists(platoon_path):
        try:
            with open(platoon_path, 'r', encoding='utf-8') as pf:
                platoon_cache = json.load(pf)
            print(f"[NPAS]: Loaded Platoon Cache with {len(platoon_cache.get('pitchers', {}))} pitchers splits.")
        except Exception as e:
            print(f"[WARNING]: Could not load platoon cache: {e}")

    h_reports = []
    pitcher_csw_map = {}
    for pr in (pitcher_reports or []):
        pitcher_csw_map[normalize_player_name(pr.get('pitcher', ''))] = float(pr.get('csw', 0.25) or 0.25)

    for h in raw_hitters:
        team_score = 50.0
        team_data = next((tr for tr in team_reports if tr['team'] == h['team']), None)
        if team_data: team_score = team_data['stack_score']
        
        venue_team = next((tr['team'] if tr.get('is_home') else tr['opponent'] 
                          for tr in team_reports if tr['team'] == h['team']), h['team'])
        # OMEGA v13.6: Dampen ballpark factors by 50% to prevent venue bias
        raw_pf = config.PARK_FACTORS.get(venue_team, 1.0)
        park_factor = 1.0 + (raw_pf - 1.0) * 0.5
        
        # Momentum & Vision
        is_hot = False
        vision_boost = 1.0
        mom = h_prop_analyzer.statcast.get_player_momentum(h['name'])
        smash_factor = False
        if mom:
            if mom.get('ops', 0) > 0.900: is_hot = True
            if mom.get('s_k_rate', 0) > 0 and mom.get('r_k_rate', 0) < (mom.get('s_k_rate', 0) * 0.8):
                vision_boost = 1.10
        
        # Protection synergy
        protection_boost = 1.05 if (team_data and team_data.get('stack_score', 0) >= 75) else 1.0

        # OMEGA v7.7: Matchup Radar Synergy
        opp_pitcher = team_data['opp_pitcher'] if team_data else "TBD"
        matchup_radar_boost = matchup_radar.get_matchup_boost(h['name'], opp_pitcher)

        # OMEGA v9.5 splits matching: Resolve opposing pitcher hand and hitter splits
        opp_pitcher_norm = normalize_player_name(opp_pitcher)
        p_profile = cache.get(opp_pitcher_norm, {})
        pitch_hand = p_profile.get("pitch_hand", "R") if p_profile.get("type") == "pitcher" else "R"
        
        hitter_norm = normalize_player_name(h['name'])
        h_profile = cache.get(hitter_norm, {})
        opp_csw = pitcher_csw_map.get(opp_pitcher_norm) or float(p_profile.get('csw', 0) or 0)

        # Individual Multi-Factor Slate Momentum Index (MSMI)
        h_rolling_k_delta = 0.0
        h_rolling_ops_delta = 0.0
        h_is_cold_streak_msmi = False
        h_is_hot_run_msmi = False
        
        if h_profile:
            pa = h_profile.get('pa', 0)
            k = h_profile.get('k', 0)
            r_pa = h_profile.get('rolling_pa', 0)
            r_k = h_profile.get('rolling_k', 0)
            s_ops = h_profile.get('ops', 0.0)
            r_ops = h_profile.get('rolling_ops', 0.0)
            
            season_k_rate = k / pa if pa >= 20 else 0.0
            rolling_k_rate = r_k / r_pa if r_pa >= 5 else 0.0
            
            if season_k_rate > 0:
                h_rolling_k_delta = round((rolling_k_rate - season_k_rate) / season_k_rate * 100, 1)
            if s_ops > 0:
                h_rolling_ops_delta = round((r_ops - s_ops) / s_ops * 100, 1)
                
            # OMEGA v13.9: Batted ball profile (barrel % + hard hit %)
            barrel_pct  = float(h_profile.get('barrel_pct', 0) or 0)
            hard_hit_pct = float(h_profile.get('hard_hit_pct', 0) or 0)

            # OMEGA v12.1.1: Calibrated slate-wide balance (highly selective AND trigger)
            h_is_cold_streak_msmi = h_rolling_k_delta >= 12.0 and h_rolling_ops_delta <= -12.0
            h_is_hot_run_msmi = h_rolling_ops_delta >= 12.0 and h_rolling_k_delta <= -10.0

        # Dynamic Platoon splits via Matchup DNA or hand-based NPAS
        platoon_multiplier = 1.0
        try:
            platoon_multiplier = compute_platoon_multiplier(
                h_profile, pitch_hand,
                hitter_name=h['name'], pitcher_name=opp_pitcher,
                matchup_radar=matchup_radar
            ) if h_profile else 1.0
        except Exception:
            pass

        # Adjust hitter's matchup_xwoba by platoon_multiplier
        baseline_xwoba = float(h.get('matchup_xwoba', 0.330) or 0.330)
        matchup_xwoba_npas = cap_matchup_xwoba(baseline_xwoba * platoon_multiplier)
        NPAS_xwOBA = matchup_xwoba_npas - baseline_xwoba

        # OMEGA v15.0: Smash gate tightened (grid sweep: xwOBA>=0.360 AND plat>=1.03 = +7.7pp over baseline)
        # Old: matchup_xwoba_npas >= 0.370 only. New: require genuine platoon advantage too.
        smash_factor = (matchup_xwoba_npas >= 0.360 and platoon_multiplier >= 1.03)

        # Check if this hitter has a Matchup DNA edge
        is_hitter_pitch_alignment = False
        if matchup_radar and opp_pitcher and opp_pitcher != "TBD":
            p_name = normalize_player_name(opp_pitcher)
            h_name = normalize_player_name(h['name'])
            if p_name in matchup_radar.data.get('pitchers', {}) and h_name in matchup_radar.data.get('hitters', {}):
                if platoon_multiplier > 1.0:
                    is_hitter_pitch_alignment = True

        res = sharps_weighting.calculate_individual_hitter_score(
            h['name'], team_score, matchup_xwoba_npas, h.get('ahr_price', 400),
            park_factor=park_factor, is_target=h.get('is_juiced_target', False),
            is_speed_target=h.get('is_speed_target', False), is_hot=is_hot,
            vision_boost=vision_boost, protection_boost=protection_boost,
            matchup_radar_boost=matchup_radar_boost, opp_csw=opp_csw,
            pitch_hand=pitch_hand, hitter_splits=h_profile, smash_factor=smash_factor,
            pitcher_name=opp_pitcher, matchup_radar=matchup_radar,
            walks_line=h.get('walks_line'), walks_price=h.get('walks_price'),
            strikeouts_line=h.get('strikeouts_line'), strikeouts_price=h.get('strikeouts_price'),
            runs_g_rbi_line=h.get('runs_g_rbi_line'), runs_g_rbi_price=h.get('runs_g_rbi_price'),
            hard_hit_pct=hard_hit_pct,
            barrel_pct=barrel_pct,
            hits_line=h.get('hits_line'),
            hits_price=h.get('hits_price')
        )

        h_reports.append({
            'name': h['name'].title(), 'team': h['team'], 
            'opponent': team_data['opponent'] if team_data else "TBD",
            'opp_pitcher': (team_data.get('opp_pitcher') or 'TBD').title() if team_data else "TBD",
            'player_score': res.get('solo_score', res['final']),
            'stack_adjusted_score': res['final'],
            'physics_score': res.get('physics_component', res['physics']),
            'market_score': res.get('market', 0),
            'matchup_xwoba': res.get('matchup_xwoba', h.get('matchup_xwoba', 0.330)),
            'ahr_price': h.get('ahr_price', 400),
            'hits_line': h.get('hits_line', '-'),
            'hits_price': h.get('hits_price', 0),
            'tb_line': h.get('tb_line', '-'),
            'tb_price': h.get('tb_price', 0),
            'bullpen_fatigue': team_data['bullpen_fatigue'] if team_data else 0,
            'is_hot': is_hot, 'is_juiced_target': h.get('is_juiced_target', False),
            'is_prop_juice': h.get('is_prop_juice', False),
            'is_speed_target': h.get('is_speed_target', False),
            'is_pitch_alignment': is_hitter_pitch_alignment,
            'walks_boost': res.get('walks_boost', False),
            'strikeouts_penalty': res.get('strikeouts_penalty', False),
            'is_anti_chalk_smash': team_data.get('is_anti_chalk_smash', False) if team_data else False,
            'platoon_multiplier': platoon_multiplier,
            'platoon_label': res.get('platoon_label', 'Neutral'),
            'bat_side': h_profile.get('bat_side', 'R') if h_profile.get('type') == 'hitter' else 'R',
            'pitch_hand': pitch_hand,
            'smash_factor': smash_factor,
            'NPAS_xwOBA': round(NPAS_xwOBA, 3),
            'is_cold_streak_msmi': h_is_cold_streak_msmi,
            'is_hot_run_msmi': h_is_hot_run_msmi,
            'barrel_pct': barrel_pct,
            'hard_hit_pct': hard_hit_pct
        })

    # Calibrate dynamic splits (platoon_label) slate-wide (OMEGA v12.1: Tightened, highly selective GPP criteria)
    if h_reports:
        # Sort by NPAS_xwOBA descending
        h_reports_sorted = sorted(h_reports, key=lambda x: x.get('NPAS_xwOBA', 0.0), reverse=True)
        n_hitters = len(h_reports_sorted)
        # Create a lookup mapping from hitter name to its calibrated splits details
        calibrated_labels = {}
        for idx, hr in enumerate(h_reports_sorted):
            percentile = idx / n_hitters if n_hitters > 0 else 0.5
            npas = hr.get('NPAS_xwOBA', 0.0)
            
            # Calibrate label with strict absolute thresholds + percentiles (OMEGA v12.4: Tightened for elite selectivity)
            if percentile <= 0.05 and npas >= 0.025:
                label = "ELITE PLATOON"
            elif percentile <= 0.15 and npas >= 0.015:
                label = "STRONG EDGE"
            elif npas <= -0.015 or (percentile >= 0.90 and npas <= -0.010):
                label = "PLATOON TRAP"
            else:
                label = "NEUTRAL"
                
            calibrated_labels[hr['name']] = label


        # Apply the calibrated label back to h_reports
        for hr in h_reports:
            hr['platoon_label'] = calibrated_labels.get(hr['name'], hr['platoon_label'])

        # OMEGA v13.5.1: Calculate hitter confidence using the calibrated splits label
        from utils.hitter_confidence import score_hitter_confidence
        for hr in h_reports:
            opp_pitcher_norm = normalize_player_name(hr['opp_pitcher'])
            opp_pitcher_row = next((pr for pr in (pitcher_reports or []) if normalize_player_name(pr.get('pitcher', '')) == opp_pitcher_norm), None)
            team_data = next((tr for tr in team_reports if tr['team'] == hr['team']), None)
            conf, reasons = score_hitter_confidence(hr, team_data, opp_pitcher_row)
            hr['attack_conf'] = conf
            hr['attack_reasons'] = reasons

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
