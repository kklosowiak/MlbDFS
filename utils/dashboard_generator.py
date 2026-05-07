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
        
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MLB Omega DFS + Betting engine v.5.0</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;800&display=swap" rel="stylesheet">
    <style>
        :root {{
            --bg: #050505;
            --accent: #00ffff;
            --glass: rgba(255, 255, 255, 0.05);
            --border: rgba(255, 255, 255, 0.1);
            --card-bg: #111;
        }}
        body {{
            background: var(--bg);
            color: #e0e0e0;
            font-family: 'Outfit', sans-serif;
            margin: 0;
            padding: 20px;
            display: flex;
            flex-direction: column;
            align-items: center;
        }}
        .container {{ width: 100%; max-width: 1400px; }}
        .header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            width: 100%;
            border-bottom: 2px solid var(--accent);
            padding-bottom: 15px;
            margin-bottom: 25px;
        }}
        .header h1 {{ margin: 0; font-weight: 800; letter-spacing: 2px; color: var(--accent); text-transform: uppercase; }}
        
        /* Tabs System */
        .tabs {{ display: flex; gap: 10px; margin-bottom: 25px; width: 100%; }}
        .tab-btn {{
            flex: 1;
            padding: 18px;
            background: var(--glass);
            border: 1px solid var(--border);
            color: #fff;
            cursor: pointer;
            border-radius: 12px;
            font-weight: 700;
            transition: all 0.3s;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        .tab-btn.active {{
            background: var(--accent);
            color: #000;
            border-color: var(--accent);
            box-shadow: 0 0 25px rgba(0, 255, 255, 0.4);
        }}
        .tab-content {{ display: none; width: 100%; }}
        .tab-content.active {{ display: block; animation: fadeIn 0.4s ease-out; }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Table & Card Styles */
        .card {{
            background: var(--card-bg);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 25px;
            margin-bottom: 30px;
        }}
        table {{ width: 100%; border-collapse: collapse; table-layout: auto; }}
        th {{ text-align: left; opacity: 0.5; font-size: 0.7rem; padding: 12px; border-bottom: 1px solid var(--border); text-transform: uppercase; }}
        th:nth-child(2), td:nth-child(2) {{ min-width: 140px; padding-right: 5px; }}
        th:nth-child(3), td:nth-child(3) {{ min-width: 220px; padding-right: 5px; }}
        td {{ padding: 12px 15px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); font-size: 0.9rem; }}
        .score {{ font-weight: 800; color: var(--accent); font-size: 1.2rem; font-family: 'Courier New', monospace; }}
        .score.overdrive {{ 
            background: linear-gradient(135deg, rgba(0, 255, 255, 0.2), rgba(0, 200, 255, 0.1)) !important;
            color: #00ffff !important;
            text-shadow: 0 0 15px rgba(0, 255, 255, 0.6);
            border: 1px solid rgba(0, 255, 255, 0.4);
            box-shadow: inset 0 0 15px rgba(0, 255, 255, 0.2);
            padding: 4px 8px;
            border-radius: 6px;
            animation: pulse-cyan 2s infinite ease-in-out;
        }}
        @keyframes pulse-cyan {{
            0% {{ box-shadow: inset 0 0 15px rgba(0, 255, 255, 0.2); }}
            50% {{ box-shadow: inset 0 0 25px rgba(0, 255, 255, 0.4); }}
            100% {{ box-shadow: inset 0 0 15px rgba(0, 255, 255, 0.2); }}
        }}
        .metric {{ font-family: 'Courier New', monospace; font-size: 0.85rem; color: #888; }}
        .metric b {{ color: #fff; }}
        .vs {{ opacity: 0.4; font-size: 0.8rem; margin: 0 5px; }}
        
        .god-tier {{ 
            background: rgba(0, 255, 255, 0.05) !important; 
            border-left: 4px solid var(--accent) !important;
        }}
        
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 12px;
            margin-bottom: 30px;
            justify-content: center;
        }}
        .legend-item {{
            background: var(--glass);
            padding: 8px 15px;
            border-radius: 20px;
            font-size: 0.75rem;
            border: 1px solid var(--border);
            color: #888;
        }}
        .legend-item b {{ color: var(--accent); }}
        
        .signals-container {{
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            max-width: 260px;
        }}
        .signal-pill {{
            display: inline-block;
            font-size: 8px;
            font-weight: 800;
            padding: 3px 6px;
            border-radius: 4px;
            text-transform: uppercase;
            background: #000;
            border: 1px solid var(--accent);
            color: var(--accent);
            white-space: nowrap;
        }}

        .status-confirmed {{ color: #00ff88; font-weight: 800; font-size: 0.7rem; }}
        .status-unconfirmed {{ color: #ff3e3e; font-weight: 800; font-size: 0.7rem; }}
        
        /* Move Coloring (Neon) */
        .move-up {{ color: #00ff88 !important; text-shadow: 0 0 5px rgba(0, 255, 136, 0.4); }}
        .move-down {{ color: #ff4444 !important; text-shadow: 0 0 5px rgba(255, 68, 68, 0.4); }}
        .move-even {{ color: #666 !important; }}
        
        .trend-surging {{ color: #ff00ff !important; font-weight: 800; animation: pulse-magenta 2s infinite; }}
        .trend-fading {{ color: #00bfff !important; font-weight: 800; opacity: 0.8; }}
        .divergence-cell {{ white-space: nowrap; display: flex; align-items: center; gap: 8px; }}
        @keyframes pulse-magenta {{
            0% {{ text-shadow: 0 0 5px rgba(255, 0, 255, 0.2); }}
            50% {{ text-shadow: 0 0 15px rgba(255, 0, 255, 0.6); }}
            100% {{ text-shadow: 0 0 5px rgba(255, 0, 255, 0.2); }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>MLB Omega DFS + Betting engine v.5.0</h1>
            <div style="text-align: right;">
                <small style="opacity: 0.5;">FINAL HANDOVER: v5.0 MASTER CONVERGENCE</small><br>
                <small style="color: var(--accent);">Last Sync: {datetime.datetime.now().strftime("%Y-%m-%d %I:%M %p ET")}</small>
            </div>
        </div>

            <div class="legend-item" style="border-color: var(--accent); color: var(--accent);">⚡ <b>ALPHA (+15%):</b> Market Leaders (Storm, Whale, Shark, Target, Steam).</div>
            <div class="legend-item">🔹 <b>BETA (+5%):</b> Supporting signals (Sharp, Power, Engine).</div>
            <div class="legend-item" style="color: #ff00ff; border-color: #ff00ff;">🌪️ <b>STORM:</b> Correlated Sharp Action (ML + Total).</div>
            <div class="legend-item" style="color: #ff4500; border-color: #ff4500;">💨 <b>STEAM:</b> Heavy Line Movement + Consensus Money.</div>
            <div class="legend-item" style="color: #ff8c00;">♨️ <b>PEN ALERT:</b> Bullpen fatigue detected. Red = Gassed.</div>
            <div class="legend-item" style="color: #ff4500;">⚠️ <b>PARADOX:</b> Conflict detected (Pitcher vs. Top Stack).</div>
            <div class="legend-item" style="color: #00ced1;">📉 <b>CEILING:</b> Low strikeout upside detected.</div>
            <div class="legend-item" style="color: #ffff00; border-color: #ffff00;">⚡ <b>BURST:</b> High power concentration or Early Explosion detected.</div>

        <div class="tabs">
            <button class="tab-btn active" onclick="openTab(event, 'pitchers')">Pitchers Matrix</button>
            <button class="tab-btn" onclick="openTab(event, 'hitters')">Hitters Matrix</button>
            <button class="tab-btn" onclick="openTab(event, 'teams')">Teams Matrix</button>
        </div>

        <!-- PITCHERS TAB -->
        <div id="pitchers" class="tab-content active">
            <div class="card">
                <h2>Elite Pitcher Alpha Matrix</h2>
                <table>
                    <thead>
                        <tr><th>OMEGA</th><th>ALPHA SIGNALS</th><th>ALPHA CONTEXT</th><th>PITCHER</th><th>vs OPPONENT</th><th>K-PROP</th><th>OUTS</th></tr>
                    </thead>
                    <tbody>
                        {"".join([f"<tr class='{'god-tier' if p['alpha_score'] >= 85 else ''}'>"
                                  f"<td class='score { 'overdrive' if p['alpha_score'] >= 100 else '' }'>{p['alpha_score']}</td>"
                                  f"<td><div class='signals-container'>"
                                  f"{ '<span class=\"signal-pill\">🎯 TARGET</span>' if p.get('is_juiced_target') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#00bfff; color:#00bfff;\">🦈 SHARK</span>' if p.get('is_shark') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ff00ff; color:#ff00ff;\">✨ DEBUT</span>' if p.get('is_debut') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ff3e3e; color:#ff3e3e; background:rgba(255,62,62,0.1);\">🔍 LOW CONF</span>' if p.get('confidence') == 'low' else '' }"
                                  f"</div></td>"
                                  f"<td><div class='signals-container'>"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ff4500; color:#ff4500;\">⚠️ PARADOX</span>' if p.get('is_paradox') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ff8c00; color:#ff8c00;\">🌋 HAZARD</span>' if p.get('is_hazard') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#00fa9a; color:#00fa9a;\">🏔️ ALTITUDE</span>' if p.get('is_coors') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#00ced1; color:#00ced1;\">📉 CEILING</span>' if p.get('is_low_ceiling') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#aaa; color:#aaa;\">🏗️ ENGINE</span>' if (p.get('outs_line') or 0) >= 17.5 else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#aaa; color:#aaa;\">🎰 SHARP</span>' if (p.get('divergence') or 0) >= 10 and not (p.get('divergence') or 0) >= 15 else '' }"
                                  f"<span class='signal-pill' style='border-color:#888; color:#888;'>{p.get('weather_label', 'WEATHER: TBD')}</span>"
                                  f"<span class='signal-pill' style='border-color:#888; color:#888;'>UMP: {p.get('umpire_name', 'TBD')}</span>"
                                  f"</div></td>"
                                  f"<td><strong>{p['pitcher']}</strong></td>"
                                  f"<td><span class='vs'>vs</span>{p['opponent']}</td>"
                                  f"<td class='metric'><b>{p.get('k_line') or '-'}</b> K <span style='opacity:0.6; font-size:0.75em;'>({p.get('k_odds') or '-'})</span></td>"
                                  f"<td class='metric'><b>{p.get('outs_line') or '-'}</b> OUTS <span style='opacity:0.6; font-size:0.75em;'>({p.get('outs_odds') or '-'})</span></td>"
                                  f"</tr>" for p in p_reports[:35]])}
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
                        <tr><th>OMEGA</th><th>ALPHA SIGNALS</th><th>ALPHA CONTEXT</th><th>PLAYER</th><th>TEAM</th><th>vs PITCHER</th><th>HR-PROP</th><th>BASES</th></tr>
                    </thead>
                    <tbody>
                        {"".join([f"<tr class='{'god-tier' if h['player_score'] >= 85 else ''}'>"
                                  f"<td class='score { 'overdrive' if h['player_score'] >= 100 else '' }'>{h['player_score']}</td>"
                                  f"<td><div class='signals-container'>"
                                  f"{ '<span class=\"signal-pill\">🎯 TARGET</span>' if h.get('is_juiced_target') else '' }"
                                  f"</div></td>"
                                  f"<td><div class='signals-container'>"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#aaa; color:#aaa;\">🔋 POWER</span>' if h['matchup_xwoba'] >= 0.360 else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#aaa; color:#aaa;\">🏃‍♂️ THIEF</span>' if h.get('is_speed_target') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#aaa; color:#aaa;\">♨️ HOT</span>' if h.get('is_hot') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ff8c00; color:#ff8c00;\">♨️ PEN ALERT</span>' if h.get('bullpen_fatigue', 0) >= 80 else '' }"
                                  f"</div></td>"
                                  f"<td><strong>{h['name']}</strong></td>"
                                  f"<td>{abbrev_map.get(h['team'], h['team'])}</td>"
                                  f"<td><span class='vs'>vs</span>{h.get('opp_pitcher', 'TBD')} ({abbrev_map.get(h.get('opponent', 'TBD'), 'TBD')})</td>"
                                  f"<td class='metric'>{h['ahr_price']}</td>"
                                  f"<td class='metric'><b>{h.get('hit_line', '-')}</b> TB <span style='opacity:0.6; font-size:0.75em;'>({h.get('hits_price') or '-'})</span></td>"
                                  f"</tr>" for h in h_reports[:25]])}
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
                        <tr><th>OMEGA</th><th>ALPHA SIGNALS</th><th>ALPHA CONTEXT</th><th>TEAM</th><th>vs PITCHER</th><th>ITT</th><th>ML MOVE</th><th>TT MOVE</th><th>DIVERGENCE</th></tr>
                    </thead>
                    <tbody>
                        {"".join([f"<tr class='{'god-tier' if t['stack_score'] >= 85 else ''}'>"
                                  f"<td class='score { 'overdrive' if t['stack_score'] >= 100 else '' }'>{t['stack_score']}</td>"
                                  f"<td><div class='signals-container'>"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#00bfff; color:#00bfff;\">🦈 SHARK</span>' if t.get('is_shark') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ff00ff; color:#ff00ff;\">🌪️ STORM</span>' if t.get('is_storm') else '' }"
                                  f"{ '<span class=\"signal-pill\">🐋 WHALE</span>' if t.get('is_whale') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ff4500; color:#ff4500;\">💨 STEAM</span>' if t.get('is_steam') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ffff00; color:#ffff00;\">⚡ BURST</span>' if t.get('is_burst') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ff3e3e; color:#ff3e3e; background:rgba(255,62,62,0.1);\">🔍 LOW CONF</span>' if t.get('confidence') == 'low' else '' }"
                                  f"</div></td>"
                                  f"<td><div class='signals-container'>"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#aaa; color:#aaa;\">🎰 SHARP</span>' if t.get('is_sharp') else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#aaa; color:#aaa;\">🚂 TRAIN</span>' if t['stack_score'] >= 90 else '' }"
                                  f"{ '<span class=\"signal-pill\" style=\"border-color:#ff8c00; color:#ff8c00;\">♨️ PEN ALERT</span>' if t.get('is_fatigued') or t.get('is_gassed') else '' }"
                                  + (f'<span class="signal-pill" style="border-color:#a0f0a0; color:#a0f0a0;">{t["total_signal"]}</span>' if t.get('total_signal') else '')
                                  + "</div></td>"
                                  f"<td><strong>{t['team']}</strong></td>"
                                  f"<td><span class='vs'>vs</span>{t['opp_pitcher']} ({abbrev_map.get(t['opponent'], 'TBD')})</td>"
                                  f"<td class='metric' style='font-weight:bold;'><span style=\"{ 'color:#00e676;' if t.get('implied_total', 0) >= 4.2 else '' }\">{t.get('implied_total', '-')}</span></td>"
                                  f"<td class='metric { 'move-up' if t['ml_move'] < 0 else ('move-down' if t['ml_move'] > 0 else 'move-even') }'>{ '+' if t['ml_move'] > 0 else '' }{ t['ml_move'] if t['ml_move'] != 0 else 'EVEN' }</td>"
                                  f"<td class='metric { 'move-up' if t['tt_move'] > 0 else ('move-down' if t['tt_move'] < 0 else 'move-even') }'>{ '+' if t['tt_move'] > 0 else '' }{ t['tt_move'] if t['tt_move'] != 0 else 'EVEN' }</td>"
                                  f"<td><div class='divergence-cell { 'move-up' if (t.get('divergence') or 0) > 0 else ('move-down' if (t.get('divergence') or 0) < 0 else 'move-even') }'>"
                                  f"<span>{ '+' if (t.get('divergence') or 0) > 0 else '' }{ t.get('divergence', 0) }%</span>"
                                  f"<span class='{ 'trend-surging' if t.get('trend') == 'SURGING' else ('trend-fading' if t.get('trend') == 'FADING' else '') }' style='font-size: 0.9rem;'>"
                                  f"{ '🔥' if t.get('trend') == 'SURGING' else ('❄️' if t.get('trend') == 'FADING' else '▫️') }</span>"
                                  f"</div></td>"
                                  f"</tr>" for t in t_reports[:20]])}
                    </tbody>
                </table>
            </div>
        </div>

    </div>

    <script>
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
