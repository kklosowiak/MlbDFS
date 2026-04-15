import json
import os

def backfill():
    snapshot_path = 'data/snapshot_20260411_093359.json'
    opening_path = 'data/opening_lines.json'
    
    if not os.path.exists(snapshot_path):
        print(f"Error: {snapshot_path} not found.")
        return

    with open(snapshot_path, 'r') as f:
        snapshot = json.load(f)

    opening_data = []
    processed_keys = set()
    
    for game in snapshot.get('odds', []):
        home = game['home_team']
        away = game['away_team']
        key = f"{away}@{home}"
        
        if key in processed_keys: continue
        processed_keys.add(key)
        
        # Simple extraction for backfill
        home_ml = None
        away_ml = None
        total = None
        
        for book in game.get('bookmakers', []):
            if book['key'] == 'draftkings':
                for market in book.get('markets', []):
                    if market['key'] == 'h2h':
                        for o in market['outcomes']:
                            if o['name'] == home: home_ml = o['price']
                            if o['name'] == away: away_ml = o['price']
                    if market['key'] == 'totals':
                        total = market['outcomes'][0]['point']
        
        if home_ml and away_ml:
            opening_data.append({
                "team_away": away,
                "team_home": home,
                "away_opening_ml": away_ml,
                "away_current_ml": away_ml,
                "home_opening_ml": home_ml,
                "home_current_ml": home_ml,
                "opening_total": total or 8.5,
                "current_total": total or 8.5
            })

    with open(opening_path, 'w') as f:
        json.dump(opening_data, f, indent=4)
    
    print(f"Successfully backfilled {len(opening_data)} games from 9:33 AM baseline.")

if __name__ == "__main__":
    backfill()
