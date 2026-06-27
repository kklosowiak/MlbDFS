import json
from pathlib import Path

# Load stats bridge or stats file
stats_path = Path(r"c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\data\backtest_2026_player_stats.json")
if stats_path.exists():
    with open(stats_path, 'r', encoding='utf-8') as f:
        stats = json.load(f)
        bennett = stats.get("jake bennett", {})
        print("--- Jake Bennett 2026 Season Stats ---")
        print(json.dumps(bennett, indent=2))
else:
    print("Stats file not found.")
