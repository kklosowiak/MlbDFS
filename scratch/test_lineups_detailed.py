from data.lineup_fetcher import LineupFetcher
import json

fetcher = LineupFetcher()
lineups = fetcher.fetch_confirmed_lineups()
target_teams = ["Chicago White Sox", "Arizona Diamondbacks", "Chicago Cubs", "Texas Rangers"]

for team in target_teams:
    if team in lineups:
        print(f"--- {team} ---")
        for i, p in enumerate(lineups[team]):
            print(f"{i+1}. {p}")
    else:
        print(f"--- {team} NOT FOUND ---")
