from data.lineup_fetcher import LineupFetcher
import json

fetcher = LineupFetcher()
lineups = fetcher.fetch_confirmed_lineups()

# Filter for the teams we care about
teams_to_show = ["St. Louis Cardinals", "Chicago White Sox", "Cleveland Guardians"]
print("\n=== CONFIRMED LINEUPS FOR TODAY ===")
for team, players in lineups.items():
    if any(t in team for t in teams_to_show) and len(players) > 0:
        print(f"\n{team}:")
        for i, p in enumerate(players, 1):
            print(f"  {i}. {p}")
