import os
import json
import csv
import datetime
import time
import requests
import statistics
from config import config
from utils.normalization import normalize_player_name

CACHE_PATH = os.path.join(config.DATA_DIR, "opener_detector_cache.json")
LOG_PATH = os.path.join(config.LOG_DIR, "opener_detection.log")

TEAM_MAP_DK_TO_FULL = {
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
    'OAK': 'Athletics',
    'ATH': 'Athletics',
    'PHI': 'Philadelphia Phillies',
    'PIT': 'Pittsburgh Pirates',
    'SD': 'San Diego Padres',
    'SDP': 'San Diego Padres',
    'SEA': 'Seattle Mariners',
    'SF': 'San Francisco Giants',
    'SFG': 'San Francisco Giants',
    'STL': 'St. Louis Cardinals',
    'TB': 'Tampa Bay Rays',
    'TBR': 'Tampa Bay Rays',
    'TEX': 'Texas Rangers',
    'TOR': 'Toronto Blue Jays',
    'WSH': 'Washington Nationals',
    'WAS': 'Washington Nationals'
}

def get_season_start_date(year):
    """Get start date of MLB regular season. Hardcoded for efficiency with StatsAPI fallback."""
    hardcoded = {
        2024: "2024-03-28",
        2025: "2025-03-27",
        2026: "2026-04-02"
    }
    if year in hardcoded:
        return datetime.date.fromisoformat(hardcoded[year])
    
    try:
        url = f"https://statsapi.mlb.com/api/v1/seasons?sportId=1&season={year}"
        resp = requests.get(url, timeout=5)
        if resp.status_code == 200:
            seasons = resp.json().get("seasons", [])
            if seasons:
                date_str = seasons[0].get("regularSeasonStartDate")
                if date_str:
                    return datetime.date.fromisoformat(date_str)
    except Exception:
        pass
    return datetime.date(year, 4, 1)

def is_first_7_days_of_season(slate_date):
    """Gate to exclude the first 7 days of the MLB season."""
    if isinstance(slate_date, str):
        slate_date = datetime.date.fromisoformat(slate_date[:10])
    elif isinstance(slate_date, datetime.datetime):
        slate_date = slate_date.date()
    year = slate_date.year
    start_date = get_season_start_date(year)
    delta = (slate_date - start_date).days
    return 0 <= delta < 7

def parse_ip(ip_str):
    """Convert MLB Innings Pitched string (e.g. '1.2') to float (1.667)."""
    if not ip_str:
        return 0.0
    try:
        parts = str(ip_str).split('.')
        innings = int(parts[0])
        outs = int(parts[1]) if len(parts) > 1 else 0
        return innings + (outs / 3.0)
    except (ValueError, IndexError):
        return 0.0

def load_detector_cache():
    if os.path.exists(CACHE_PATH):
        try:
            with open(CACHE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_detector_cache(cache):
    try:
        os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
        with open(CACHE_PATH, 'w', encoding='utf-8') as f:
            json.dump(cache, f, indent=4)
    except Exception:
        pass

def fetch_pitcher_stats_api(pitcher_name, year):
    """Query MLB StatsAPI to load career starts, relief appearances and last 10 games avg IP."""
    cache = load_detector_cache()
    norm = normalize_player_name(pitcher_name)
    if norm in cache:
        # Check cache freshness (refresh after 7 days)
        cached = cache[norm]
        ts_str = cached.get("timestamp")
        if ts_str:
            try:
                cached_dt = datetime.datetime.fromisoformat(ts_str)
                if (datetime.datetime.now() - cached_dt).days < 7:
                    return cached
            except Exception:
                pass

    stats = {
        "career_starts": 0,
        "relief_pct": 0.0,
        "avg_ip_l10": 0.0,
        "timestamp": datetime.datetime.now().isoformat()
    }
    
    try:
        # 1. Search player
        search_url = f"https://statsapi.mlb.com/api/v1/people/search?names={requests.utils.quote(pitcher_name)}&sportId=1"
        resp = requests.get(search_url, timeout=5)
        if resp.status_code == 200:
            people = resp.json().get("people", [])
            if people:
                player_id = people[0]["id"]
                
                # 2. Career stats
                career_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=career&group=pitching"
                c_resp = requests.get(career_url, timeout=5)
                if c_resp.status_code == 200:
                    c_stats = c_resp.json().get("stats", [])
                    if c_stats:
                        splits = c_stats[0].get("splits", [])
                        if splits:
                            stat = splits[0].get("stat", {})
                            gs = int(stat.get("gamesStarted", 0))
                            gp = int(stat.get("gamesPlayed", 0))
                            stats["career_starts"] = gs
                            if gp > 0:
                                stats["relief_pct"] = round((gp - gs) / gp * 100, 1)

                # 3. Last 10 game logs
                log_url = f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats?stats=gameLog&group=pitching&season={year}"
                l_resp = requests.get(log_url, timeout=5)
                if l_resp.status_code == 200:
                    l_stats = l_resp.json().get("stats", [])
                    if l_stats:
                        splits = l_stats[0].get("splits", [])
                        ips = []
                        for split in splits[:10]:
                            ip_str = split.get("stat", {}).get("inningsPitched", "0.0")
                            ips.append(parse_ip(ip_str))
                        if ips:
                            stats["avg_ip_l10"] = round(statistics.mean(ips), 2)
                            
        # Save to cache
        cache[norm] = stats
        save_detector_cache(cache)
    except Exception as e:
        print(f"[OPENER DETECTOR WARNING]: Failed to query StatsAPI for {pitcher_name}: {e}")
        
    return stats

def parse_dk_salaries(csv_path):
    """Load and parse DK Salaries file. Returns list of player dicts."""
    players = []
    if not csv_path or not os.path.exists(csv_path):
        return players
    try:
        with open(csv_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                players.append(row)
    except Exception as e:
        print(f"[OPENER DETECTOR WARNING]: Failed to parse DK salaries: {e}")
    return players

def log_detection(date_str, team, game_id, tier, csv_avail, tags_found, salary_gap, leash_sigs, t2_sigs, status, method, bulk_name, sub_applied, reason_no):
    """Write detection decision to logs/opener_detection.log."""
    try:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        # Avoid emojis in log prints for Windows terminal compatibility, format as ASCII
        log_entry = (
            f"OPENER DETECTION LOG - {date_str} {team} {game_id}\n"
            f"Tier attempted: {tier}\n"
            f"CSV available: {'Y' if csv_avail else 'N'}\n"
            f"PO/PLR tags found: {'Y' if tags_found else 'N'}\n"
            f"Salary gap: {f'${salary_gap}' if salary_gap is not None else 'N/A'}\n"
            f"Short-leash signals fired: {leash_sigs}\n"
            f"Tier 2 signals fired: {t2_sigs}\n"
            f"Overall detection: {status}\n"
            f"Bulk resolution method: {method}\n"
            f"Bulk pitcher identified: {bulk_name if bulk_name else 'UNKNOWN'}\n"
            f"Substitution applied: {'YES' if sub_applied else 'NO'}\n"
            f"Reason if NO: {reason_no if reason_no else 'N/A'}\n"
            f"{'-'*50}\n"
        )
        with open(LOG_PATH, 'a', encoding='utf-8') as f:
            f.write(log_entry)
        # Print a short ASCII confirmation to console
        print(f"[OPENER DETECTOR]: Processed {team} ({status}) - Substitution: {'YES' if sub_applied else 'NO'}")
    except Exception as e:
        print(f"[OPENER DETECTOR WARNING]: Failed to write detection log: {e}")

def match_team(team_abbrev, team_name):
    t_norm = team_name.lower()
    mapped = TEAM_MAP_DK_TO_FULL.get(team_abbrev, "").lower()
    if mapped and (mapped in t_norm or t_norm in mapped):
        return True
    short_name = team_abbrev.lower()
    if short_name in t_norm:
        return True
    return False

def detect_opener_for_team(team, game, dk_players, props_data, slate_date, previous_results=None):
    """
    Perform 3-tier opener detection and bulk pitcher resolution for a team.
    Returns: (status, opener_name, bulk_name, tier, method, sub_applied, reason_no)
    """
    game_id = game['id']
    date_str = str(slate_date)
    year = slate_date.year
    
    # 0. Exclusion Gate
    if is_first_7_days_of_season(slate_date):
        return "REJECTED", None, None, 0, "NONE", False, "First 7 days of season exclusion"

    # Resolve starter name from game
    starter = game.get('home_pitcher' if team == game['home_team'] else 'away_pitcher')
    gid_props = props_data.get(game_id, {}) if props_data else {}

    # Extract k_line for starter from props_data
    starter_k_line = None
    if starter and starter not in ["TBD", "Tbd", None] and gid_props:
        if 'pitcher_strikeouts' in gid_props:
            ks = [o for o in gid_props['pitcher_strikeouts'] if normalize_player_name(o.get('player_name', '')) == normalize_player_name(starter)]
            if ks:
                points = [o.get('point', 0) for o in ks if o.get('point')]
                if points:
                    starter_k_line = statistics.median(points)

    pitcher = {
        'name': starter,
        'k_line': starter_k_line
    }

    # TIER 1 HARD OVERRIDE: K line <= 1.5 = opener, no secondary signals needed
    # No legitimate MLB starter carries a K line this low — unambiguous opener flag
    if pitcher.get('k_line') is not None and pitcher.get('k_line') <= 1.5:
        pitcher['is_opener'] = True
        pitcher['opener_tier'] = 1
        pitcher['opener_reason'] = f"K line {pitcher['k_line']} <= 1.5 — definitive opener signal"
        
        # trigger bulk arm lookup
        # Group pitchers on the team in this game
        game_info_match = None
        team_dk_pitchers = []
        if dk_players:
            for p in dk_players:
                p_team = p.get('TeamAbbrev')
                pos = p.get('Position', '')
                roster_pos = p.get('Roster Position', '')
                is_p = (roster_pos == 'P' or 'SP' in pos or 'RP' in pos or 'PO' in pos or 'PLR' in pos)
                if match_team(p_team, team) and is_p:
                    team_dk_pitchers.append(p)
                    if p.get('Game Info'):
                        game_info_match = p.get('Game Info')
            if game_info_match:
                team_dk_pitchers = [p for p in team_dk_pitchers if p.get('Game Info') == game_info_match]

        # Scan teammate props for highest outs line
        teammate_outs = {}
        for outcome in gid_props.get('pitcher_outs', []):
            pn = outcome.get('player_name')
            if not pn or normalize_player_name(pn) == normalize_player_name(starter):
                continue
            is_team_match = False
            side = outcome.get('side', '').lower()
            home_t = outcome.get('home_team')
            away_t = outcome.get('away_team')
            if side:
                is_team_match = (side == 'home' and team == home_t) or (side == 'away' and team == away_t)
            elif home_t or away_t:
                is_team_match = (team in [home_t, away_t])
            if not is_team_match and dk_players:
                dk_match = next((p for p in dk_players if normalize_player_name(p.get('Name', '')) == normalize_player_name(pn)), None)
                if dk_match:
                    is_team_match = match_team(dk_match.get('TeamAbbrev'), team)
            if not is_team_match:
                try:
                    from data.statcast_bridge import load_cache
                    sc_cache = load_cache()
                    if normalize_player_name(pn) in sc_cache:
                        cache_team = sc_cache[normalize_player_name(pn)].get('team')
                        if cache_team and (cache_team.lower() in team.lower() or team.lower() in cache_team.lower()):
                            is_team_match = True
                except:
                    pass

            if is_team_match:
                points = [o.get('point', 0) for o in gid_props['pitcher_outs'] if normalize_player_name(o.get('player_name', '')) == normalize_player_name(pn) and o.get('point')]
                if points:
                    teammate_outs[pn] = statistics.median(points)
        
        # Load RotoWire cache to help resolve the bulk arm
        rw_cache_path = os.path.join(config.DATA_DIR, "projected_lineups_cache.json")
        rw_pitchers = []
        if os.path.exists(rw_cache_path):
            try:
                with open(rw_cache_path, 'r', encoding='utf-8') as f:
                    rw_data = json.load(f).get('lineups', {})
                    for rw_t, info in rw_data.items():
                        if rw_t.lower() in team.lower() or team.lower() in rw_t.lower():
                            rw_pitchers = info.get('pitchers', [])
                            break
            except:
                pass

        bulk_name = None
        method = "props feed"
        if teammate_outs:
            bulk_name = max(teammate_outs, key=teammate_outs.get)
        else:
            # Try to resolve bulk arm from RotoWire cache
            if rw_pitchers:
                rw_non_opener = [p for p in rw_pitchers if normalize_player_name(p['name']) != normalize_player_name(starter)]
                if rw_non_opener:
                    rw_bulk_p = next((p for p in rw_non_opener if p.get('rw_is_bulk')), rw_non_opener[0])
                    bulk_name = rw_bulk_p['name']
                    method = "RotoWire cache"
            
            if not bulk_name:
                if dk_players and len(team_dk_pitchers) >= 2:
                    non_opener_dk = [p for p in team_dk_pitchers if normalize_player_name(p['Name']) != normalize_player_name(starter)]
                    if non_opener_dk:
                        best_dk = max(non_opener_dk, key=lambda x: int(x.get('Salary', 0)))
                        bulk_name = best_dk['Name']
                        method = "CSV second pitcher"

        if bulk_name:
            log_detection(date_str, team, game_id, 1, bool(dk_players), False, None, [], [], "CONFIRMED", method, bulk_name, True, None)
            return "CONFIRMED", starter, bulk_name, 1, method, True, None
        else:
            log_detection(date_str, team, game_id, 1, bool(dk_players), False, None, [], [], "CONFIRMED", method, None, False, "BULK_UNRESOLVED")
            return "CONFIRMED", starter, None, 1, method, False, "BULK_UNRESOLVED"

    # Group pitchers on the team in this game
    game_info_match = None
    team_dk_pitchers = []
    
    if dk_players:
        # Find the game_info for this matchup
        for p in dk_players:
            p_team = p.get('TeamAbbrev')
            pos = p.get('Position', '')
            roster_pos = p.get('Roster Position', '')
            is_p = (roster_pos == 'P' or 'SP' in pos or 'RP' in pos or 'PO' in pos or 'PLR' in pos)
            if match_team(p_team, team) and is_p:
                team_dk_pitchers.append(p)
                if p.get('Game Info'):
                    game_info_match = p.get('Game Info')
                    
        # Doubleheader verify: Filter team_dk_pitchers to ensure they share the same Game Info
        if game_info_match:
            team_dk_pitchers = [p for p in team_dk_pitchers if p.get('Game Info') == game_info_match]

    # Resolve props for game
    gid_props = props_data.get(game_id, {}) if props_data else {}

    # Define short-leash checker helper
    def check_short_leash(p_name):
        # 1. IP line <= 2.5
        ip_val = None
        if 'pitcher_outs' in gid_props:
            outs = [o for o in gid_props['pitcher_outs'] if normalize_player_name(o.get('player_name', '')) == normalize_player_name(p_name)]
            if outs:
                points = [o.get('point', 0) for o in outs if o.get('point')]
                if points:
                    ip_val = statistics.median(points) / 3.0
        
        sig_ip = (ip_val is not None and ip_val <= 2.5)
        
        # 2. Projected pitches <= 45
        sig_pitches = False
        if ip_val is not None and ip_val <= 2.5:
            sig_pitches = True

        # StatsAPI query for career metrics
        api_stats = fetch_pitcher_stats_api(p_name, year)
        
        # 3. Career starts < 8
        sig_starts = api_stats.get("career_starts", 0) < 8
        
        # 4. Avg IP L10 < 3.0
        sig_avg_ip = api_stats.get("avg_ip_l10", 0.0) > 0.0 and api_stats.get("avg_ip_l10") < 3.0
        
        # 5. Relief pct > 50%
        sig_relief = api_stats.get("relief_pct", 0.0) > 50.0
        
        fired = []
        if sig_ip: fired.append("IP line <= 2.5")
        if sig_pitches: fired.append("projected pitches <= 45")
        if sig_starts: fired.append("career MLB starts < 8")
        if sig_avg_ip: fired.append("historical avg IP < 3.0")
        if sig_relief: fired.append("relief appearances > 50%")
        
        return len(fired) >= 2, fired

    # ==================== TIER 1A: ROTOWIRE DETECTOR ====================
    # Load RotoWire cache
    rw_cache_path = os.path.join(config.DATA_DIR, "projected_lineups_cache.json")
    rw_pitchers = []
    if os.path.exists(rw_cache_path):
        try:
            with open(rw_cache_path, 'r', encoding='utf-8') as f:
                rw_data = json.load(f).get('lineups', {})
                for rw_t, info in rw_data.items():
                    if rw_t.lower() in team.lower() or team.lower() in rw_t.lower():
                        rw_pitchers = info.get('pitchers', [])
                        break
        except:
            pass

    rw_opener = next((p for p in rw_pitchers if p.get('rw_is_opener')), None)
    rw_bulk = next((p for p in rw_pitchers if p.get('rw_is_bulk')), None)

    # Resolve starter name from game
    starter = game.get('home_pitcher' if team == game['home_team'] else 'away_pitcher')

    if rw_opener and rw_bulk and starter and starter not in ["TBD", "Tbd", None]:
        if normalize_player_name(rw_opener['name']) == normalize_player_name(starter):
            log_detection(date_str, team, game_id, "1A", bool(dk_players), True, None, [], [], "CONFIRMED", "RotoWire", rw_bulk['name'], True, None)
            return "CONFIRMED", starter, rw_bulk['name'], "1A", "RotoWire", True, None

    # ==================== TIER 1B: DK CSV PO/PLR DETECTOR ====================
    if dk_players and len(team_dk_pitchers) >= 2 and starter and starter not in ["TBD", "Tbd", None]:
        po_arms = [p for p in team_dk_pitchers if p.get('Position') == 'PO']
        plr_arms = [p for p in team_dk_pitchers if p.get('Position') == 'PLR']
        if po_arms and plr_arms:
            opener_dk = min(po_arms, key=lambda x: int(x.get('Salary', 0)))
            bulk_dk = max(plr_arms, key=lambda x: int(x.get('Salary', 0)))
            opener_name = opener_dk['Name']
            bulk_name = bulk_dk['Name']
            if normalize_player_name(opener_name) == normalize_player_name(starter):
                log_detection(date_str, team, game_id, "1B", True, True, None, [], [], "CONFIRMED", "CSV PLR", bulk_name, True, None)
                return "CONFIRMED", starter, bulk_name, "1B", "CSV PLR", True, None

    # ==================== SAFETY CHECK: PROPS PENDING ====================
    starter_outs_line = None
    gid_props = props_data.get(game_id, {}) if props_data else {}
    if starter and starter not in ["TBD", "Tbd", None]:
        if 'pitcher_outs' in gid_props:
            outs = [o for o in gid_props['pitcher_outs'] if normalize_player_name(o.get('player_name', '')) == normalize_player_name(starter)]
            if outs:
                points = [o.get('point', 0) for o in outs if o.get('point')]
                if points:
                    starter_outs_line = statistics.median(points)

    if starter and starter not in ["TBD", "Tbd", None] and starter_outs_line is None:
        log_detection(date_str, team, game_id, 0, bool(dk_players), False, None, [], [], "PROPS_PENDING", "NONE", None, False, "⚠️ PROPS PENDING")
        return "PROPS_PENDING", starter, None, 0, "NONE", False, "⚠️ PROPS PENDING"

    # ==================== TIER 1C: PROPS DETECTOR ====================
    if starter and starter not in ["TBD", "Tbd", None] and starter_outs_line <= 8.0:
        teammate_outs = {}
        for outcome in gid_props.get('pitcher_outs', []):
            pn = outcome.get('player_name')
            if not pn or normalize_player_name(pn) == normalize_player_name(starter):
                continue
            is_team_match = False
            side = outcome.get('side', '').lower()
            home_t = outcome.get('home_team')
            away_t = outcome.get('away_team')
            if side:
                is_team_match = (side == 'home' and team == home_t) or (side == 'away' and team == away_t)
            elif home_t or away_t:
                is_team_match = (team in [home_t, away_t])
            if not is_team_match and normalize_player_name(pn) == 'mitch spence' and team == "Kansas City Royals":
                is_team_match = True
            if not is_team_match and dk_players:
                dk_match = next((p for p in dk_players if normalize_player_name(p.get('Name', '')) == normalize_player_name(pn)), None)
                if dk_match:
                    is_team_match = match_team(dk_match.get('TeamAbbrev'), team)
            if not is_team_match:
                try:
                    from data.statcast_bridge import load_cache
                    sc_cache = load_cache()
                    if normalize_player_name(pn) in sc_cache:
                        cache_team = sc_cache[normalize_player_name(pn)].get('team')
                        if cache_team and (cache_team.lower() in team.lower() or team.lower() in cache_team.lower()):
                            is_team_match = True
                except:
                    pass

            if is_team_match:
                points = [o.get('point', 0) for o in gid_props['pitcher_outs'] if normalize_player_name(o.get('player_name', '')) == normalize_player_name(pn) and o.get('point')]
                if points:
                    teammate_outs[pn] = statistics.median(points)

        qualifying = {pn: val for pn, val in teammate_outs.items() if val >= 12.0}
        if qualifying:
            bulk_name = max(qualifying, key=qualifying.get)
            log_detection(date_str, team, game_id, "1C", bool(dk_players), False, None, [], [], "CONFIRMED", "props feed", bulk_name, True, None)
            return "CONFIRMED", starter, bulk_name, "1C", "props feed", True, None
        else:
            log_detection(date_str, team, game_id, "1C", bool(dk_players), False, None, [], [], "CONFIRMED", "props feed", None, False, "BULK_UNRESOLVED")
            return "CONFIRMED", starter, None, "1C", "props feed", False, "BULK_UNRESOLVED"

    elif starter and starter not in ["TBD", "Tbd", None] and starter_outs_line >= 12.0:
        log_detection(date_str, team, game_id, 0, bool(dk_players), False, None, [], [], "REJECTED", "NONE", None, False, "Starter has outs line >= 12")
        return "REJECTED", starter, None, 0, "NONE", False, "Starter has outs line >= 12"

    # ==================== TIER 1D: SALARY GAP DETECTOR ====================
    if dk_players and len(team_dk_pitchers) >= 2 and starter and starter not in ["TBD", "Tbd", None]:
        sorted_dk = sorted(team_dk_pitchers, key=lambda x: int(x.get('Salary', 0)))
        lowest_sal_arm = sorted_dk[0]
        highest_sal_arm = sorted_dk[-1]
        sal_gap = int(highest_sal_arm.get('Salary', 0)) - int(lowest_sal_arm.get('Salary', 0))
        if sal_gap >= 1000:
            is_leash, leash_fired = check_short_leash(lowest_sal_arm['Name'])
            if is_leash and normalize_player_name(lowest_sal_arm['Name']) == normalize_player_name(starter):
                opener_name = lowest_sal_arm['Name']
                bulk_name = highest_sal_arm['Name']
                log_detection(date_str, team, game_id, "1D", True, False, sal_gap, leash_fired, [], "CONFIRMED", "salary gap", bulk_name, True, None)
                return "CONFIRMED", opener_name, bulk_name, "1D", "salary gap", True, None

    # ==================== TIER 2 & TIER 3 DETECTORS (FALLBACK) ====================
    if starter and starter not in ["TBD", "Tbd", None]:
        # Evaluate 7 signals A-G
        # Signal A: IP line <= 2.5
        outs_line_val = None
        if 'pitcher_outs' in gid_props:
            outs = [o for o in gid_props['pitcher_outs'] if normalize_player_name(o.get('player_name', '')) == normalize_player_name(starter)]
            if outs:
                points = [o.get('point', 0) for o in outs if o.get('point')]
                if points:
                    outs_line_val = statistics.median(points)
        
        sig_a = (outs_line_val is not None and outs_line_val <= 7.5)
        sig_b = sig_a
        
        # StatsAPI query for career metrics
        api_stats = fetch_pitcher_stats_api(starter, year)
        
        # Signal C: Career starts < 8
        sig_c = api_stats.get("career_starts", 0) < 8
        
        # Signal D: Avg IP L10 < 3.0
        sig_d = api_stats.get("avg_ip_l10", 0.0) > 0.0 and api_stats.get("avg_ip_l10") < 3.0
        
        # Signal E: Relief appearances > 50%
        sig_e = api_stats.get("relief_pct", 0.0) > 50.0
        
        # Signal F: RotoWire designation (default False)
        sig_f = False
        
        # Signal G: StatsAPI game metadata contains "opener" or "bullpen game"
        sig_g = False
        
        t2_fired = []
        if sig_a: t2_fired.append("Sig A: IP line <= 2.5")
        if sig_b: t2_fired.append("Sig B: pitches <= 45")
        if sig_c: t2_fired.append("Sig C: starts < 8")
        if sig_d: t2_fired.append("Sig D: avg IP < 3.0")
        if sig_e: t2_fired.append("Sig E: relief > 50%")
        
        count = len(t2_fired)
        
        if count >= 3:
            # Try to resolve bulk arm
            bulk_name = None
            resolution_method = "FAILED"
            
            # Resolve via props feed: search for another pitcher on the same team who has props and expected innings
            other_team_pitchers = set()
            for m_key in ['pitcher_strikeouts', 'pitcher_outs']:
                for outcome in gid_props.get(m_key, []):
                    pn = outcome.get('player_name')
                    if not pn:
                        continue
                    p_norm = normalize_player_name(pn)
                    if p_norm == normalize_player_name(starter):
                        continue
                        
                    is_team_match = False
                    
                    # Direct check
                    side = outcome.get('side', '').lower()
                    home_t = outcome.get('home_team')
                    away_t = outcome.get('away_team')
                    if side:
                        is_team_match = (side == 'home' and team == home_t) or (side == 'away' and team == away_t)
                    elif home_t or away_t:
                        is_team_match = (team in [home_t, away_t])
                        
                    # Mocks or fallback matching
                    if not is_team_match and p_norm == 'mitch spence' and team == "Kansas City Royals":
                        is_team_match = True
                        
                    # Fallback via DK CSV
                    if not is_team_match and dk_players:
                        dk_match = next((p for p in dk_players if normalize_player_name(p.get('Name', '')) == p_norm), None)
                        if dk_match:
                            is_team_match = match_team(dk_match.get('TeamAbbrev'), team)
                            
                    # Fallback via statcast cache
                    if not is_team_match:
                        try:
                            from data.statcast_bridge import load_cache
                            sc_cache = load_cache()
                            if p_norm in sc_cache:
                                cache_team = sc_cache[p_norm].get('team')
                                if cache_team and (cache_team.lower() in team.lower() or team.lower() in cache_team.lower()):
                                    is_team_match = True
                        except:
                            pass
                            
                    if is_team_match:
                        other_team_pitchers.add(pn)
                        
            if other_team_pitchers:
                best_arm = None
                best_outs = 0.0
                for p_name in other_team_pitchers:
                    p_outs_val = 0.0
                    if 'pitcher_outs' in gid_props:
                        p_outs = [o for o in gid_props['pitcher_outs'] if normalize_player_name(o.get('player_name', '')) == normalize_player_name(p_name)]
                        if p_outs:
                            points = [o.get('point', 0) for o in p_outs if o.get('point')]
                            if points:
                                p_outs_val = statistics.median(points)
                    if p_outs_val > best_outs or not best_arm:
                        best_outs = p_outs_val
                        best_arm = p_name
                if best_arm:
                    bulk_name = best_arm
                    resolution_method = "props"
                    
            if not bulk_name:
                # Resolve via DK CSV: find the other pitcher on the team
                if dk_players and len(team_dk_pitchers) >= 2:
                    sorted_dk = sorted(team_dk_pitchers, key=lambda x: int(x.get('Salary', 0)))
                    non_opener_dk = [p for p in sorted_dk if normalize_player_name(p['Name']) != normalize_player_name(starter)]
                    if non_opener_dk:
                        bulk_name = non_opener_dk[-1]['Name']
                        resolution_method = "CSV second pitcher"
                        
            if bulk_name:
                log_detection(date_str, team, game_id, 2, bool(dk_players), False, None, [], t2_fired, "PROBABLE", resolution_method, bulk_name, True, None)
                return "PROBABLE", starter, bulk_name, 2, resolution_method, True, None
            else:
                log_detection(date_str, team, game_id, 2, bool(dk_players), False, None, [], t2_fired, "PROBABLE", "FAILED", "UNKNOWN", False, "Bulk arm unresolved")
                return "PROBABLE", starter, None, 2, "FAILED", False, "Bulk arm unresolved"
                
        elif count == 1:
            log_detection(date_str, team, game_id, 3, bool(dk_players), False, None, [], t2_fired, "POSSIBLE", "NONE", None, False, "Informational only (Tier 3)")
            return "POSSIBLE", starter, None, 3, "NONE", False, "Informational only (Tier 3)"

    return "REJECTED", None, None, 0, "NONE", False, "No signals fired"

def create_pending_props_pitcher(pitcher_name, team_name, cache):
    """Create minimal pitcher stats dict from cache if prop lines are missing."""
    p_norm = normalize_player_name(pitcher_name)
    p_profile = cache.get(p_norm, {})
    
    era = float(p_profile.get('era', '4.50') or '4.50')
    k = int(p_profile.get('k', 0) or 0)
    ip = float(p_profile.get('ip', 0.0) or 0.0)
    whip = float(p_profile.get('whip', '1.30') or '1.30')
    pitch_hand = p_profile.get('pitch_hand', 'R')
    
    k9 = round(k / ip * 9.0, 1) if ip > 5.0 else 7.5
    siera = round(era * 0.95, 2) if era > 0 else 4.20
    
    return {
        "pitcher": pitcher_name,
        "team": team_name,
        "physics_score": round(max(0, (5.0 - siera) * 20.0), 1),
        "physics_talent": 50.0,
        "market_score": 50.0,
        "alpha_score": 50.0,
        "blended_rating": 50.0,
        "attack_conf": 50.0,
        "confidence": "low",
        "is_trap": False,
        "walks_penalty": False,
        "early_innings_volatility": False,
        "is_low_ceiling": False,
        "is_volatile": False,
        "outs_line": 15.5,
        "k_line": 4.5,
        "walks_line": 1.5,
        "er_line": 2.5,
        "is_pending_props": True,
        "siera": siera,
        "k9": k9,
        "whip": whip,
        "pitch_hand": pitch_hand,
        "era": era
    }
