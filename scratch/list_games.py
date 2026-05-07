import json, glob, os

# Find latest snapshot
files = sorted(glob.glob("data/snapshot_*.json"), reverse=True)
if not files:
    print("No snapshot found")
    exit()

snap = files[0]
print(f"Snapshot: {snap}")
d = json.load(open(snap))
games = d.get('odds', [])
games.sort(key=lambda x: x.get('commence_time', ''))

print(f"\nTotal games: {len(games)}\n")
print(f"{'Time':26s}  {'Away':26s}  {'Home':26s}  {'Away P':22s}  {'Home P':22s}")
print("-" * 130)

for g in games:
    ct = g.get('commence_time', '?')
    away = g.get('away_team', '?')
    home = g.get('home_team', '?')
    ap = g.get('away_pitcher', 'TBD')
    hp = g.get('home_pitcher', 'TBD')
    print(f"{ct:26s}  {away:26s}  {home:26s}  {ap:22s}  {hp:22s}")
