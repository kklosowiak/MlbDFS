import json

with open(r"c:\Users\konra\.gemini\antigravity\scratch\mlb_dfs_sharps_engine\data\snapshot_20260410_124245.json", 'r', encoding='utf-8') as f:
    data = json.load(f)

for gid, props in data.get("props", {}).items():
    for market, outcomes in props.items():
        for o in outcomes:
            if o.get("player_name") == "Chad Patrick":
                print(f"{market}: {o}")

