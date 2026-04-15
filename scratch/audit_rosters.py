import json
import os

def extract_2026_rosters(snapshot_path):
    with open(snapshot_path, 'r') as f:
        data = json.load(f)
    
    mapping = {}
    props = data.get('props', {})
    
    for game_id, markets in props.items():
        for market_key, entries in markets.items():
            for entry in entries:
                p_name = entry.get('player_name')
                home = entry.get('home_team')
                away = entry.get('away_team')
                side = entry.get('side') # Some props have side: home/away
                
                # We need to determine the side. Usually 'home_team' and 'away_team' are present.
                # If we don't have 'side', we can't be 100% sure unless we look at multiple props.
                if p_name not in mapping:
                    mapping[p_name] = {'home': home, 'away': away}
    
    # Let's try to get more specific.
    # We can look at the hitters report to see how they were resolved.
    return mapping

if __name__ == "__main__":
    path = "data/snapshot_20260412_104206.json"
    rosters = extract_2026_rosters(path)
    for p, teams in list(rosters.items())[:50]:
        print(f"{p}: {teams['away']} @ {teams['home']}")
