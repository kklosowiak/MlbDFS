from data.umpire_fetcher import UmpireFetcher
import json

fetcher = UmpireFetcher()
assignments = fetcher.fetch_daily_assignments()
with open("data/slate_filter.json", "r") as f:
    slate_filter = json.load(f)
allowed_teams = slate_filter.get("allowed_teams", [])

print("--- Umpire Assignments & Factors ---")
for team, data in assignments.items():
    if team in allowed_teams:
        factor = data["factor"]
        bias = "NEUTRAL"
        if factor > 1.05: bias = "PITCHER FRIENDLY (Large Zone)"
        elif factor < 0.95: bias = "HITTER FRIENDLY (Tight Zone)"
        print(f"{team}: {data['name']} (Factor: {factor}) -> {bias}")
