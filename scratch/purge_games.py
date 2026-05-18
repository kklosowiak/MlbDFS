import json
import os

purge_teams = [
    "Baltimore Orioles", "Washington Nationals",
    "Philadelphia Phillies", "Pittsburgh Pirates",
    "Miami Marlins", "Tampa Bay Rays",
    "Toronto Blue Jays", "Detroit Tigers",
    "Kansas City Royals", "St. Louis Cardinals",
    "Arizona Diamondbacks", "Colorado Rockies",
    "Cincinnati Reds", "Cleveland Guardians"
]

snapshot_file = "data/snapshot_20260516_133906.json"
with open(snapshot_file, 'r') as f:
    snapshot = json.load(f)

all_teams = set()
for game in snapshot.get('odds', []):
    all_teams.add(game['home_team'])
    all_teams.add(game['away_team'])

allowed_teams = [team for team in all_teams if team not in purge_teams]

filter_data = {
    "enabled": True,
    "active_date": "2026-05-16",
    "allowed_teams": allowed_teams
}

with open("data/slate_filter.json", 'w') as f:
    json.dump(filter_data, f, indent=4)

print(f"Purged {len(purge_teams)} teams. Allowed {len(allowed_teams)} teams.")
print(f"Allowed Teams: {allowed_teams}")
