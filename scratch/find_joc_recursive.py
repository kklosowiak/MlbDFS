import json

def find_val(data, target, path=""):
    if isinstance(data, dict):
        for k, v in data.items():
            current_path = f"{path} -> {k}"
            if target in str(k).lower() or target in str(v).lower():
                if not isinstance(v, (dict, list)):
                    print(f"FOUND: {v} at {current_path}")
                    # If this is a prop, it might have team info
                    if 'player_name' in data:
                        print(f"  Context: {data.get('home_team')} vs {data.get('away_team')}")
                        print(f"  Player Team Hint: {data.get('side')}")
                find_val(v, target, current_path)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            find_val(item, target, f"{path}[{i}]")

with open('data/snapshot_20260426_115644.json', 'r') as f:
    data = json.load(f)

find_val(data, 'joc pederson')
