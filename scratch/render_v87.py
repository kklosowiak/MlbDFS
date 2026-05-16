import json
import os
import sys
from utils.dashboard_generator import DashboardGenerator

def render():
    with open('reports/latest_results.json') as f:
        data = json.load(f)
    
    # Re-run the weighting logic for each team to ensure v8.7 flags are present
    from engine.sharps_weighting import SharpsWeighting
    sharps = SharpsWeighting()
    
    t_reports = data.get('teams', [])
    sharp_map = {t['team']: t for t in t_reports}
    
    for t in t_reports:
        res = sharps.calculate_stack_score(
            team=t['team'],
            ml_move=t.get('ml_move', 0),
            tt_move=t.get('tt_move', 0),
            team_xwoba=t.get('team_xwoba', 0.330),
            power_concentration=t.get('power_concentration', 0.330),
            divergence=t.get('divergence', 0),
            is_whale=t.get('is_whale', False),
            is_storm=t.get('is_storm', False),
            is_steam=t.get('is_steam', False),
            is_shark=t.get('is_shark', False),
            is_sharp=t.get('is_sharp', False),
            is_burst=t.get('is_burst', False),
            implied_total=t.get('implied_total', 4.5),
            bullpen_fatigue=t.get('bullpen_fatigue', 0),
            pitcher_outs=t.get('pitcher_outs', 18.0)
        )
        t.update(res)
        t['stack_score'] = res['final']

    gen = DashboardGenerator()
    gen.generate_report(data.get('pitchers', []), t_reports, data.get('hitters', []))
    print("Dashboard generated: reports/dashboard.html")

if __name__ == "__main__":
    render()
