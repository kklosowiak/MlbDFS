import sys
sys.path.append(r"c:\Users\konra\.gemini\antigravity\scratch\mlb_dfs_sharps_engine")
from data.pitcher_analyzer import PitcherAnalyzer
from config import config
import json, os

snapshot_path = r"c:\Users\konra\.gemini\antigravity\scratch\mlb_dfs_sharps_engine\data\snapshot_20260410_154842.json"
with open(snapshot_path, 'r') as f: snap = json.load(f)
rosters = {"Milwaukee Brewers": "Aaron Ashby"}
p = PitcherAnalyzer()
reports = p.analyze_slate(snapshot_path, os.path.join(config.DATA_DIR, "opening_lines.json"), os.path.join(config.DATA_DIR, "consensus_splits_live.json"), props_data=snap.get('props',{}), rosters=rosters)
for r in reports:
    if r['pitcher'] == 'Aaron Ashby':
        print(f"k_line: {r['k_line']}, outs_line: {r['outs_line']}")
