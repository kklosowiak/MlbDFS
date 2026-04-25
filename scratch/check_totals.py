import json
import os

def check_total_movement():
    # Load opening lines
    with open('data/opening_lines.json', 'r') as f:
        opening = json.load(f)
    
    # Get latest snapshot
    snapshots = sorted([f for f in os.listdir('data') if f.startswith('snapshot_') and f.endswith('.json')])
    if not snapshots:
        print("No snapshots found.")
        return
    
    latest_path = os.path.join('data', snapshots[-1])
    with open(latest_path, 'r') as f:
        snap = json.load(f)
    
    events = snap.get('events', [])
    
    print(f"--- TOTAL MOVEMENT ANALYSIS (Baseline: {snapshots[-1]}) ---")
    
    found = False
    for event in events:
        away = event.get('away_team')
        home = event.get('home_team')
        
        # Match with opening line
        open_game = next((o for o in opening if o.get('team_away') == away and o.get('team_home') == home), None)
        
        if open_game:
            open_total = open_game.get('opening_total')
            current_total = None
            
            # Find current total (using DraftKings as proxy for market)
            for book in event.get('bookmakers', []):
                if book.get('key') == 'draftkings':
                    for market in book.get('markets', []):
                        if market.get('key') == 'totals':
                            for outcome in market.get('outcomes', []):
                                current_total = outcome.get('point')
                                break
            
            if current_total is not None:
                diff = current_total - open_total
                if abs(diff) >= 0: # Show all for now to help user see the board
                    found = True
                    move_indicator = ""
                    if diff > 0:
                        move_indicator = " 🔥 OVER SHARP?"
                    elif diff < 0:
                        move_indicator = " ❄️ UNDER SHARP?"
                    
                    print(f"{away} @ {home}: {open_total} -> {current_total} (Diff: {diff:+.1f}){move_indicator}")
    
    if not found:
        print("No matches found between opening lines and current snapshot.")

if __name__ == "__main__":
    check_total_movement()
