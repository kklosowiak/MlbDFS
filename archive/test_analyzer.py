import json
import os
import sys

# To print unbuffered
sys.stdout.reconfigure(line_buffering=True)

from data.pitcher_analyzer import PitcherAnalyzer
from config import config

p_analyzer = PitcherAnalyzer()
snapshot_path = r"data\snapshot_20260410_154842.json"
opening_lines_path = os.path.join(config.DATA_DIR, "opening_lines.json")
splits_path = os.path.join(config.DATA_DIR, "consensus_splits_live.json")

print("Loading snapshot...")
with open(snapshot_path, 'r') as f:
    snapshot = json.load(f)

rosters = {}
print("Starting analyze_slate...")
try:
    reports = p_analyzer.analyze_slate(
        snapshot_path, 
        opening_lines_path, 
        splits_path, 
        props_data=snapshot.get('props', {}),
        rosters=rosters
    )
    print("Done!")
except Exception as e:
    import traceback
    traceback.print_exc()
