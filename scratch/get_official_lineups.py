from data.lineup_fetcher import LineupFetcher

fetcher = LineupFetcher()
lineups = fetcher.fetch_confirmed_lineups()

print("=== OFFICIAL CONFIRMED LINEUPS (MLB STATSAPI) ===")
if not lineups:
    print("No confirmed lineups found yet.")
else:
    for team, players in lineups.items():
        if players:
            print(f"\n{team.upper()}:")
            for i, p in enumerate(players, 1):
                print(f"  {i}. {p}")
