import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('reports/latest_results.json', 'r') as f:
    data = json.load(f)

pitchers_dict = {p['pitcher']: p for p in data['pitchers']}

top_teams = sorted(data['teams'], key=lambda x: x.get('stack_score', 0), reverse=True)[:6]

for t in top_teams:
    opp_p_name = t.get('opp_pitcher')
    opp_p = pitchers_dict.get(opp_p_name, {})
    
    print(f"\n=========================================")
    print(f"TEAM: {t['team']} (Score: {t.get('stack_score', 0):.1f})")
    print(f"  xwOBA: {t.get('team_xwoba', 0):.3f} | Conc: {t.get('power_concentration', 0):.3f}")
    print(f"  Implied Total: {t.get('implied_total')}")
    print(f"  Bullpen Fatigue: {t.get('bullpen_fatigue', 0):.1f} | Gassed: {t.get('is_gassed')}")
    flags = [k.replace('is_', '').upper() for k, v in t.items() if k.startswith('is_') and v and k not in ['is_gassed', 'is_fatigued', 'is_burst']]
    print(f"  Market Flags: {','.join(flags)}")
    
    print(f"  --- OPPOSING PITCHER ---")
    print(f"  Name: {opp_p_name}")
    print(f"  Alpha: {opp_p.get('alpha_score', 0):.1f} | SIERA: {opp_p.get('siera', 0):.2f} | CSW: {opp_p.get('csw', 0):.3f}")
    p_flags = []
    if opp_p.get('is_hazard'): p_flags.append('HAZARD')
    if opp_p.get('is_paradox'): p_flags.append('PARADOX')
    print(f"  Pitcher Flags: {','.join(p_flags)}")
