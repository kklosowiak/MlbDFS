from data.lineup_fetcher import LineupFetcher
import json

fetcher = LineupFetcher()
lineups = fetcher.fetch_confirmed_lineups()
print(f"Fetched {len(lineups)} teams.")
for team, players in lineups.items():
    print(f"{team}: {players[:3]}...")
