import json

with open('data/snapshot_20260426_115644.json', 'r') as f:
    data = json.load(f)

for game in data.get('odds', []):
    for bm in game.get('bookmakers', []):
        for market in bm.get('markets', []):
            for outcome in market.get('outcomes', []):
                name = outcome.get('name', '')
                description = outcome.get('description', '')
                if 'joc' in name.lower() or 'joc' in description.lower():
                    print(f"Joc found in game: {game['home_team']} vs {game['away_team']}")
                    print(f"Full Name: {name or description}")
                    import sys
                    sys.exit(0)
