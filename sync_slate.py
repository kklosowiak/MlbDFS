import os
import sys
import json
import argparse
import glob
from datetime import datetime, timezone, timedelta

# Force UTF-8 stdout
sys.stdout.reconfigure(encoding='utf-8')

# Map team abbreviation to full name
TEAM_MAP = {
    'MIL': 'Milwaukee Brewers',
    'LAD': 'Los Angeles Dodgers',
    'CIN': 'Cincinnati Reds',
    'ATL': 'Atlanta Braves',
    'TOR': 'Toronto Blue Jays',
    'HOU': 'Houston Astros',
    'MIN': 'Minnesota Twins',
    'SD': 'San Diego Padres',
    'NYM': 'New York Mets',
    'CHC': 'Chicago Cubs',
    'STL': 'St. Louis Cardinals',
    'SF': 'San Francisco Giants',
    'SFG': 'San Francisco Giants',
    'ATH': 'Athletics',
    'OAK': 'Athletics',
    'MIA': 'Miami Marlins',
    'PHI': 'Philadelphia Phillies',
    'WSH': 'Washington Nationals',
    'PIT': 'Pittsburgh Pirates',
    'TB': 'Tampa Bay Rays',
    'TBR': 'Tampa Bay Rays',
    'BOS': 'Boston Red Sox',
    'BAL': 'Baltimore Orioles',
    'NYY': 'New York Yankees',
    'CLE': 'Cleveland Guardians',
    'DET': 'Detroit Tigers',
    'CWS': 'Chicago White Sox',
    'CHW': 'Chicago White Sox',
    'KC': 'Kansas City Royals',
    'KCR': 'Kansas City Royals',
    'TEX': 'Texas Rangers',
    'SEA': 'Seattle Mariners',
    'ARI': 'Arizona Diamondbacks',
    'COL': 'Colorado Rockies',
    'LAA': 'Los Angeles Angels'
}

def find_latest_snapshot(data_dir):
    files = glob.glob(os.path.join(data_dir, "snapshot_*.json"))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def main():
    parser = argparse.ArgumentParser(description="Sync Slate Filter with OMEGA night-slate games")
    parser.add_argument("--dry-run", action="store_true", help="Print slate changes without writing to file")
    parser.add_argument("--night-only", action="store_true", help="Filter for night games only (commencing after 6:00 PM ET / 22:00 UTC)")
    parser.add_argument("--cutoff-mins", type=int, default=90, help="Purge games started more than X minutes ago (default: 90)")
    parser.add_argument("--exclude-teams", nargs="+", help="Exclude specific team names or abbreviations")
    parser.add_argument("--custom-teams", nargs="+", help="Explicitly specify the list of teams to allow")
    
    args = parser.parse_args()
    
    # Resolve project paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    filter_path = os.path.join(data_dir, "slate_filter.json")
    
    # Check custom teams first
    if args.custom_teams:
        allowed_teams = []
        for t in args.custom_teams:
            upper_t = t.upper()
            if upper_t in TEAM_MAP:
                allowed_teams.append(TEAM_MAP[upper_t])
            else:
                allowed_teams.append(t)
        
        write_filter(filter_path, allowed_teams, args.dry_run)
        return

    # Find latest snapshot
    snapshot_path = find_latest_snapshot(data_dir)
    if not snapshot_path:
        print("ERROR: No OMEGA snapshot found in data directory. Run a fresh fetch first.")
        sys.exit(1)
        
    print(f"Reading snapshot: {os.path.basename(snapshot_path)}")
    with open(snapshot_path, 'r', encoding='utf-8') as f:
        snapshot = json.load(f)
        
    odds = snapshot.get('odds', [])
    if not odds:
        print("WARNING: Snapshot contains no game/odds entries.")
        sys.exit(0)
        
    now_utc = datetime.now(timezone.utc)
    active_teams = set()
    games_count = 0
    
    print("\n--- GALE MATCHUP RESOLUTION ---")
    for g in odds:
        home = g.get('home_team')
        away = g.get('away_team')
        ct = g.get('commence_time') or g.get('game_time') or ''
        
        if not ct:
            continue
            
        try:
            # Parse commence time (ISO 8601 UTC)
            game_dt = datetime.fromisoformat(ct.replace('Z', '+00:00'))
        except Exception as e:
            print(f"  [ERROR] Parsing time '{ct}' for {away} @ {home}: {e}")
            continue
            
        # 1. Doubleheader Cutoff check (Started > 90 mins ago)
        started_diff_seconds = (now_utc - game_dt).total_seconds()
        if started_diff_seconds > (args.cutoff_mins * 60):
            print(f"  [PURGED] {away} @ {home} ({game_dt.strftime('%I:%M %p ET')}) - Started > {args.cutoff_mins} mins ago")
            continue
            
        # 2. Night Only filter (Starts after 6:00 PM ET / 22:00 UTC)
        # 22:00 UTC is 6:00 PM ET (EDT is UTC-4)
        if args.night_only:
            # Use game hour in UTC
            if game_dt.hour < 22:
                print(f"  [SKIP DAY] {away} @ {home} ({game_dt.strftime('%I:%M %p ET')}) - Day Game")
                continue
                
        # 3. Manual exclusion check
        if args.exclude_teams:
            excl_upper = [x.upper() for x in args.exclude_teams]
            exclude_this = False
            for team in [home, away]:
                # check full name and abbreviation
                abbr = next((k for k, v in TEAM_MAP.items() if v.lower() == team.lower()), '')
                if team.upper() in excl_upper or (abbr and abbr in excl_upper):
                    exclude_this = True
                    break
            if exclude_this:
                print(f"  [EXCLUDED] {away} @ {home} ({game_dt.strftime('%I:%M %p ET')}) - Excluded by flag")
                continue
                
        print(f"  [ACTIVE] {away} @ {home} ({game_dt.strftime('%I:%M %p ET')})")
        active_teams.add(home)
        active_teams.add(away)
        games_count += 1
        
    print(f"\nResolved {games_count} active games ({len(active_teams)} teams).")
    
    if not active_teams:
        print("WARNING: No active teams resolved. Slate filter not updated.")
        sys.exit(0)
        
    write_filter(filter_path, sorted(list(active_teams)), args.dry_run)

def write_filter(filter_path, allowed_teams, dry_run):
    today = datetime.now().strftime("%Y-%m-%d")
    filter_data = {
        "enabled": True,
        "active_date": today,
        "allowed_teams": allowed_teams
    }
    
    print("\n--- PROPOSED SLATE FILTER ---")
    print(f"Active Date: {today}")
    print("Allowed Teams:")
    for t in allowed_teams:
        print(f"  - {t}")
        
    if dry_run:
        print("\n[DRY RUN]: File write skipped.")
    else:
        with open(filter_path, 'w', encoding='utf-8') as f:
            json.dump(filter_data, f, indent=4)
        print(f"\nSUCCESS: Slate filter updated successfully at {filter_path}")

if __name__ == "__main__":
    main()
