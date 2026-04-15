import json

file_path = r"c:\Users\konra\.gemini\antigravity\scratch\mlb_dfs_sharps_engine\data\snapshot_20260410_154842.json"

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Props for Patrick Corbin:")
for game_id, props in data.get("props", {}).items():
    for market, outcomes in props.items():
        if market in ["pitcher_strikeouts", "pitcher_outs"]:
            for outcome in outcomes:
                if outcome.get("player_name") == "Patrick Corbin":
                    print(f"[{outcome['bookmaker']}] {market} - {outcome['side']} {outcome['point']} | Odds: {outcome['price']}")
