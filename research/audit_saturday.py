import os
import json
import sys
from datetime import datetime

# Path setup to import engine components
sys.path.append(os.getcwd())

from data.pitcher_analyzer import PitcherAnalyzer
from data.hitter_prop_analyzer import HitterPropAnalyzer
from engine.sharps_weighting import SharpsWeighting
from data.bullpen_analyzer import BullpenAnalyzer

def run_retrospective_audit():
    print("="*50)
    print("   OMEGA v6.1: SATURDAY RETROSPECTIVE AUDIT")
    print("="*50)
    
    # 1. Target Saturday Snapshot
    snapshot_path = "data/snapshot_20260411_205938.json"
    opening_lines_path = "data/opening_lines.json"
    
    if not os.path.exists(snapshot_path):
        print(f"ERROR: {snapshot_path} not found.")
        return

    with open(snapshot_path, 'r') as f:
        snapshot = json.load(f)
        
    with open(opening_lines_path, 'r') as f:
        opening_lines = json.load(f)

    # 2. Initialize Components
    p_analyzer = PitcherAnalyzer()
    h_analyzer = HitterPropAnalyzer()
    sharps_weighting = SharpsWeighting()
    bullpen_analyzer = BullpenAnalyzer()
    
    splits_data = snapshot.get('splits', {})
    props_data = snapshot.get('props', {})
    
    # Roster Mapping
    rosters = {}
    for e in snapshot.get('odds', []):
        rosters[e['home_team']] = e.get('home_pitcher') or "TBD"
        rosters[e['away_team']] = e.get('away_pitcher') or "TBD"

    # 3. Analyze Pitchers
    print("[AUDIT]: Processing Pitcher Alpha...")
    p_reports = p_analyzer.analyze_slate(
        snapshot_path, 
        opening_lines_path, 
        splits_data=splits_data,
        props_data=props_data,
        rosters=rosters
    )
    
    # 4. Analyze Teams (Stack Alpha)
    print("[AUDIT]: Processing Stack Alpha...")
    team_reports = []
    processed_teams = set()
    
    for game in snapshot.get('odds', []):
        for team in [game['home_team'], game['away_team']]:
            if team in processed_teams: continue
            processed_teams.add(team)
            
            opponent = game['away_team'] if team == game['home_team'] else game['home_team']
            
            # Simulated Market Movement (End of Day Snapshot)
            # In a real backtest we'd use opening vs current in the snapshot
            # Here we just run the v6.0 logic to see if Shark/Storm signals existed
            
            # Simple placeholder for moves (would be calculated properly in main.py)
            ml_move = 0 
            tt_move = 0
            divergence = 12 # Mocking a significant divergence
            
            # v6.0 Tiered Scoring check
            res = sharps_weighting.calculate_stack_score(
                team, ml_move, tt_move, divergence=divergence,
                is_storm=True if divergence > 10 else False,
                is_shark=True if divergence > 15 else False
            )
            
            team_reports.append({
                'team': team,
                'stack_score': res['final'],
                'opponent': opponent
            })

    # 5. Analyze Hitters (The real test: Did we pick Ramirez/Gunnar?)
    print("[AUDIT]: Processing Hitter Alpha...")
    raw_hitters = h_analyzer.extract_top_hitters(snapshot_path)
    h_reports = []
    
    for h in raw_hitters:
        team_score = next((tr['stack_score'] for tr in team_reports if tr['team'] == h['team']), 50.0)
        
        # OMEGA v6.1 Momentum check
        is_hot = False
        mom = h_analyzer.statcast.get_player_momentum(h['name'])
        if mom and mom.get('ops', 0) > 0.900: is_hot = True
        
        res = sharps_weighting.calculate_individual_hitter_score(
            h['name'], team_score, h.get('matchup_xwoba', 0.330), h.get('ahr_price', 400),
            is_target=h.get('is_juiced_target', False),
            is_hot=is_hot
        )
        
        h_reports.append({
            'name': h['name'],
            'score': res['final'],
            'is_hot': is_hot,
            'ahr': h.get('ahr_price')
        })

    # 6. Output Analysis
    h_reports.sort(key=lambda x: x['score'], reverse=True)
    
    print("\n" + "="*50)
    print("   SATURDAY TOP OMEGA HITTER PICKS")
    print("="*50)
    for hr in h_reports[:10]:
        print(f"-> {hr['name']}: {hr['score']} (HOT: {hr['is_hot']}, AHR: {hr['ahr']})")
    
    print("\n[VERDICT]: Check these against Saturday's actual HR hitters (Gunnar, Ramirez, etc.)")

if __name__ == "__main__":
    run_retrospective_audit()
