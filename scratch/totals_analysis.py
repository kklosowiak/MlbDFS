import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('reports/latest_results.json', 'r') as f:
    results = json.load(f)

night_teams = [
    "New York Yankees", "Kansas City Royals",
    "Miami Marlins", "Milwaukee Brewers",
    "Boston Red Sox", "Detroit Tigers",
    "Minnesota Twins", "Cincinnati Reds",
    "Houston Astros", "St. Louis Cardinals",
    "Colorado Rockies", "Los Angeles Dodgers",
    "Los Angeles Angels", "San Diego Padres",
    "Arizona Diamondbacks", "Toronto Blue Jays",
    "Athletics", "Chicago White Sox",
    "Seattle Mariners", "Texas Rangers"
]

matchups = {}

# Group teams by matchup
for t in results['teams']:
    if t['team'] in night_teams:
        team_name = t['team']
        opp_pitcher = t['opp_pitcher']
        
        # We find the opponent team based on opp_pitcher from the pitchers list
        opp_team = "Unknown"
        for p in results['pitchers']:
            if p['pitcher'] == opp_pitcher:
                opp_team = p['team']
                break
                
        # If we couldn't match by pitcher, try to match by who is playing who in the API array
        if opp_team == "Unknown":
            with open('data/snapshot_20260417_182155.json', 'r') as fsnap:
                 snap = json.load(fsnap)
                 for g in snap.get('odds', []):
                     if g['home_team'] == team_name:
                         opp_team = g['away_team']
                     elif g['away_team'] == team_name:
                         opp_team = g['home_team']

        
        # Create a unique match ID
        match_arr = sorted([team_name, opp_team])
        match_id = f"{match_arr[0]} vs {match_arr[1]}"
        
        if match_id not in matchups:
            matchups[match_id] = {'moves': []}
        
        matchups[match_id]['moves'].append(t.get('tt_move', 0.0))

print("============ OVER/UNDER SHARP MOVEMENT ============")
for match, data in matchups.items():
    moves = data['moves']
    # The game total move is typically consistent across both teams or represents individual team totals.
    # Take the max absolute move to see if the game moved up or down overall.
    if len(moves) == 0: continue
    
    # Let's just output the first valid TT move assuming the game total moved consistently
    avg_move = sum(moves) / len(moves) if moves else 0.0
    
    if avg_move > 0:
        print(f"📈 SHARPS BETTING THE OVER: {match} (Moved +{avg_move:.1f} Runs)")
    elif avg_move < 0:
        print(f"📉 SHARPS BETTING THE UNDER: {match} (Moved {avg_move:.1f} Runs)")
    else:
        print(f"➖ NO TOTAL MOVEMENT: {match} (Stable)")

