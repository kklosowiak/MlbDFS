import json
import os
import glob
from datetime import datetime
from dateutil import parser

# Get latest snapshot
snapshots = glob.glob('data/snapshot_*.json')
latest_snap = max(snapshots, key=os.path.getmtime)
with open(latest_snap, 'r') as f:
    snap_data = json.load(f)

# Get latest results
with open('reports/latest_results.json', 'r') as f:
    results_data = json.load(f)

night_teams = set()
for game in snap_data.get('games', []):
    dt = parser.parse(game['date'])
    if dt.hour >= 23 or dt.hour <= 3:
        night_teams.add(game['home_team'])
        night_teams.add(game['away_team'])

print('--- NIGHT TEAMS ---')
print(list(night_teams))

print('\n--- TOP NIGHT PITCHERS ---')
night_pitchers = [p for p in results_data['pitchers'] if p['team'] in night_teams or p['opponent'] in night_teams]
night_pitchers.sort(key=lambda x: x['alpha_score'], reverse=True)
for p in night_pitchers[:5]:
    print(f"{p['pitcher']} ({p['team']}) - Alpha: {p['alpha_score']} | CSW: {p['csw']} | Market: {p['market_score']} | Sharp: {p['is_juiced_target']}")

print('\n--- TOP NIGHT STACKS ---')
night_stacks = [t for t in results_data['teams'] if t['team'] in night_teams]
for t in night_stacks[:5]:
    trend = t.get('trend', 'STABLE')
    print(f"{t['team']} vs {t['opp_pitcher']} - Score: {t['stack_score']} | Div: {t['divergence']}% ({trend}) | Sharp: {t['is_sharp']}")

print('\n--- TOP NIGHT HITTERS ---')
night_hitters = [h for h in results_data['hitters'] if h['team'] in night_teams]
for h in night_hitters[:10]:
    print(f"{h['name']} ({h['team']}) - Score: {h['player_score']} | Hot: {h['is_hot']} | Sharp: {h['is_juiced_target']}")
