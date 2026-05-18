import json
import os
import sys

# Standalone execution support to import from current working directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.dashboard_generator import DashboardGenerator

archive_path = "reports/archive/results_2026-05-16.json"
if not os.path.exists(archive_path):
    print(f"ERROR: Archived results not found at {archive_path}")
    sys.exit(1)

print(f"Loading archived results from: {archive_path}")
with open(archive_path, 'r', encoding='utf-8') as f:
    summary = json.load(f)

# Re-calculate stack scores for the new v8.8 Talent Floor Gate
for t in summary['teams']:
    physics_raw = t.get('physics_score', 0)
    has_market_inflation = t.get('is_whale') or t.get('is_storm') or t.get('is_shark') or t.get('is_steam') or t.get('is_sharp') or (t.get('divergence', 0) > 12)
    
    if physics_raw < 36.0 and has_market_inflation:
        old_score = t['stack_score']
        # Apply the 5% caution flag (0.95x)
        t['stack_score'] = round(t['stack_score'] * 0.95, 1)
        print(f"  - talent gate: Adjusted {t['team']} stack score from {old_score} to {t['stack_score']}")

# Re-sort teams after score updates
summary['teams'].sort(key=lambda x: x['stack_score'], reverse=True)

# Re-run dashboard generator
dash = DashboardGenerator()
out = dash.generate_report(summary['pitchers'], summary['teams'], summary['hitters'])
print(f"\nSUCCESS: Dashboard successfully regenerated at: {out}")
