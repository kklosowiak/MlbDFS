import json
import os
import sys

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import config

snapshot_dir = config.DATA_DIR
files = [f for f in os.listdir(snapshot_dir) if f.startswith("snapshot_") and f.endswith(".json")]
if not files:
    print("No snapshots found")
    sys.exit(1)
files.sort(reverse=True)
latest_snap_path = os.path.join(snapshot_dir, files[0])

print(f"Loading snapshot: {latest_snap_path}")
with open(latest_snap_path, 'r') as f:
    snap = json.load(f)

results_path = os.path.join(config.REPORTS_DIR, "latest_results.json")
print(f"Loading results: {results_path}")
if not os.path.exists(results_path):
    print("No results file found")
    sys.exit(1)
with open(results_path, 'r') as f:
    res = json.load(f)

snap_games = set()
for g in snap.get('odds', []):
    away = g.get('away_team')
    home = g.get('home_team')
    snap_games.add((away, home, g.get('commence_time')))

res_games = set()
for p in res.get('pitchers', []):
    team = p.get('team')
    opp = p.get('opponent')
    # determine who is home/away from side
    if p.get('side') == 'home':
        res_games.add((opp, team))
    else:
        res_games.add((team, opp))

print("\n" + "="*80)
print("SNAP GAMES:")
for a, h, t in sorted(snap_games):
    print(f"  {a} @ {h} | Commence: {t}")

print("\n" + "="*80)
print("RESULTS GAMES:")
for a, h in sorted(res_games):
    print(f"  {a} @ {h}")

print("\n" + "="*80)
# Check missing
print("GAMES IN SNAPSHOT BUT MISSING IN RESULTS:")
found_any = False
for a, h, t in snap_games:
    matched = False
    for ra, rh in res_games:
        if (a == ra and h == rh) or (a == rh and h == ra):
            matched = True
            break
    if not matched:
        print(f"  MISSING: {a} @ {h} | Commence: {t}")
        found_any = True

if not found_any:
    print("  None! All snapshot games are successfully analyzed in the results file.")
print("="*80)
