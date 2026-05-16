import json

snapshot_path = "data/snapshot_20260515_170958.json"
with open(snapshot_path, 'r') as f:
    snapshot = json.load(f)

# The snapshot structure for rosters is: snapshot['rosters'][team_name] = [list of players]
# Confirmed players have an 'order' field.

teams_of_interest = [
    "Chicago White Sox", "Chicago Cubs", 
    "Los Angeles Angels", "Los Angeles Dodgers",
    "Atlanta Braves", "Boston Red Sox",
    "Houston Astros", "Texas Rangers",
    "San Diego Padres", "Seattle Mariners",
    "Cleveland Guardians", "Cincinnati Reds",
    "Miami Marlins", "Tampa Bay Rays"
]

print("=== CONFIRMED LINEUPS ===")
for team in teams_of_interest:
    roster = snapshot.get('rosters', {}).get(team, [])
    confirmed = [p for p in roster if p.get('order')]
    if confirmed:
        confirmed.sort(key=lambda x: x['order'])
        print(f"\n{team.upper()}:")
        for p in confirmed:
            print(f"  {p['order']}. {p['name']} ({p['position']})")
    else:
        print(f"\n{team.upper()}: [NOT CONFIRMED OR MISSING]")
