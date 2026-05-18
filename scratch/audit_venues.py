import os
import json

base_dir = r"c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS"
results_path = os.path.join(base_dir, "reports", "latest_results.json")

if os.path.exists(results_path):
    with open(results_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    pitchers = data.get("pitchers", [])
    print(f"Total pitchers analyzed: {len(pitchers)}")
    print("-" * 50)
    for p in pitchers[:10]:
        print(f"Pitcher: {p.get('pitcher')}")
        print(f"  Team: {p.get('team')}")
        print(f"  Opponent: {p.get('opponent')}")
        print(f"  Is Home: {p.get('is_home')}")
        print(f"  Side: {p.get('side')}")
        print("-" * 50)
else:
    print(f"Error: {results_path} does not exist")
