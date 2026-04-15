import sys
sys.path.append(r"c:\Users\konra\.gemini\antigravity\scratch\mlb_dfs_sharps_engine")
from data.pitcher_analyzer import PitcherAnalyzer
from config import config
import os

p = PitcherAnalyzer()
ext_props = p.load_external_worksheet_props(
    os.path.join(config.DATA_DIR, "manual_props.csv"),
    os.path.join(config.DATA_DIR, "manual_props.csv")
)
print(ext_props)
