import os
import datetime
from config import config

class DashboardGenerator:
    def __init__(self):
        self.output_path = os.path.join(config.BASE_DIR, "reports", "dashboard.html")
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def generate_report(self, p_reports, t_reports, h_reports, skipped_events=None, median_k=5.5):
        """Generates a premium 3-Tab dashboard (Pitchers | Hitters | Teams)."""
        if skipped_events is None: skipped_events = []
        from engine.hitter_alpha import HitterAlpha
        emoji_key = HitterAlpha().get_emoji_key()
        
        abbrev_map = {
            'Arizona Diamondbacks': 'ARI', 'Atlanta Braves': 'ATL', 'Baltimore Orioles': 'BAL',
            'Boston Red Sox': 'BOS', 'Chicago Cubs': 'CHC', 'Chicago White Sox': 'CWS',
            'Cincinnati Reds': 'CIN', 'Cleveland Guardians': 'CLE', 'Colorado Rockies': 'COL',
            'Detroit Tigers': 'DET', 'Houston Astros': 'HOU', 'Kansas City Royals': 'KC',
            'Los Angeles Angels': 'LAA', 'Los Angeles Dodgers': 'LAD', 'Miami Marlins': 'MIA',
            'Milwaukee Brewers': 'MIL', 'Minnesota Twins': 'MIN', 'New York Mets': 'NYM',
            'New York Yankees': 'NYY', 'Oakland Athletics': 'OAK', 'Philadelphia Phillies': 'PHI',
            'Pittsburgh Pirates': 'PIT', 'San Diego Padres': 'SD', 'San Francisco Giants': 'SF',
            'Seattle Mariners': 'SEA', 'St. Louis Cardinals': 'STL', 'Tampa Bay Rays': 'TB',
            'Texas Rangers': 'TEX', 'Toronto Blue Jays': 'TOR', 'Washington Nationals': 'WSH',
            'Diamondbacks': 'ARI', 'Braves': 'ATL', 'Orioles': 'BAL', 'Red Sox': 'BOS',
            'Cubs': 'CHC', 'White Sox': 'CWS', 'Reds': 'CIN', 'Guardians': 'CLE',
            'Rockies': 'COL', 'Tigers': 'DET', 'Astros': 'HOU', 'Royals': 'KC',
            'Angels': 'LAA', 'Dodgers': 'LAD', 'Marlins': 'MIA', 'Brewers': 'MIL',
            'Twins': 'MIN', 'Mets': 'NYM', 'Yankees': 'NYY', 'Athletics': 'OAK',
            'Phillies': 'PHI', 'Pirates': 'PIT', 'Padres': 'SD', 'Giants': 'SF',
            'Mariners': 'SEA', 'Cardinals': 'STL', 'Rays': 'TB', 'Rangers': 'TEX',
            'Blue Jays': 'TOR', 'Nationals': 'WSH'
        }

        import json
        analysis_path = os.path.join(config.BASE_DIR, "reports", "slate_analysis.md")
        slate_analysis_md = "No analysis available yet."
        if os.path.exists(analysis_path):
            with open(analysis_path, "r", encoding="utf-8") as f:
                slate_analysis_md = f.read()
        safe_md = json.dumps(slate_analysis_md)
        
        # OMEGA v8.7: Final Intelligence Sort
        # Ensures highest-probability plays are always at the top after all gates/boosts
        t_reports = sorted(t_reports, key=lambda x: x.get('stack_score', 0), reverse=True)
        p_reports = sorted(p_reports, key=lambda x: x.get('alpha_score', 0), reverse=True)
        h_reports = sorted(h_reports, key=lambda x: x.get('player_score', 0), reverse=True)
        
        pitcher_rows = []
        for p in p_reports[:35]:
            row = f"""<tr class="{'god-tier' if p['alpha_score'] >= 85 else ''}">
<td class="score {'score-elite' if p['alpha_score'] >= 100 else ('score-high' if p['alpha_score'] >= 85 else '')}">{p['alpha_score']}</td>
<td class="metric-sub">{p.get('physics_score', '-')}</td>
<td class="metric-sub">{p.get('market_score', '-')}</td>
<td><div class="signals-container">
{ '<span class="signal-pill pill-target">🎯 TARGET</span>' if p.get('is_juiced_target') else '' }
{ '<span class="signal-pill pill-shark">🦈 SHARK</span>' if p.get('is_shark') else '' }
{ '<span class="signal-pill pill-storm">✨ DEBUT</span>' if p.get('is_debut') else '' }
{ '<span class="signal-pill pill-lowconf">🔍 LOW CONF</span>' if p.get('confidence') == 'low' else '' }
</div></td>
<td><div class="signals-container">
{ '<span class="signal-pill pill-paradox">⚠️ PARADOX</span>' if p.get('is_paradox') else '' }
{ '<span class="signal-pill pill-exhausted">🌋 HAZARD</span>' if p.get('is_hazard') else '' }
{ '<span class="signal-pill pill-trap">⚠️ TRAP</span>' if p.get('is_trap') else '' }
{ '<span class="signal-pill pill-neutral">⚖️ NEUTRAL K</span>' if abs(p.get('opponent_k_boost', 5.0)) <= 3.0 else '' }
{ '<span class="signal-pill pill-neutral">📉 CEILING</span>' if p.get('is_low_ceiling') else '' }
<span class="signal-pill pill-neutral">{p.get('weather_label', 'WEATHER: TBD')}</span>
</div></td>
<td><strong>{p['pitcher']}</strong> <span class="team-label">({abbrev_map.get(p['team'], p['team'])})</span></td>
<td><span class="vs">vs</span>{p['opponent']}</td>
<td class="metric"><b>{p.get('k_line') or '-'}</b><br><span style="font-size:0.8em; color: var(--text-secondary);">({'+' if isinstance(p.get('k_odds'), (int, float)) and p['k_odds'] > 0 else ''}{p.get('k_odds') or '-'})</span></td>
<td class="metric"><b>{p.get('outs_line') or '-'}</b><br><span style="font-size:0.8em; color: var(--text-secondary);">({'+' if isinstance(p.get('outs_odds'), (int, float)) and p['outs_odds'] > 0 else ''}{p.get('outs_odds') or '-'})</span></td>
</tr>"""
            pitcher_rows.append(row)

        hitter_rows = []
        for h in h_reports[:25]:
            platoon_mult = h.get('platoon_multiplier', 1.0)
            p_hand = h.get('pitch_hand', 'R')
            if platoon_mult > 1.0:
                pct = round((platoon_mult - 1.0) * 100)
                platoon_pill = f'<span class="signal-pill" style="background: linear-gradient(135deg, rgba(50, 215, 75, 0.15) 0%, rgba(50, 215, 75, 0.3) 100%); border: 1px solid #32d74b; color: #32d74b; font-weight:700; box-shadow: 0 0 8px rgba(50, 215, 75, 0.35);">⚡ VS {p_hand}HP (+{pct}%)</span>'
            elif platoon_mult < 1.0:
                pct = round((1.0 - platoon_mult) * 100)
                platoon_pill = f'<span class="signal-pill" style="background: linear-gradient(135deg, rgba(255, 69, 58, 0.15) 0%, rgba(255, 69, 58, 0.3) 100%); border: 1px solid #ff453a; color: #ff453a; font-weight:700; box-shadow: 0 0 8px rgba(255, 69, 58, 0.35);">📉 VS {p_hand}HP (-{pct}%)</span>'
            else:
                platoon_pill = ''

            row = f"""<tr class="{'god-tier' if h['player_score'] >= 85 else ''}">
<td class="score {'score-elite' if h['player_score'] >= 100 else ('score-high' if h['player_score'] >= 85 else '')}">{h['player_score']}</td>
<td><div class="signals-container">
{ '<span class="signal-pill pill-target">🎯 TARGET</span>' if h.get('is_juiced_target') else '' }
</div></td>
<td><div class="signals-container">
{ '<span class="signal-pill pill-neutral">🔋 POWER</span>' if h['matchup_xwoba'] >= 0.360 else '' }
{ '<span class="signal-pill pill-neutral">🏃\u200d♂️ THIEF</span>' if h.get('is_speed_target') else '' }
{ '<span class="signal-pill pill-target">♨️ HOT</span>' if h.get('is_hot') else '' }
{ '<span class="signal-pill pill-target">⚡ RADAR</span>' if h.get('matchup_boost', 1.0) > 1.0 else '' }
{ '<span class="signal-pill pill-weary">♨️ PEN ALERT</span>' if h.get('bullpen_fatigue', 0) >= 80 else '' }
{ platoon_pill }
</div></td>
<td><strong>{h['name']}</strong> <span class="team-label" style="font-weight: 800; color: #ff9f0a;">({h.get('bat_side', 'R')}B)</span> <span class="team-label">({abbrev_map.get(h['team'], h['team'])})</span></td>
<td><span class="vs">vs</span>{h.get('opp_pitcher', 'TBD')} <span class="team-label" style="font-weight: 800; color: #0a84ff;">({h.get('pitch_hand', 'R')}HP)</span> <span class="team-label">({abbrev_map.get(h.get('opponent', 'TBD'), 'TBD')})</span></td>
<td class="metric">{'+' if isinstance(h.get('ahr_price'), (int, float)) and h['ahr_price'] > 0 else ''}{h.get('ahr_price', '-')}</td>
<td class="metric"><b>{h.get('hit_line', '-')}</b><br><span style="font-size:0.8em; color: var(--text-secondary);">({'+' if isinstance(h.get('hits_price'), (int, float)) and h['hits_price'] > 0 else ''}{h.get('hits_price') or '-'})</span></td>
</tr>"""
            hitter_rows.append(row)

        team_rows = []
        for t in t_reports[:20]:
            div = t.get('divergence', 0)
            if div >= 15:
                div_pill = f'<span class="signal-pill" style="background:linear-gradient(135deg, rgba(50, 215, 75, 0.15) 0%, rgba(50, 215, 75, 0.3) 100%); border-color:#32d74b; color:#32d74b; font-weight:800; box-shadow:0 0 10px rgba(50, 215, 75, 0.35);">🟢 O-DIV (+{div}%)</span>'
            elif div <= -15:
                div_pill = f'<span class="signal-pill" style="background:linear-gradient(135deg, rgba(255, 69, 58, 0.15) 0%, rgba(255, 69, 58, 0.3) 100%); border-color:#ff453a; color:#ff453a; font-weight:800; box-shadow:0 0 10px rgba(255, 69, 58, 0.35);">🔴 U-DIV ({div}%)</span>'
            else:
                div_pill = ''

            row = f"""<tr class="{'god-tier' if t['stack_score'] >= 85 else ''}">
<td class="score {'score-elite' if t['stack_score'] >= 100 else ('score-high' if t['stack_score'] >= 85 else '')}">{t['stack_score']}</td>
<td class="score-physics">{t.get('physics_score', 0)}</td>
<td class="score-market">{t.get('market_score', 0)}</td>
<td><div class="signals-container">
{ '<span class="signal-pill pill-shark">🦈 SHARK</span>' if t.get('is_shark') else '' }
{ '<span class="signal-pill pill-storm">🌪️ STORM</span>' if t.get('is_storm') else '' }
{ '<span class="signal-pill pill-whale">🐋 WHALE</span>' if t.get('is_whale') else '' }
{ '<span class="signal-pill pill-sharp">🎰 SHARP</span>' if t.get('is_sharp') else '' }
{ '<span class="signal-pill pill-steam">💨 STEAM</span>' if t.get('is_steam') else '' }
{ '<span class="signal-pill pill-burst">⚡ BURST</span>' if t.get('is_burst') else '' }
{ '<span class="signal-pill pill-neutral" style="background: linear-gradient(135deg, rgba(0, 242, 254, 0.12) 0%, rgba(79, 172, 254, 0.12) 100%); border-color: #00f2fe; color: #00f2fe; text-shadow: 0 0 8px rgba(0, 242, 254, 0.4);">👁️ BLIND SPOT</span>' if (t.get('physics_score', 0) - t.get('market_score', 0)) >= 25 else '' }
{ '<span class="signal-pill pill-storm">✨ DEBUT TARGET</span>' if t.get('is_opp_debut') else '' }
</div></td>
<td><div class="signals-container">
{ '<span class="signal-pill pill-trap">⚠️ TRAP</span>' if t.get('is_trap') else '' }
{ '<span class="signal-pill pill-paradox">⚠️ PARADOX</span>' if t.get('is_paradox') else '' }
{ '<span class="signal-pill pill-exhausted">🔥 EXHAUSTED</span>' if t.get('bullpen_fatigue',0) >= 90 else ('<span class="signal-pill pill-gassed">♨️ GASSED</span>' if t.get('bullpen_fatigue',0) >= 80 else ('<span class="signal-pill pill-weary">♨️ WEARY</span>' if t.get('bullpen_fatigue',0) >= 70 else '')) }
{ (f'<span class="signal-pill pill-neutral">{t["total_signal"]}</span>' if t.get('total_signal') else '') }
{ div_pill }
</div></td>
<td><span class="team-label" style="font-size:1rem; font-weight:700; margin-left:0;">{t['team']}</span></td>
<td><span class="vs">vs</span>{t['opp_pitcher']} <span class="team-label">({abbrev_map.get(t['opponent'], 'TBD')})</span></td>
<td class="metric" style="font-weight:600;"><span class="{ 'val-up' if t.get('implied_total', 0) >= 4.2 else '' }">{t.get('implied_total', '-')}</span></td>
<td class="metric { 'val-up' if t['ml_move'] < 0 else ('val-down' if t['ml_move'] > 0 else 'val-even') }">{ '+' if t['ml_move'] > 0 else '' }{ t['ml_move'] if t['ml_move'] != 0 else 'EVEN' }</td>
<td class="metric { 'val-up' if t['tt_move'] > 0 else ('val-down' if t['tt_move'] < 0 else 'val-even') }">{ '+' if t['tt_move'] > 0 else '' }{ t['tt_move'] if t['tt_move'] != 0 else 'EVEN' }</td>
<td><div class="divergence-cell { 'val-up' if (t.get('divergence') or 0) > 0 else ('val-down' if (t.get('divergence') or 0) < 0 else 'val-even') }">
<span>{ '+' if (t.get('divergence') or 0) > 0 else '' }{ t.get('divergence', 0) }%</span>
</div></td>
</tr>"""
            team_rows.append(row)

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MLB Omega Engine</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        :root {{
            --bg: #000000;
            --surface: #1c1c1e;
            --surface-hover: #2c2c2e;
            --text-primary: #f5f5f7;
            --text-secondary: #86868b;
            --accent-blue: #0a84ff;
            --accent-green: #32d74b;
            --accent-red: #ff453a;
            --accent-orange: #ff9f0a;
            --accent-purple: #bf5af2;
            --border: rgba(255, 255, 255, 0.1);
            --radius-lg: 20px;
            --radius-md: 12px;
            --radius-sm: 8px;
        }}
        * {{ box-sizing: border-box; }}
        body {{
            background-color: var(--bg);
            background-image: url('omega_bg.png');
            background-size: cover;
            background-position: center;
            background-attachment: fixed;
            color: var(--text-primary);
            font-family: -apple-system, BlinkMacSystemFont, "Inter", "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 40px 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
            -webkit-font-smoothing: antialiased;
        }}
        .container {{ width: 100%; max-width: 1200px; }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            width: 100%;
            margin-bottom: 40px;
        }}
        .header-title {{
            display: flex;
            flex-direction: column;
            gap: 4px;
        }}
        .header h1 {{ 
            margin: 0; 
            font-weight: 800; 
            font-size: 2.8rem; 
            letter-spacing: -0.03em; 
            color: var(--text-primary); 
            text-shadow: 0 2px 15px rgba(0,0,0,0.8);
        }}
        .header-subtitle {{
            color: #ffffff;
            font-size: 1.1rem;
            font-weight: 600;
            letter-spacing: 0.02em;
            text-shadow: 0 2px 10px rgba(0,0,0,0.8);
            opacity: 0.95;
        }}
        .header-meta {{
            text-align: right;
            font-size: 0.95rem;
            color: #ffffff;
            font-weight: 700;
            letter-spacing: 0.02em;
            text-shadow: 0 2px 10px rgba(0,0,0,0.8);
            opacity: 0.9;
        }}
        
        /* Tabs System (Segmented Control style) */
        .tabs {{ 
            display: flex; 
            gap: 8px; 
            margin-bottom: 30px; 
            width: 100%; 
            background: #2c2c2e;
            padding: 6px;
            border-radius: var(--radius-md);
        }}
        .tab-btn {{
            flex: 1;
            padding: 12px 16px;
            background: transparent;
            border: none;
            color: var(--text-secondary);
            cursor: pointer;
            border-radius: var(--radius-sm);
            font-weight: 600;
            font-size: 0.95rem;
            transition: all 0.2s ease;
        }}
        .tab-btn:hover {{
            color: var(--text-primary);
        }}
        .tab-btn.active {{
            background: rgba(255, 255, 255, 0.12);
            color: var(--text-primary);
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
        }}
        .tab-content {{ display: none; width: 100%; }}
        .tab-content.active {{ display: block; animation: fadeIn 0.4s ease-out forwards; }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(8px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Cards & Tables */
        .card {{
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            padding: 30px;
            margin-bottom: 30px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.4);
        }}
        .card h2 {{
            text-align: center;
            margin-top: 0;
            margin-bottom: 24px;
            font-size: 1.6rem;
            font-weight: 700;
            letter-spacing: -0.02em;
            color: var(--text-primary);
            text-shadow: 0 1px 3px rgba(0,0,0,0.3);
        }}
        table {{ width: 100%; border-collapse: collapse; table-layout: auto; }}
        th {{ 
            text-align: left; 
            color: #ffffff; 
            font-size: 0.8rem; 
            font-weight: 700;
            padding: 12px 16px; 
            border-bottom: 1px solid var(--border); 
            text-transform: uppercase; 
            letter-spacing: 0.08em;
            opacity: 0.9;
        }}
        td {{ 
            padding: 16px; 
            border-bottom: 1px solid rgba(255, 255, 255, 0.04); 
            font-size: 0.95rem; 
            font-weight: 500;
            vertical-align: middle;
        }}
        tr:last-child td {{ border-bottom: none; }}
        tr {{
            transition: transform 0.2s cubic-bezier(0.25, 0.8, 0.25, 1), background-color 0.2s ease;
        }}
        tr:hover {{
            transform: translateX(4px);
        }}
        tr:hover td {{
            background: rgba(255, 255, 255, 0.035) !important;
            border-bottom-color: rgba(255, 255, 255, 0.08);
        }}
        
        .score {{ 
            font-weight: 700; 
            font-size: 1.1rem; 
        }}
        .score-balanced {{ color: var(--accent-blue); }}
        .score-physics-heavy {{ color: var(--accent-green); text-shadow: 0 0 10px rgba(50, 215, 75, 0.3); }}
        .score-market-heavy {{ color: var(--accent-purple); text-shadow: 0 0 10px rgba(191, 90, 242, 0.3); }}
        .score-trap {{ color: var(--accent-red); text-shadow: 0 0 10px rgba(255, 69, 58, 0.3); text-decoration: line-through; opacity: 0.8; }}
        
        .status-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 6px;
            font-size: 0.75rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 4px;
        }}
        .badge-lock {{ background: var(--accent-blue); color: #fff; box-shadow: 0 0 15px rgba(10, 132, 255, 0.5); }}
        .badge-leverage {{ background: var(--accent-green); color: #fff; box-shadow: 0 0 15px rgba(50, 215, 75, 0.5); }}
        .badge-steam {{ background: var(--accent-purple); color: #fff; opacity: 0.9; }}
        .badge-trap {{ background: var(--accent-red); color: #fff; animation: pulse 2s infinite; }}
        
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.6; }}
            100% {{ opacity: 1; }}
        }}

        .metric {{ font-variant-numeric: tabular-nums; color: var(--text-secondary); }}
        .metric b {{ color: var(--text-primary); }}
        .vs {{ color: var(--text-secondary); font-size: 0.85rem; margin: 0 6px; font-weight: 400; }}
        
        .god-tier td {{
            background: rgba(10, 132, 255, 0.03);
        }}
        .god-tier td:first-child {{
            border-left: 3px solid var(--accent-blue);
        }}
        
        .team-label {{
            font-size: 0.8em;
            color: var(--text-secondary);
            font-weight: 500;
            margin-left: 2px;
        }}
        
        /* Pills & Badges (Apple Style) */
        .signals-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
            max-width: 280px;
        }}
        .signal-pill {{
            display: inline-flex;
            align-items: center;
            font-size: 0.7rem;
            font-weight: 600;
            padding: 4px 8px;
            border-radius: var(--radius-sm);
            text-transform: uppercase;
            letter-spacing: 0.02em;
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
        }}
        /* Semantic pill colors */
        .pill-target {{ background: rgba(10, 132, 255, 0.15); color: var(--accent-blue); }}
        .pill-shark {{ background: rgba(10, 132, 255, 0.15); color: var(--accent-blue); }}
        .pill-storm {{ background: rgba(139, 92, 246, 0.2); color: #a78bfa; border: 1px solid rgba(139, 92, 246, 0.3); }}
        .pill-sharp {{ background: rgba(20, 184, 166, 0.2); color: #2dd4bf; border: 1px solid rgba(20, 184, 166, 0.3); }}
        .pill-whale {{ background: rgba(50, 215, 75, 0.15); color: var(--accent-green); }}
        .pill-steam {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }}
        .pill-burst {{ background: rgba(255, 214, 10, 0.15); color: #ffd60a; }}
        .pill-lowconf {{ background: rgba(255, 69, 58, 0.15); color: var(--accent-red); }}
        .pill-paradox {{ background: rgba(255, 159, 10, 0.15); color: var(--accent-orange); }}
        .pill-trap {{ background: rgba(255, 69, 58, 0.15); color: var(--accent-red); }}
        .pill-exhausted {{ background: rgba(255, 69, 58, 0.15); color: var(--accent-red); }}
        .pill-weary {{ background: rgba(255, 159, 10, 0.15); color: var(--accent-orange); }}
        .pill-gassed {{ background: rgba(255, 69, 58, 0.15); color: var(--accent-red); }}
        .pill-neutral {{ background: rgba(255, 255, 255, 0.1); color: var(--text-secondary); }}

        /* Legend */
        .legend {{
            margin-bottom: 40px;
            padding: 30px;
            background: var(--surface);
            border: 1px solid var(--border);
            border-radius: var(--radius-lg);
            width: 100%;
        }}
        .legend-content {{
            display: flex;
            flex-wrap: wrap;
            gap: 40px;
            justify-content: space-between;
        }}
        .legend-group {{ display: flex; flex-direction: column; gap: 10px; }}
        .legend-title {{ 
            font-size: 0.85rem; 
            font-weight: 800; 
            text-transform: uppercase; 
            color: var(--accent-blue); 
            letter-spacing: 0.08em; 
            margin-bottom: 6px; 
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 0.9rem;
            color: rgba(255, 255, 255, 0.9);
            font-weight: 500;
        }}
        .legend-item b {{ color: var(--text-primary); }}
        .legend h2 {{
            text-align: center;
            margin-top: 0;
            margin-bottom: 24px;
            font-size: 1.2rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--text-secondary);
            border-bottom: 1px solid var(--border);
            padding-bottom: 12px;
        }}
        
        /* Divergence Cells */
        .divergence-cell {{ display: flex; align-items: center; gap: 8px; font-weight: 600; font-variant-numeric: tabular-nums; }}
        .val-up {{ color: var(--accent-green); }}
        .val-down {{ color: var(--accent-red); }}
        .val-even {{ color: var(--text-secondary); }}
        
        /* Markdown container */
        /* Model Analysis Premium Banner & Cards */
        #analysis-content {{
            line-height: 1.75;
            font-size: 0.98rem;
            color: var(--text-primary);
            display: flex;
            flex-direction: column;
            gap: 24px;
        }}
        .analysis-banner {{
            background: linear-gradient(135deg, rgba(10, 132, 255, 0.08) 0%, rgba(0, 242, 254, 0.03) 100%);
            border: 1px solid rgba(10, 132, 255, 0.15);
            border-radius: var(--radius-lg);
            padding: 35px 40px;
            margin-bottom: 8px;
            box-shadow: var(--shadow-lg);
            position: relative;
            overflow: hidden;
            backdrop-filter: blur(20px);
        }}
        .analysis-banner h1 {{
            font-size: 2.3rem;
            font-weight: 800;
            color: #fff;
            margin: 0 0 10px 0;
            letter-spacing: -0.02em;
            text-shadow: 0 0 20px rgba(10, 132, 255, 0.3);
        }}
        .analysis-banner .banner-badge {{
            display: inline-block;
            padding: 6px 14px;
            background: rgba(10, 132, 255, 0.12);
            border: 1px solid rgba(10, 132, 255, 0.3);
            color: var(--accent-blue);
            border-radius: 20px;
            font-size: 0.72rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            margin-bottom: 14px;
            text-transform: uppercase;
            box-shadow: 0 0 15px rgba(10, 132, 255, 0.15);
        }}
        .analysis-banner .banner-subtitle {{
            font-size: 1.05rem;
            color: var(--text-secondary);
            margin: 0;
            font-weight: 500;
        }}
        .analysis-card {{
            margin-bottom: 0px;
            padding: 0 !important;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.04);
            box-shadow: var(--shadow-md);
            background: rgba(255, 255, 255, 0.015);
            backdrop-filter: blur(20px);
        }}
        .analysis-card-header {{
            background: rgba(255, 255, 255, 0.01);
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            padding: 22px 30px;
        }}
        .analysis-card-header h2 {{
            font-size: 1.35rem !important;
            font-weight: 800 !important;
            color: #fff !important;
            margin: 0 !important;
            border-bottom: none !important;
            padding: 0 !important;
            letter-spacing: -0.01em !important;
        }}
        .analysis-card-body {{
            padding: 30px;
        }}
        #analysis-content h3 {{
            font-size: 1.15rem;
            font-weight: 700;
            color: var(--accent-blue);
            margin-top: 1.5em;
            margin-bottom: 0.8em;
            letter-spacing: -0.01em;
        }}
        #analysis-content p {{
            color: rgba(255, 255, 255, 0.8);
            margin-bottom: 1.3em;
        }}
        #analysis-content blockquote {{
            background: rgba(10, 132, 255, 0.04);
            border-left: 3px solid var(--accent-blue);
            padding: 16px 20px;
            border-radius: 4px;
            margin: 1.5em 0;
            color: var(--text-primary);
        }}
        #analysis-content blockquote p {{
            margin: 0;
            font-size: 0.95rem;
            font-style: italic;
            color: var(--text-primary);
        }}
        #analysis-content ul {{
            list-style: none;
            padding-left: 0;
            margin-bottom: 1.5em;
        }}
        #analysis-content li {{
            position: relative;
            padding-left: 22px;
            margin-bottom: 8px;
            font-size: 0.96rem;
            color: rgba(255, 255, 255, 0.8);
        }}
        #analysis-content li::before {{
            content: "•";
            position: absolute;
            left: 6px;
            color: var(--accent-blue);
            font-weight: 900;
            font-size: 1.2rem;
            top: -2px;
        }}
        #analysis-content table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            border-radius: 8px;
            overflow: hidden;
            border: 1px solid rgba(255, 255, 255, 0.04);
            margin-bottom: 2em;
            background: rgba(255, 255, 255, 0.005);
        }}
        #analysis-content th {{
            background: rgba(255, 255, 255, 0.02);
            font-weight: 700;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            color: var(--text-secondary);
            border: none;
            border-bottom: 1px solid rgba(255, 255, 255, 0.06);
            padding: 14px 16px;
            text-align: left;
        }}
        #analysis-content td {{
            padding: 14px 16px;
            border: none;
            border-bottom: 1px solid rgba(255, 255, 255, 0.04);
            font-size: 0.93rem;
            color: var(--text-primary);
        }}
        #analysis-content tr:last-child td {{
            border-bottom: none;
        }}
        #analysis-content tr:hover td {{
            background: rgba(255, 255, 255, 0.015);
        }}
        #analysis-content strong {{
            color: #fff;
            font-weight: 600;
        }}
        
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <h1>OMEGA Engine</h1>
                <div class="header-subtitle">MLB Daily Fantasy & Market Divergence</div>
            </div>
            <div class="header-meta">
                v5.0 MASTER CONVERGENCE<br>
                <span style="color: var(--text-primary);">{datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p ET")}</span>
            </div>
        </div>
        
        <div class="legend">
            <h2>SIGNALS</h2>
            <div class="legend-content">
                <div class="legend-group">
                    <div class="legend-title">Market Alpha</div>
                    <div class="legend-item"><span class="signal-pill pill-whale">🐋 WHALE</span> <b>+15%:</b> Major Conviction</div>
                    <div class="legend-item"><span class="signal-pill pill-sharp">🎰 SHARP</span> <b>Smart Money:</b> Pro Confirmed</div>
                    <div class="legend-item"><span class="signal-pill pill-storm">🌪️ STORM</span> Correlated Sharp Action</div>
                    <div class="legend-item"><span class="signal-pill pill-steam">💨 STEAM</span> Heavy Line Movement</div>
                </div>
                <div class="legend-group">
                    <div class="legend-title">Model Beta</div>
                    <div class="legend-item"><span class="signal-pill pill-target">🎯 TARGET</span> Sharp / Power Play</div>
                    <div class="legend-item"><span class="signal-pill pill-burst">⚡ BURST</span> High power / Early explosion</div>
                    <div class="legend-item"><span class="signal-pill pill-neutral">📉 CEILING</span> Low strikeout upside</div>
                </div>
                <div class="legend-group">
                    <div class="legend-title">Risk & Context</div>
                    <div class="legend-item"><span class="signal-pill pill-paradox">⚠️ PARADOX</span> Conflict (Pitcher vs. Stack)</div>
                    <div class="legend-item"><span class="signal-pill pill-exhausted">🔥 EXHAUSTED</span> <b>90+:</b> Relievers Taxed (198+ pitches)</div>
                    <div class="legend-item"><span class="signal-pill pill-gassed">♨️ GASSED</span> <b>80+:</b> Heavy Fatigue (176+ pitches)</div>
                    <div class="legend-item"><span class="signal-pill pill-weary">♨️ WEARY</span> <b>70+:</b> Bullpen Weary (154+ pitches)</div>
                    <div class="legend-item"><span class="signal-pill pill-trap">⚠️ TRAP</span> Suspicious prop lines</div>
                </div>
            </div>
        </div>

        <div class="tabs">
            <button class="tab-btn active" onclick="openTab(event, 'pitchers')">Pitchers Matrix</button>
            <button class="tab-btn" onclick="openTab(event, 'hitters')">Hitters Matrix</button>
            <button class="tab-btn" onclick="openTab(event, 'teams')">Teams Matrix</button>
            <button class="tab-btn" onclick="openTab(event, 'analysis')">Model Analysis</button>
        </div>

        <!-- PITCHERS TAB -->
        <div id="pitchers" class="tab-content active">
            <div class="card">
                <h2>Elite Pitcher Alpha Matrix</h2>
                <table>
                    <thead>
                        <tr><th>OMEGA</th><th>PHY</th><th>MKT</th><th>ALPHA SIGNALS</th><th>ALPHA CONTEXT</th><th>PITCHER</th><th>vs OPPONENT</th><th>K-PROP</th><th>OUTS</th></tr>
                    </thead>
                    <tbody>
                        {"".join(pitcher_rows)}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- HITTERS TAB -->
        <div id="hitters" class="tab-content">
            <div class="card">
                <h2>Power & Alpha Matrix</h2>
                <table>
                    <thead>
                        <tr><th>OMEGA</th><th>ALPHA SIGNALS</th><th>ALPHA CONTEXT</th><th>PLAYER</th><th>vs PITCHER</th><th>HR-PROP</th><th>BASES</th></tr>
                    </thead>
                    <tbody>
                        {"".join(hitter_rows)}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- TEAMS TAB -->
        <div id="teams" class="tab-content">
            <div class="card">
                <h2>Market Sentiment Matrix</h2>
                <table>
                    <thead>
                        <tr><th>OMEGA</th><th>PHY</th><th>MKT</th><th>ALPHA SIGNALS</th><th>ALPHA CONTEXT</th><th>TEAM</th><th>vs PITCHER</th><th>ITT</th><th>ML MOVE</th><th>TT MOVE</th><th>DIVERGENCE</th></tr>
                    </thead>
                    <tbody>
                        {"".join(team_rows)}
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- ANALYSIS TAB -->
        <div id="analysis" class="tab-content">
            <div id="analysis-content">
                Loading analysis...
            </div>
        </div>


    </div>

    <script>
        // Tab switching logic
        function openTab(evt, tabName) {{
            var i, tabcontent, tablinks;
            tabcontent = document.getElementsByClassName("tab-content");
            for (i = 0; i < tabcontent.length; i++) {{
                tabcontent[i].style.display = "none";
                tabcontent[i].classList.remove("active");
            }}
            tablinks = document.getElementsByClassName("tab-btn");
            for (i = 0; i < tablinks.length; i++) {{
                tablinks[i].classList.remove("active");
            }}
            document.getElementById(tabName).style.display = "block";
            document.getElementById(tabName).classList.add("active");
            evt.currentTarget.classList.add("active");
        }}
        
        // Render Markdown Analysis
        const markdownData = {safe_md};
        document.addEventListener('DOMContentLoaded', () => {{
            if (typeof marked !== 'undefined') {{
                const rawHTML = marked.parse(markdownData);
                const tempDiv = document.createElement('div');
                tempDiv.innerHTML = rawHTML;

                const container = document.getElementById('analysis-content');
                container.innerHTML = ''; // clear loading

                // Let's group children by H2 elements into separate visual cards!
                let currentCard = null;
                let cardBody = null;

                // Render banner first if H1 exists
                const h1 = tempDiv.querySelector('h1');
                if (h1) {{
                    const banner = document.createElement('div');
                    banner.className = 'analysis-banner';
                    banner.innerHTML = `
                        <div class="banner-badge">SLATE INTELLIGENCE BRIEFING</div>
                        <h1>${{h1.innerText.replace('⚾ ', '').replace(' OMEGA ', ' ')}}</h1>
                        <div class="banner-subtitle">Dynamic quantitative signals, high-leverage pitcher tiers, and stadium physics calibrated live.</div>
                    `;
                    container.appendChild(banner);
                }}

                // Loop through elements and create cards
                Array.from(tempDiv.children).forEach(el => {{
                    if (el.tagName === 'H1' || (el.tagName === 'P' && el === tempDiv.querySelector('p')) || (el.tagName === 'P' && el.innerText.startsWith('Generated:'))) {{
                        // skip banner elements and timestamp
                        return;
                    }}

                    if (el.tagName === 'H2') {{
                        // Start a new card!
                        currentCard = document.createElement('div');
                        currentCard.className = 'card analysis-card';
                        
                        const header = document.createElement('div');
                        header.className = 'analysis-card-header';
                        header.innerHTML = `<h2>${{el.innerHTML}}</h2>`;
                        currentCard.appendChild(header);

                        cardBody = document.createElement('div');
                        cardBody.className = 'analysis-card-body';
                        currentCard.appendChild(cardBody);

                        container.appendChild(currentCard);
                    }} else if (el.tagName === 'HR') {{
                        // skip horizontal rules as cards act as dividers
                        return;
                    }} else {{
                        // Append to active card body, or directly to container if no card yet
                        if (cardBody) {{
                            cardBody.appendChild(el.cloneNode(true));
                        }} else {{
                            container.appendChild(el.cloneNode(true));
                        }}
                    }}
                }});
            }} else {{
                document.getElementById('analysis-content').innerHTML = "<p>Error: Could not load markdown parser.</p>";
            }}
        }});
    </script>
</body>
</html>
"""
        with open(self.output_path, "w", encoding="utf-8") as f:
            f.write(html)
            
        # OMEGA v4.6.3: Mirror to user's active sports_agent path
        try:
            mirror_path = os.path.join(os.path.dirname(config.BASE_DIR), "sports_agent", "konrad_sharp_model_v45.html")
            os.makedirs(os.path.dirname(mirror_path), exist_ok=True)
            with open(mirror_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[SYNC]: Mirrored dashboard to {mirror_path}")
        except Exception as e:
            print(f"[SYNC ERROR]: Could not mirror to sports_agent: {e}")
            
        return self.output_path
