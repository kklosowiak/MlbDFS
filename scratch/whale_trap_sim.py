import json
import os
from datetime import datetime, timedelta
from utils.audit_engine import AuditEngine

def run_simulation():
    dates = ['2026-05-13', '2026-05-14', '2026-05-15']
    audit = AuditEngine()
    
    print(f"{'Date':12} | {'Team':20} | {'Score':6} | {'NewScore':8} | {'P-Raw':6} | {'M-Raw':6} | {'Trap?':5} | {'Runs':4}")
    print("-" * 85)
    
    for d in dates:
        path = f'reports/archive/results_{d}.json'
        if d == '2026-05-15':
            path = 'reports/latest_results.json'
            
        if not os.path.exists(path):
            continue
            
        with open(path) as f:
            data = json.load(f)
            
        actuals = audit.fetch_results(date=d)
        teams = data.get('teams', [])
        
        from engine.sharps_weighting import SharpsWeighting
        sharps = SharpsWeighting()
        
        for t in teams[:15]: # Check top 15 each day
            # Get inputs from archived team data
            # Note: We use the archived fields to recreate the call
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
            
            new_score = res['final']
            p_score = res['physics']
            m_score = res['market']
            p_raw = p_score / 0.4
            m_raw = m_score / 0.2
            
            is_trap = p_raw < 30.0 and m_raw > 80.0
            
            # Get actual runs
            actual_runs = actuals.get(t['team'], {}).get('runs', 0)
            
            if is_trap or t['stack_score'] > 95:
                trap_str = "YES" if is_trap else "no"
                print(f"{d:12} | {t['team']:20} | {t['stack_score']:6.1f} | {new_score:8.1f} | {p_raw:6.1f} | {m_raw:6.1f} | {trap_str:5} | {actual_runs:4}")

if __name__ == "__main__":
    run_simulation()
