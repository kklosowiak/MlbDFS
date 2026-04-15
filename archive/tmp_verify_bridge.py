import os
import json
from data.hitter_prop_analyzer import HitterPropAnalyzer
from config import config

def test_bridge():
    analyzer = HitterPropAnalyzer()
    
    # Use the latest snapshot
    snapshot_dir = config.DATA_DIR
    snapshots = [f for f in os.listdir(snapshot_dir) if f.startswith("snapshot_") and f.endswith(".json")]
    if not snapshots:
        print("No snapshots found.")
        return
        
    latest_snapshot = os.path.join(snapshot_dir, sorted(snapshots, reverse=True)[0])
    print(f"Testing with snapshot: {latest_snapshot}")
    
    hitters = analyzer.extract_top_hitters(latest_snapshot)
    
    print(f"\nExtracted {len(hitters)} hitters.")
    
    # Check for TBD teams
    tbd_hitters = [h for h in hitters if h['team'] == 'TBD']
    print(f"Hitters with TBD team: {len(tbd_hitters)}")
    
    # Check for a specific high-alpha hitter from the anchors
    anchors = analyzer.get_anchor_teams()
    for team, players in anchors.items():
        for p in players:
            found = next((h for h in hitters if h['name'] == p), None)
            if found:
                print(f"Found {p}: Team={found['team']} (Expected: {team})")
                break
        if 'found' in locals() and found: break

if __name__ == "__main__":
    test_bridge()
