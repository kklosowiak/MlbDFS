import json

with open('data/snapshot_20260426_115644.json', 'r') as f:
    data = json.load(f)

for game in data.get('odds', []):
    if game.get('id') == 'd8f901c0fc526d986a568d86c64039d5':
        print(f"Game: {game['home_team']} vs {game['away_team']}")
        print(f"Home Pitcher: {game.get('home_pitcher')}")
        print(f"Away Pitcher: {game.get('away_pitcher')}")
        break
