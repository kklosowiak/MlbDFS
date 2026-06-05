import os
import datetime
from config import config
from utils.team_signals import apply_team_blind_spot

class DashboardGenerator:
    def __init__(self):
        self.output_path = os.path.join(config.BASE_DIR, "reports", "dashboard.html")
        os.makedirs(os.path.dirname(self.output_path), exist_ok=True)

    def generate_report(self, p_reports, t_reports, h_reports, skipped_events=None, median_k=5.5, vegas_board=None):
        """Generates a premium 4-Tab dashboard including the Vegas Board."""
        if skipped_events is None: skipped_events = []
        emoji_key = {
            "elite": "🔥", "high": "⚡", "med": "📈", "low": "📉",
            "trap": "🚨", "shark": "🦈", "whale": "🐳", "steam": "💨",
        }
        
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
        t_reports = sorted(t_reports, key=lambda x: x.get('blended_rating', (x.get('stack_score', 0) + x.get('attack_conf', 50)) / 2), reverse=True)
        p_reports = sorted(p_reports, key=lambda x: x.get('alpha_score', 0), reverse=True)
        h_reports = sorted(h_reports, key=lambda x: x.get('player_score', 0), reverse=True)
        
        pitcher_rows = []
        for p in p_reports[:35]:
            p_conf = p.get('attack_conf')
            p_reasons = p.get('attack_reasons', [])
            p_reasons_li = "".join([f"<div style='background:rgba(255,255,255,0.02); border-left:3px solid var(--accent-blue); padding:10px 14px; border-radius:6px; margin-bottom:8px; font-size:0.92rem; color:rgba(255,255,255,0.85);'>• {r}</div>" for r in p_reasons])
            
            # Statcast features
            siera_val = p.get('siera', 4.10)
            csw_val = p.get('csw', 0.25)
            form_era = p.get('recent_era', '-')
            form_k9 = p.get('recent_k9', '-')
            
            statcast_grid = f"""
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; margin-bottom:20px;">
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:8px; border-radius:8px; text-align:center;">
                    <div style="font-size:0.68rem; color:var(--text-secondary); text-transform:uppercase; margin-bottom:4px; font-weight:700;">SIERA</div>
                    <div style="font-size:1.05rem; font-weight:700; color:#fff;">{f"{siera_val:.2f}" if isinstance(siera_val, float) else siera_val}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:8px; border-radius:8px; text-align:center;">
                    <div style="font-size:0.68rem; color:var(--text-secondary); text-transform:uppercase; margin-bottom:4px; font-weight:700;">CSW%</div>
                    <div style="font-size:1.05rem; font-weight:700; color:#fff;">{f"{(csw_val*100):.1f}%" if isinstance(csw_val, float) else csw_val}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:8px; border-radius:8px; text-align:center;">
                    <div style="font-size:0.68rem; color:var(--text-secondary); text-transform:uppercase; margin-bottom:4px; font-weight:700;">Form ERA</div>
                    <div style="font-size:1.05rem; font-weight:700; color:var(--accent-green);">{form_era}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:8px; border-radius:8px; text-align:center;">
                    <div style="font-size:0.68rem; color:var(--text-secondary); text-transform:uppercase; margin-bottom:4px; font-weight:700;">Form K/9</div>
                    <div style="font-size:1.05rem; font-weight:700; color:#fff;">{form_k9}</div>
                </div>
            </div>
            """

            # Player props grid
            props_list = []
            if p.get('k_line') is not None:
                props_list.append(("K Prop Limit", f"{p['k_line']} ({p.get('k_odds', 'EVEN')})"))
            if p.get('outs_line') is not None:
                props_list.append(("Outs Limit", f"{p['outs_line']} ({p.get('outs_odds', 'EVEN')})"))
            if p.get('walks_line') is not None:
                props_list.append(("Walks Limit", f"{p['walks_line']} ({p.get('walks_odds', 'EVEN')})"))
            if p.get('er_line') is not None:
                props_list.append(("ER Limit", f"{p['er_line']} ({p.get('er_odds', 'EVEN')})"))
            if p.get('hits_allowed_line') is not None:
                props_list.append(("Hits Allowed", f"{p['hits_allowed_line']} ({p.get('hits_allowed_odds', 'EVEN')})"))

            props_grid_html = ""
            if props_list:
                cards = []
                for i, (name, value) in enumerate(props_list):
                    is_last_odd = (i == len(props_list) - 1) and (len(props_list) % 2 != 0)
                    span_style = "grid-column: span 2;" if is_last_odd else ""
                    cards.append(f"""
                    <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.04); padding:10px 14px; border-radius:8px; display:flex; justify-content:space-between; align-items:center; {span_style}">
                        <span style="font-size:0.85rem; color:var(--text-secondary); font-weight:500;">{name}</span>
                        <span style="font-size:0.95rem; font-weight:700; color:#fff;">{value}</span>
                    </div>
                    """)
                props_grid_html = f"""
                <div style="margin-bottom:20px;">
                    <div style="font-size:0.8rem; font-weight:700; text-transform:uppercase; color:var(--accent-blue); letter-spacing:0.05em; margin-bottom:10px;">VEGAS PLAYER PROPS</div>
                    <div style="display:grid; grid-template-columns: repeat(2, 1fr); gap:10px;">
                        {"".join(cards)}
                    </div>
                </div>
                """

            # True Talent boundary warnings
            talent_warning_html = ""
            if p.get('true_talent_penalty'):
                talent_warning_html = """
                <div style="background:rgba(255,69,58,0.08); border:1px solid rgba(255,69,58,0.25); padding:12px 16px; border-radius:10px; margin-bottom:20px; display:flex; align-items:center; gap:12px;">
                    <span style="font-size:1.5rem;">🚨</span>
                    <div>
                        <div style="color:#fff; font-weight:700; font-size:0.9rem;">SABERMETRIC TRAP ARMS</div>
                        <div style="color:rgba(255,255,255,0.75); font-size:0.82rem; margin-top:2px;">Season K-BB% < 14% and HR/9 > 1.40. Poor control and high homer risk priced in.</div>
                    </div>
                </div>
                """
            
            p_reasons_html = f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:25px; background:rgba(255,255,255,0.02); padding:16px 20px; border-radius:12px; border:1px solid rgba(255,255,255,0.04);">
                <span style="font-size:1rem; color:var(--text-secondary); font-weight:600;">OMEGA Confidence Score</span>
                <span style="font-size:1.8rem; font-weight:800; color:var(--accent-blue); text-shadow:0 0 15px rgba(10,132,255,0.4);">{p_conf}%</span>
            </div>
            {talent_warning_html}
            {statcast_grid}
            {props_grid_html}
            <div style="margin-bottom:10px; font-size:0.8rem; font-weight:700; text-transform:uppercase; color:var(--accent-blue); letter-spacing:0.05em;">PITCHER ANALYTICS</div>
            <div style="display:flex; flex-direction:column; gap:2px; margin-bottom:10px;">{p_reasons_li}</div>
            """
            p_reasons_html = p_reasons_html.replace('"', '&quot;').replace('\n', ' ')

            row = f"""<tr class="{'god-tier' if p['alpha_score'] >= 85 else ''}" style="cursor:pointer;" onclick="showDetails('{p['pitcher']} ({abbrev_map.get(p['team'], p['team'])})', '{p_reasons_html}')">
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
            
            # Formulated platoon description (for popup details only)
            platoon_desc = ""
            if platoon_mult > 1.0:
                pct = round((platoon_mult - 1.0) * 100)
                platoon_desc = f"""
                <div style="background:rgba(50,215,75,0.08); border:1px solid rgba(50,215,75,0.25); padding:12px 16px; border-radius:10px; margin-bottom:20px; display:flex; align-items:center; gap:12px;">
                    <span style="font-size:1.5rem;">⚡</span>
                    <div>
                        <div style="color:var(--accent-green); font-weight:700; font-size:0.9rem;">PLATOON SPLITS EDGE (+{pct}%)</div>
                        <div style="color:rgba(255,255,255,0.75); font-size:0.82rem; margin-top:2px;">Excellent edge vs. opposing starter throwing with their hand ({p_hand}HP).</div>
                    </div>
                </div>
                """
            elif platoon_mult < 1.0:
                pct = round((1.0 - platoon_mult) * 100)
                platoon_desc = f"""
                <div style="background:rgba(255,69,58,0.08); border:1px solid rgba(255,69,58,0.25); padding:12px 16px; border-radius:10px; margin-bottom:20px; display:flex; align-items:center; gap:12px;">
                    <span style="font-size:1.5rem;">📉</span>
                    <div>
                        <div style="color:var(--accent-red); font-weight:700; font-size:0.9rem;">PLATOON DISADVANTAGE (-{pct}%)</div>
                        <div style="color:rgba(255,255,255,0.75); font-size:0.82rem; margin-top:2px;">Disadvantageous splits vs. opposing starter's hand ({p_hand}HP).</div>
                    </div>
                </div>
                """

            h_conf = h.get('attack_conf')
            h_reasons = h.get('attack_reasons', [])
            h_reasons_li = "".join([f"<div style='background:rgba(255,255,255,0.02); border-left:3px solid var(--accent-blue); padding:10px 14px; border-radius:6px; margin-bottom:8px; font-size:0.92rem; color:rgba(255,255,255,0.85);'>• {r}</div>" for r in h_reasons])
            
            # Hitter player props (for popup details)
            hitter_props = []
            if h.get('hits_line') and h.get('hits_line') != '-':
                hitter_props.append(("Hits Prop", f"{h['hits_line']} ({h.get('hits_price', 'EVEN')})"))
            if h.get('tb_line') and h.get('tb_line') != '-':
                hitter_props.append(("Total Bases", f"{h['tb_line']} ({h.get('tb_price', 'EVEN')})"))
            if h.get('walks_line') and h.get('walks_line') != '-':
                hitter_props.append(("Walks Prop", f"{h['walks_line']} ({h.get('walks_price', 'EVEN')})"))
            if h.get('strikeouts_line') and h.get('strikeouts_line') != '-':
                hitter_props.append(("Strikeouts", f"{h['strikeouts_line']} ({h.get('strikeouts_price', 'EVEN')})"))
            if h.get('runs_g_rbi_line') and h.get('runs_g_rbi_line') != '-':
                hitter_props.append(("Runs+RBI", f"{h['runs_g_rbi_line']} ({h.get('runs_g_rbi_price', 'EVEN')})"))
                
            h_props_html = ""
            if hitter_props:
                cards = []
                for name, value in hitter_props:
                    cards.append(f"""
                    <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.04); padding:10px 14px; border-radius:8px; display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-size:0.85rem; color:var(--text-secondary); font-weight:500;">{name}</span>
                        <span style="font-size:0.95rem; font-weight:700; color:#fff;">{value}</span>
                    </div>
                    """)
                h_props_html = f"""
                <div style="margin-bottom:20px; display:flex; flex-direction:column; gap:8px;">
                    <div style="font-size:0.8rem; font-weight:700; text-transform:uppercase; color:var(--accent-blue); letter-spacing:0.05em; margin-bottom:4px;">VEGAS PLAYER PROPS</div>
                    {"".join(cards)}
                </div>
                """
            
            h_reasons_html = f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:25px; background:rgba(255,255,255,0.02); padding:16px 20px; border-radius:12px; border:1px solid rgba(255,255,255,0.04);">
                <span style="font-size:1rem; color:var(--text-secondary); font-weight:600;">Hitter Confidence Score</span>
                <span style="font-size:1.8rem; font-weight:800; color:var(--accent-blue); text-shadow:0 0 15px rgba(10,132,255,0.4);">{h_conf}%</span>
            </div>
            {platoon_desc}
            {h_props_html}
            <div style="margin-bottom:10px; font-size:0.8rem; font-weight:700; text-transform:uppercase; color:var(--accent-blue); letter-spacing:0.05em;">HITTER ANALYTICS</div>
            <div style="display:flex; flex-direction:column; gap:2px; margin-bottom:10px;">{h_reasons_li}</div>
            """
            h_reasons_html = h_reasons_html.replace('"', '&quot;').replace('\n', ' ')

            row = f"""<tr class="{'god-tier' if h['player_score'] >= 85 else ''}" style="cursor:pointer;" onclick="showDetails('{h['name']} ({abbrev_map.get(h['team'], h['team'])})', '{h_reasons_html}')">
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
</div></td>
<td><strong>{h['name']}</strong> <span class="team-label" style="font-weight: 800; color: #ff9f0a;">({h.get('bat_side', 'R')}B)</span> <span class="team-label">({abbrev_map.get(h['team'], h['team'])})</span></td>
<td><span class="vs">vs</span>{h.get('opp_pitcher', 'TBD')} <span class="team-label" style="font-weight: 800; color: #0a84ff;">({h.get('pitch_hand', 'R')}HP)</span> <span class="team-label">({abbrev_map.get(h.get('opponent', 'TBD'), 'TBD')})</span></td>
<td class="metric">{'+' if isinstance(h.get('ahr_price'), (int, float)) and h['ahr_price'] > 0 else ''}{h.get('ahr_price', '-')}</td>
<td class="metric"><b>{h.get('hits_line', '-')}</b><br><span style="font-size:0.8em; color: var(--text-secondary);">({'+' if isinstance(h.get('hits_price'), (int, float)) and h['hits_price'] > 0 else ''}{h.get('hits_price') or '-'})</span></td>
<td class="metric"><b>{h.get('tb_line', '-')}</b><br><span style="font-size:0.8em; color: var(--text-secondary);">({'+' if isinstance(h.get('tb_price'), (int, float)) and h['tb_price'] > 0 else ''}{h.get('tb_price') or '-'})</span></td>
</tr>"""
            hitter_rows.append(row)

        team_rows = []
        for t in t_reports[:20]:
            apply_team_blind_spot(t)
            div = t.get('divergence', 0)
            if div >= 15:
                div_pill = f'<span class="signal-pill" style="background:linear-gradient(135deg, rgba(50, 215, 75, 0.15) 0%, rgba(50, 215, 75, 0.3) 100%); border-color:#32d74b; color:#32d74b; font-weight:800; box-shadow:0 0 10px rgba(50, 215, 75, 0.35);">🟢 ML-DIV (+{div}%)</span>'
            elif div <= -15:
                div_pill = f'<span class="signal-pill" style="background:linear-gradient(135deg, rgba(255, 69, 58, 0.15) 0%, rgba(255, 69, 58, 0.3) 100%); border-color:#ff453a; color:#ff453a; font-weight:800; box-shadow:0 0 10px rgba(255, 69, 58, 0.35);">🔴 ML-FADE ({div}%)</span>'
            else:
                div_pill = ''

            trend = t.get('trend', 'STABLE')
            if trend == 'SURGING':
                trend_pill = '<span class="signal-pill" style="background: linear-gradient(135deg, rgba(255, 159, 10, 0.15) 0%, rgba(255, 69, 58, 0.25) 100%); border: 1px solid #ff9f0a; color: #ff9f0a; font-weight:800; box-shadow: 0 0 10px rgba(255, 159, 10, 0.4);">🔥 SURGING</span>'
            elif trend == 'FADING':
                trend_pill = '<span class="signal-pill" style="background: linear-gradient(135deg, rgba(0, 180, 216, 0.15) 0%, rgba(144, 224, 239, 0.2) 100%); border: 1px solid #00b4d8; color: #00b4d8; font-weight:800; box-shadow: 0 0 8px rgba(0, 180, 216, 0.35);">❄️ FADING</span>'
            else:
                trend_pill = ''

            t_conf = t.get('attack_conf')
            t_reasons = t.get('attack_reasons', [])
            t_reasons_li = "".join([f"<div style='background:rgba(255,255,255,0.02); border-left:3px solid var(--accent-blue); padding:10px 14px; border-radius:6px; margin-bottom:8px; font-size:0.92rem; color:rgba(255,255,255,0.85);'>• {r}</div>" for r in t_reasons])
            
            # Vegas grid
            implied_val = t.get('implied_total', '-')
            ml_val = t.get('ml_move', 0.0)
            tt_val = t.get('tt_move', 0.0)
            div_val = t.get('divergence', 0)
            
            vegas_grid = f"""
            <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap:10px; margin-bottom:20px;">
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:8px; border-radius:8px; text-align:center;">
                    <div style="font-size:0.68rem; color:var(--text-secondary); text-transform:uppercase; margin-bottom:4px; font-weight:700;">Implied Runs</div>
                    <div style="font-size:1.05rem; font-weight:700; color:#fff;">{implied_val}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:8px; border-radius:8px; text-align:center;">
                    <div style="font-size:0.68rem; color:var(--text-secondary); text-transform:uppercase; margin-bottom:4px; font-weight:700;">ML Move</div>
                    <div style="font-size:1.05rem; font-weight:700; color:{'var(--accent-green)' if ml_val < 0 else ('var(--accent-red)' if ml_val > 0 else '#fff')};">{'+' if ml_val > 0 else ''}{ml_val if ml_val != 0 else 'EVEN'}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:8px; border-radius:8px; text-align:center;">
                    <div style="font-size:0.68rem; color:var(--text-secondary); text-transform:uppercase; margin-bottom:4px; font-weight:700;">Total Move</div>
                    <div style="font-size:1.05rem; font-weight:700; color:{'var(--accent-green)' if tt_val > 0 else ('var(--accent-red)' if tt_val < 0 else '#fff')};">{'+' if tt_val > 0 else ''}{tt_val if tt_val != 0 else 'EVEN'}</div>
                </div>
                <div style="background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.05); padding:8px; border-radius:8px; text-align:center;">
                    <div style="font-size:0.68rem; color:var(--text-secondary); text-transform:uppercase; margin-bottom:4px; font-weight:700;">Divergence</div>
                    <div style="font-size:1.05rem; font-weight:700; color:{'var(--accent-green)' if div_val > 0 else ('var(--accent-red)' if div_val < 0 else '#fff')};">{'+' if div_val > 0 else ''}{div_val}%</div>
                </div>
            </div>
            """
            
            blended = t.get('blended_rating', round((t.get('stack_score', 0) + t.get('attack_conf', 50)) / 2, 1))

            # Dynamic bullpen details
            opp = t.get('opponent', '')
            bullpen_info = ""
            if opp:
                try:
                    from data.bullpen_analyzer import BullpenAnalyzer
                    grade, mult, fatigue, era, whip, k_bb = BullpenAnalyzer().get_dynamic_bullpen_grade(opp)
                    bullpen_info = f"""
                    <div style="background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.04); padding:14px; border-radius:10px; margin-bottom:20px;">
                        <div style="font-size:0.8rem; font-weight:700; text-transform:uppercase; color:var(--accent-blue); letter-spacing:0.05em; margin-bottom:8px;">OPPOSING RELIEF PITCHING</div>
                        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
                            <span style="font-size:0.9rem; color:#fff; font-weight:600;">{opp} Bullpen Quality</span>
                            <span style="font-size:0.95rem; font-weight:700; color:{'var(--accent-green)' if grade in ('Elite', 'Strong') else ('var(--accent-red)' if grade in ('Weak', 'Below Average') else '#fff')};">{grade}</span>
                        </div>
                        <div style="font-size:0.85rem; color:var(--text-secondary); line-height:1.5;">
                            ERA: <b>{era:.2f}</b> | WHIP: <b>{whip:.2f}</b> | K-BB%: <b>{k_bb*100:.1f}%</b><br>
                            Recent Usage Fatigue: <b>{t.get('bullpen_fatigue', 0)}%</b>
                        </div>
                    </div>
                    """
                except:
                    pass
                
            t_reasons_html = f"""
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:25px; background:rgba(255,255,255,0.02); padding:16px 20px; border-radius:12px; border:1px solid rgba(255,255,255,0.04);">
                <span style="font-size:1rem; color:var(--text-secondary); font-weight:600;">Stack Blended Score</span>
                <span style="font-size:1.8rem; font-weight:800; color:var(--accent-blue); text-shadow:0 0 15px rgba(10,132,255,0.4);">{blended}</span>
            </div>
            {vegas_grid}
            {bullpen_info}
            <div style="margin-bottom:10px; font-size:0.8rem; font-weight:700; text-transform:uppercase; color:var(--accent-blue); letter-spacing:0.05em;">STACK ANALYTICS</div>
            <div style="display:flex; flex-direction:column; gap:2px; margin-bottom:10px;">{t_reasons_li}</div>
            """
            t_reasons_html = t_reasons_html.replace('"', '&quot;').replace('\n', ' ')


            row = f"""<tr class="{'god-tier' if blended >= 80 else ''}" style="cursor:pointer;" onclick="showDetails('{t['team']} vs {t['opponent']}', '{t_reasons_html}')">
<td class="score {'score-elite' if blended >= 85 else ('score-high' if blended >= 75 else '')}">{blended}</td>
<td class="metric-sub" style="font-weight:700; color:#fff;">{t['stack_score']}</td>
<td class="metric-sub" style="font-weight:700; color:#0a84ff;">{t.get('attack_conf', 0)}%</td>
<td class="score-physics">{t.get('physics_score', 0)}</td>
<td class="score-market">{t.get('market_score', 0)}</td>
<td><div class="signals-container">
{ '<span class="signal-pill pill-shark">🦈 SHARK</span>' if t.get('is_shark') else '' }
{ '<span class="signal-pill pill-storm">🌪️ STORM</span>' if t.get('is_storm') else '' }
{ '<span class="signal-pill pill-whale">🐋 WHALE</span>' if t.get('is_whale') else '' }
{ '<span class="signal-pill pill-sharp">🎰 HEAVY $</span>' if t.get('is_sharp') and not t.get('is_shark') else '' }
{ '<span class="signal-pill pill-steam">💨 STEAM</span>' if t.get('is_steam') else '' }
{ '<span class="signal-pill pill-burst">⚡ BURST</span>' if t.get('is_burst') else '' }
{ '<span class="signal-pill pill-neutral" style="background: linear-gradient(135deg, rgba(0, 242, 254, 0.12) 0%, rgba(79, 172, 254, 0.12) 100%); border-color: #00f2fe; color: #00f2fe; text-shadow: 0 0 8px rgba(0, 242, 254, 0.4);">👁️ BLIND SPOT</span>' if t.get('is_blind_spot') else '' }
{ '<span class="signal-pill pill-storm">✨ DEBUT TARGET</span>' if t.get('is_opp_debut') else '' }
</div></td>
<td><div class="signals-container">
{ '<span class="signal-pill pill-trap">⚠️ TRAP</span>' if t.get('is_trap') else '' }
{ '<span class="signal-pill pill-paradox">⚠️ PARADOX</span>' if t.get('is_paradox') else '' }
{ '<span class="signal-pill pill-exhausted">🔥 EXHAUSTED</span>' if t.get('bullpen_fatigue',0) >= 90 else ('<span class="signal-pill pill-gassed">♨️ GASSED</span>' if t.get('bullpen_fatigue',0) >= 80 else ('<span class="signal-pill pill-weary">♨️ WEARY</span>' if t.get('bullpen_fatigue',0) >= 70 else '')) }
{ (f'<span class="signal-pill pill-neutral">{t["total_signal"]}</span>' if t.get('total_signal') else '') }
{ div_pill }
{ trend_pill }
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

        # OMEGA Vegas Board Row Building for Static Standalone HTML
        vegas_rows = []
        team_id_map = {
            'LAA': 108, 'ARI': 109, 'BAL': 110, 'BOS': 111, 'CHC': 112, 'CIN': 113, 'CLE': 114,
            'COL': 115, 'DET': 116, 'HOU': 117, 'KC': 118, 'LAD': 119, 'WSH': 120, 'NYM': 121,
            'OAK': 133, 'PIT': 134, 'SD': 135, 'SEA': 136, 'SF': 137, 'STL': 138, 'TB': 139,
            'TEX': 140, 'TOR': 141, 'MIN': 142, 'PHI': 143, 'ATL': 144, 'CWS': 145, 'MIA': 146,
            'NYY': 147, 'MIL': 158
        }

        def get_implied_runs_class(val):
            if val is None or val == '' or val == '—': return 'cell-empty'
            try:
                v = float(val)
                if v >= 5.5: return 'cell-implied-elite'
                if v >= 5.0: return 'cell-implied-high'
                if v >= 4.5: return 'cell-implied-neutral'
                if v >= 4.0: return 'cell-implied-low-mid'
                if v >= 3.5: return 'cell-implied-low'
                return 'cell-implied-verylow'
            except ValueError:
                return 'cell-empty'

        def get_over_under_class(val):
            if val is None or val == '' or val == '—': return 'cell-empty'
            try:
                v = float(val)
                if v >= 10.5: return 'cell-ou-elite'
                if v >= 9.5: return 'cell-ou-high'
                if v >= 8.5: return 'cell-ou-neutral'
                if v >= 7.5: return 'cell-ou-low'
                return 'cell-ou-verylow'
            except ValueError:
                return 'cell-empty'

        def get_moneyline_class(val):
            if val is None or val == '' or val == '—': return 'cell-empty'
            try:
                v = float(val)
                if v < 0:
                    if v <= -180: return 'cell-ml-fav-heavy'
                    if v <= -130: return 'cell-ml-fav-medium'
                    return 'cell-ml-fav-light'
                else:
                    if v >= 180: return 'cell-ml-dog-heavy'
                    if v >= 130: return 'cell-ml-dog-medium'
                    return 'cell-ml-dog-light'
            except ValueError:
                return 'cell-empty'

        def get_pct_class(val):
            if val is None or val == '' or val == '—' or val == '-': return 'cell-empty'
            try:
                v = float(str(val).replace('%', ''))
                if v >= 65: return 'cell-pct-elite'
                if v >= 55: return 'cell-pct-high'
                if v >= 45: return 'cell-pct-neutral'
                if v >= 35: return 'cell-pct-low'
                return 'cell-pct-verylow'
            except ValueError:
                return 'cell-empty'

        def get_diff_class(val, is_moneyline=False):
            if val is None or val == '' or val == '—': return 'cell-empty'
            try:
                v = float(val)
                if v == 0: return 'cell-diff-neutral'
                is_positive = v > 0
                if is_moneyline:
                    is_positive = v < 0
                return 'cell-diff-pos' if is_positive else 'cell-diff-neg'
            except ValueError:
                return 'cell-empty'

        def py_format_numeric_odds(val):
            if val is None or val == '':
                return '—'
            try:
                n = float(val)
                return f"+{int(n)}" if n > 0 else f"{int(n)}"
            except ValueError:
                return str(val)

        if not vegas_board:
            vegas_rows.append('<tr><td colspan="13" style="text-align:center; padding:45px 30px; color:var(--text-secondary); font-size:0.85rem;">No Vegas Board slate data available for this run.</td></tr>')
        else:
            for idx, g in enumerate(vegas_board):
                implied_away_diff = None
                if g.get('away_tt_live') is not None and g.get('away_tt_open') is not None:
                    implied_away_diff = g['away_tt_live'] - g['away_tt_open']

                implied_home_diff = None
                if g.get('home_tt_live') is not None and g.get('home_tt_open') is not None:
                    implied_home_diff = g['home_tt_live'] - g['home_tt_open']

                total_diff = None
                if g.get('current_total') is not None and g.get('opening_total') is not None:
                    total_diff = g['current_total'] - g['opening_total']

                ml_away_diff = None
                if g.get('away_current_ml') is not None and g.get('away_opening_ml') is not None:
                    from utils.market_utils import calculate_ml_move
                    ml_away_diff = calculate_ml_move(g['away_opening_ml'], g['away_current_ml'])

                ml_home_diff = None
                if g.get('home_current_ml') is not None and g.get('home_opening_ml') is not None:
                    from utils.market_utils import calculate_ml_move
                    ml_home_diff = calculate_ml_move(g['home_opening_ml'], g['home_current_ml'])

                t_str = g.get('time_str', 'TBD')
                t_str = t_str.replace('am', 'AM').replace('pm', 'PM')
                if len(t_str) > 3:
                    t_str = t_str[0].upper() + t_str[1:]

                away_logo_id = team_id_map.get(g['away_ab'].upper())
                home_logo_id = team_id_map.get(g['home_ab'].upper())

                away_logo_html = f'<img src="https://www.mlbstatic.com/team-logos/{away_logo_id}.svg" style="width:24px; height:24px; border-radius:4px; vertical-align:middle; background:rgba(255,255,255,0.03); padding:2px;" alt="{g["away_ab"]}">' if away_logo_id else f'<div style="width:24px; height:24px; border-radius:12px; background:rgba(255,255,255,0.08); color:rgba(255,255,255,0.8); font-size:0.65rem; font-weight:700; display:inline-flex; align-items:center; justify-content:center;">{g["away_ab"]}</div>'
                home_logo_html = f'<img src="https://www.mlbstatic.com/team-logos/{home_logo_id}.svg" style="width:24px; height:24px; border-radius:4px; vertical-align:middle; background:rgba(255,255,255,0.03); padding:2px;" alt="{g["home_ab"]}">' if home_logo_id else f'<div style="width:24px; height:24px; border-radius:12px; background:rgba(255,255,255,0.08); color:rgba(255,255,255,0.8); font-size:0.65rem; font-weight:700; display:inline-flex; align-items:center; justify-content:center;">{g["home_ab"]}</div>'

                ou_open = f"{g['opening_total']:.1f}" if g.get('opening_total') else '—'
                ou_live = f"{g['current_total']:.1f}" if g.get('current_total') else '—'

                over_t = f"{g['over_ticket']}%" if g.get('over_ticket') is not None else '—'
                over_m = f"{g['over_money']}%" if g.get('over_money') is not None else '—'
                under_t = f"{g['under_ticket']}%" if g.get('under_ticket') is not None else '—'
                under_m = f"{g['under_money']}%" if g.get('under_money') is not None else '—'

                total_splits_html = f"""
                    <div style="font-size:0.68rem; color:var(--text-secondary); background:rgba(255,255,255,0.02); padding:4px 6px; border-radius:4px; border:1px solid rgba(255,255,255,0.04); margin-top:6px; display:inline-block; text-align:left; font-variant-numeric:tabular-nums; line-height:1.2;" title="Consensus Splits: percentage of total ticket bets placed vs. percentage of total dollars (Money) handle on the Over/Under">
                        <span style="color:var(--accent-green); font-weight:700; font-size:0.65rem;">▲ O:</span> {over_t} Bets / {over_m} Money<br>
                        <span style="color:var(--accent-red); font-weight:700; font-size:0.65rem;">▼ U:</span> {under_t} Bets / {under_m} Money
                    </div>
                """

                away_t = f"{g['away_ml_ticket']}%" if g.get('away_ml_ticket') is not None else '—'
                away_m = f"{g['away_ml_money']}%" if g.get('away_ml_money') is not None else '—'
                home_t = f"{g['home_ml_ticket']}%" if g.get('home_ml_ticket') is not None else '—'
                home_m = f"{g['home_ml_money']}%" if g.get('home_ml_money') is not None else '—'

                away_tt_open_val = f"{g['away_tt_open']:.2f}" if g.get('away_tt_open') is not None else '—'
                away_tt_live_val = f"{g['away_tt_live']:.2f}" if g.get('away_tt_live') is not None else '—'
                home_tt_open_val = f"{g['home_tt_open']:.2f}" if g.get('home_tt_open') is not None else '—'
                home_tt_live_val = f"{g['home_tt_live']:.2f}" if g.get('home_tt_live') is not None else '—'

                away_diff_txt = f"{'+' if implied_away_diff > 0 else ''}{implied_away_diff:.2f}" if implied_away_diff is not None else '—'
                home_diff_txt = f"{'+' if implied_home_diff > 0 else ''}{implied_home_diff:.2f}" if implied_home_diff is not None else '—'
                total_diff_txt = f"{'+' if total_diff > 0 else ''}{total_diff:.1f}" if total_diff is not None else '—'
                ml_away_diff_txt = f"{'+' if ml_away_diff > 0 else ''}{ml_away_diff}" if ml_away_diff is not None else '—'
                ml_home_diff_txt = f"{'+' if ml_home_diff > 0 else ''}{ml_home_diff}" if ml_home_diff is not None else '—'

                row_away = f"""
                <tr>
                    <td rowspan="2" class="time-cell" style="font-size:0.75rem; color:rgba(255,255,255,0.85); font-weight:700; padding:12px 8px; vertical-align:middle; line-height:1.3; font-variant-numeric: tabular-nums;">
                        {t_str}
                    </td>
                    <td class="team-cell" style="padding:12px 8px; vertical-align:middle; min-width: 140px;">
                        <div style="display:flex; align-items:center; gap:10px;">
                            {away_logo_html}
                            <div>
                                <div style="font-weight:700; color:#fff; font-size:0.85rem; display:flex; align-items:center; gap:4px;">
                                    <span>{g['away_ab']}</span>
                                    <span style="font-size:0.68rem; color:var(--text-secondary); background:rgba(255,255,255,0.05); padding:1px 4px; border-radius:3px; font-weight:500;">AWAY</span>
                                </div>
                                <div style="font-size:0.7rem; color:var(--text-secondary); max-width:130px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">{g['away_team']}</div>
                            </div>
                        </div>
                    </td>
                    
                    <td class="{get_implied_runs_class(g.get('away_tt_open'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.85rem;">{away_tt_open_val}</td>
                    <td class="{get_implied_runs_class(g.get('away_tt_live'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.88rem; font-weight:700;">{away_tt_live_val}</td>
                    <td class="{get_diff_class(implied_away_diff)}" style="text-align:center; padding:12px 8px;">{away_diff_txt}</td>
                    
                    <td rowspan="2" class="{get_over_under_class(g.get('opening_total'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.85rem; vertical-align:middle;">
                        {ou_open}
                    </td>
                    <td rowspan="2" class="{get_over_under_class(g.get('current_total'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.88rem; font-weight:800; vertical-align:middle;">
                        {ou_live}
                    </td>
                    <td rowspan="2" class="{get_diff_class(total_diff)}" style="text-align:center; padding:12px 8px; vertical-align:middle;">
                        <span style="font-weight:700;">{total_diff_txt}</span>
                        <br>
                        {total_splits_html}
                    </td>
                    
                    <td class="{get_pct_class(away_t)}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.82rem; font-weight:700;">{away_t}</td>
                    <td class="{get_moneyline_class(g.get('away_opening_ml'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.82rem;">{py_format_numeric_odds(g['away_opening_ml'])}</td>
                    <td class="{get_moneyline_class(g.get('away_current_ml'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.85rem; font-weight:700;">{py_format_numeric_odds(g['away_current_ml'])}</td>
                    <td class="{get_diff_class(ml_away_diff, True)}" style="text-align:center; padding:12px 8px;">{ml_away_diff_txt}</td>
                    <td class="{get_pct_class(away_m)}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.82rem; font-weight:700;">{away_m}</td>
                </tr>
                """

                row_home = f"""
                <tr>
                    <td class="team-cell" style="padding:12px 8px; vertical-align:middle; min-width: 140px;">
                        <div style="display:flex; align-items:center; gap:10px;">
                            {home_logo_html}
                            <div>
                                <div style="font-weight:700; color:#fff; font-size:0.85rem; display:flex; align-items:center; gap:4px;">
                                    <span>{g['home_ab']}</span>
                                    <span style="font-size:0.68rem; color:var(--text-secondary); background:rgba(255,255,255,0.05); padding:1px 4px; border-radius:3px; font-weight:500;">HOME</span>
                                </div>
                                <div style="font-size:0.7rem; color:var(--text-secondary); max-width:130px; text-overflow:ellipsis; overflow:hidden; white-space:nowrap;">{g['home_team']}</div>
                            </div>
                        </div>
                    </td>
                    <td class="{get_implied_runs_class(g.get('home_tt_open'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.85rem;">{home_tt_open_val}</td>
                    <td class="{get_implied_runs_class(g.get('home_tt_live'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.88rem; font-weight:700;">{home_tt_live_val}</td>
                    <td class="{get_diff_class(implied_home_diff)}" style="text-align:center; padding:12px 8px;">{home_diff_txt}</td>
                    
                    <td class="{get_pct_class(home_t)}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.82rem; font-weight:700;">{home_t}</td>
                    <td class="{get_moneyline_class(g.get('home_opening_ml'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.82rem;">{py_format_numeric_odds(g['home_opening_ml'])}</td>
                    <td class="{get_moneyline_class(g.get('home_current_ml'))}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.85rem; font-weight:700;">{py_format_numeric_odds(g['home_current_ml'])}</td>
                    <td class="{get_diff_class(ml_home_diff, True)}" style="text-align:center; padding:12px 8px;">{ml_home_diff_txt}</td>
                    <td class="{get_pct_class(home_m)}" style="text-align:center; font-variant-numeric: tabular-nums; padding:12px 8px; font-size:0.82rem; font-weight:700;">{home_m}</td>
                </tr>
                """

                vegas_rows.append(row_away)
                vegas_rows.append(row_home)

                # Add physical gap spacer row between matches (but not after the last game)
                if idx < len(vegas_board) - 1:
                    tr_spacer = '<tr class="vegas-spacer-row"><td colspan="13"></td></tr>'
                    vegas_rows.append(tr_spacer)

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MLB Ωmega Engine</title>
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
        
        /* ── PREMIUM VEGAS BOARD REDESIGN STYLES ── */
        #vegas-board-table {{
            border-collapse: collapse !important;
            width: 100%;
        }}
        #vegas-board-table th {{
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            padding: 12px 8px;
            vertical-align: middle;
        }}
        #vegas-board-table td {{
            border: 1px solid rgba(255, 255, 255, 0.08) !important;
            padding: 10px 8px;
            vertical-align: middle;
        }}
        #vegas-board-table tr.vegas-spacer-row td {{
            border: none !important;
            background: transparent !important;
            padding: 0 !important;
            height: 12px !important;
        }}
        
        body.light-theme #vegas-board-table th,
        body.light-theme #vegas-board-table td {{
            border: 1px solid rgba(15, 23, 42, 0.15) !important;
        }}
        body.light-theme #vegas-board-table tr.vegas-spacer-row td {{
            border: none !important;
            background: transparent !important;
        }}

        /* Vegas Board Cell Color Coding Tints */
        #vegas-board-table td.cell-implied-elite {{ background: rgba(50, 215, 75, 0.22) !important; color: #fff !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-implied-high {{ background: rgba(50, 215, 75, 0.12) !important; color: rgba(255,255,255,0.95) !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-implied-neutral {{ background: rgba(255, 255, 255, 0.02) !important; color: rgba(255,255,255,0.85) !important; }}
        #vegas-board-table td.cell-implied-low-mid {{ background: rgba(255, 69, 58, 0.05) !important; color: rgba(255,255,255,0.8) !important; }}
        #vegas-board-table td.cell-implied-low {{ background: rgba(255, 69, 58, 0.15) !important; color: #fff !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-implied-verylow {{ background: rgba(255, 69, 58, 0.25) !important; color: #fff !important; font-weight: 700 !important; }}

        #vegas-board-table td.cell-ou-elite {{ background: rgba(50, 215, 75, 0.22) !important; color: #fff !important; font-weight: 800 !important; }}
        #vegas-board-table td.cell-ou-high {{ background: rgba(50, 215, 75, 0.12) !important; color: rgba(255,255,255,0.95) !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-ou-neutral {{ background: rgba(255, 255, 255, 0.02) !important; color: rgba(255,255,255,0.85) !important; }}
        #vegas-board-table td.cell-ou-low {{ background: rgba(255, 69, 58, 0.15) !important; color: #fff !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-ou-verylow {{ background: rgba(255, 69, 58, 0.25) !important; color: #fff !important; font-weight: 700 !important; }}

        #vegas-board-table td.cell-ml-fav-heavy {{ background: rgba(50, 215, 75, 0.22) !important; color: #fff !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-ml-fav-medium {{ background: rgba(50, 215, 75, 0.12) !important; color: rgba(255,255,255,0.95) !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-ml-fav-light {{ background: rgba(50, 215, 75, 0.06) !important; color: rgba(255,255,255,0.85) !important; }}
        #vegas-board-table td.cell-ml-dog-light {{ background: rgba(255, 69, 58, 0.06) !important; color: rgba(255,255,255,0.85) !important; }}
        #vegas-board-table td.cell-ml-dog-medium {{ background: rgba(255, 69, 58, 0.12) !important; color: rgba(255,255,255,0.95) !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-ml-dog-heavy {{ background: rgba(255, 69, 58, 0.22) !important; color: #fff !important; font-weight: 700 !important; }}

        #vegas-board-table td.cell-pct-elite {{ background: rgba(50, 215, 75, 0.22) !important; color: #fff !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-pct-high {{ background: rgba(50, 215, 75, 0.12) !important; color: rgba(255,255,255,0.95) !important; }}
        #vegas-board-table td.cell-pct-neutral {{ background: rgba(255, 255, 255, 0.02) !important; color: rgba(255,255,255,0.85) !important; }}
        #vegas-board-table td.cell-pct-low {{ background: rgba(255, 69, 58, 0.12) !important; color: rgba(255,255,255,0.95) !important; }}
        #vegas-board-table td.cell-pct-verylow {{ background: rgba(255, 69, 58, 0.22) !important; color: #fff !important; font-weight: 700 !important; }}

        #vegas-board-table td.cell-diff-pos {{ background: rgba(50, 215, 75, 0.15) !important; color: var(--accent-green) !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-diff-neg {{ background: rgba(255, 69, 58, 0.15) !important; color: var(--accent-red) !important; font-weight: 700 !important; }}
        #vegas-board-table td.cell-diff-neutral {{ background: rgba(255, 255, 255, 0.02) !important; color: var(--text-secondary) !important; }}

        #vegas-board-table td.cell-empty {{ background: rgba(255, 255, 255, 0.01) !important; color: var(--text-secondary) !important; }}

        /* Light Theme Overrides */
        body.light-theme #vegas-board-table td.cell-implied-elite {{ background: rgba(22, 163, 74, 0.22) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-implied-high {{ background: rgba(22, 163, 74, 0.12) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-implied-neutral {{ background: rgba(0, 0, 0, 0.01) !important; color: var(--text-primary) !important; }}
        body.light-theme #vegas-board-table td.cell-implied-low-mid {{ background: rgba(220, 38, 38, 0.05) !important; color: #991b1b !important; }}
        body.light-theme #vegas-board-table td.cell-implied-low {{ background: rgba(220, 38, 38, 0.12) !important; color: #991b1b !important; }}
        body.light-theme #vegas-board-table td.cell-implied-verylow {{ background: rgba(220, 38, 38, 0.22) !important; color: #991b1b !important; }}

        body.light-theme #vegas-board-table td.cell-ou-elite {{ background: rgba(22, 163, 74, 0.22) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-ou-high {{ background: rgba(22, 163, 74, 0.12) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-ou-neutral {{ background: rgba(0, 0, 0, 0.01) !important; color: var(--text-primary) !important; }}
        body.light-theme #vegas-board-table td.cell-ou-low {{ background: rgba(220, 38, 38, 0.12) !important; color: #991b1b !important; }}
        body.light-theme #vegas-board-table td.cell-ou-verylow {{ background: rgba(220, 38, 38, 0.22) !important; color: #991b1b !important; }}

        body.light-theme #vegas-board-table td.cell-ml-fav-heavy {{ background: rgba(22, 163, 74, 0.22) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-ml-fav-medium {{ background: rgba(22, 163, 74, 0.12) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-ml-fav-light {{ background: rgba(22, 163, 74, 0.06) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-ml-dog-light {{ background: rgba(220, 38, 38, 0.06) !important; color: #991b1b !important; }}
        body.light-theme #vegas-board-table td.cell-ml-dog-medium {{ background: rgba(220, 38, 38, 0.12) !important; color: #991b1b !important; }}
        body.light-theme #vegas-board-table td.cell-ml-dog-heavy {{ background: rgba(220, 38, 38, 0.22) !important; color: #991b1b !important; }}

        body.light-theme #vegas-board-table td.cell-pct-elite {{ background: rgba(22, 163, 74, 0.22) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-pct-high {{ background: rgba(22, 163, 74, 0.12) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-pct-neutral {{ background: rgba(0, 0, 0, 0.01) !important; color: var(--text-primary) !important; }}
        body.light-theme #vegas-board-table td.cell-pct-low {{ background: rgba(220, 38, 38, 0.12) !important; color: #991b1b !important; }}
        body.light-theme #vegas-board-table td.cell-pct-verylow {{ background: rgba(220, 38, 38, 0.22) !important; color: #991b1b !important; }}

        body.light-theme #vegas-board-table td.cell-diff-pos {{ background: rgba(22, 163, 74, 0.15) !important; color: #166534 !important; }}
        body.light-theme #vegas-board-table td.cell-diff-neg {{ background: rgba(220, 38, 38, 0.15) !important; color: #991b1b !important; }}
        body.light-theme #vegas-board-table td.cell-diff-neutral {{ background: rgba(0, 0, 0, 0.01) !important; color: var(--text-secondary) !important; }}

        body.light-theme #vegas-board-table td.cell-empty {{ background: rgba(0, 0, 0, 0.02) !important; color: var(--text-secondary) !important; }}

        @media (max-width: 768px) {{
            body {{
                padding: 10px 5px;
            }}
            .container {{
                max-width: 100%;
            }}
            .header {{
                flex-direction: column;
                align-items: flex-start;
                gap: 15px;
                margin-bottom: 20px;
            }}
            .header h1 {{
                font-size: 2rem;
            }}
            .header-meta {{
                text-align: left;
            }}
            .card {{
                padding: 15px 10px;
                border-radius: var(--radius-md);
                overflow-x: auto;
                -webkit-overflow-scrolling: touch;
            }}
            table {{
                min-width: 900px;
            }}
            td, th {{
                padding: 10px 8px;
                font-size: 0.85rem;
            }}
            .tabs {{
                flex-wrap: wrap;
            }}
            .tab-btn {{
                padding: 8px;
                font-size: 0.85rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-title">
                <h1>ΩMEGA Engine</h1>
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
                    <div class="legend-item"><span class="signal-pill pill-sharp">🎰 HEAVY $</span> <b>Heavy Money:</b> 65%+ money & 10%+ divergence</div>
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
            <button class="tab-btn" onclick="openTab(event, 'vegas')">Vegas Board</button>
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
                        <tr><th>OMEGA</th><th>ALPHA SIGNALS</th><th>ALPHA CONTEXT</th><th>PLAYER</th><th>vs PITCHER</th><th>HR-PROP</th><th>HITS</th><th>BASES</th></tr>
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
                        <tr><th>BLENDED</th><th>OMEGA</th><th>CONF</th><th>PHY</th><th>MKT</th><th>ALPHA SIGNALS</th><th>ALPHA CONTEXT</th><th>TEAM</th><th>vs PITCHER</th><th>ITT</th><th>ML MOVE</th><th>TT MOVE</th><th>DIVERGENCE</th></tr>
                    </thead>
                    <tbody>
                        {"".join(team_rows)}
                    </tbody>
                </table>
            </div>
        </div>

        <!-- VEGAS TAB -->
        <div id="vegas" class="tab-content">
            <div class="card">
                <h2 style="display:flex; align-items:center; justify-content:center; gap:10px;">📊 Live Vegas Board & Line Movement</h2>
                <div style="overflow-x:auto;">
                    <table id="vegas-board-table" style="width:100%; text-align:left;">
                        <thead>
                            <tr style="background:rgba(255,255,255,0.01);">
                                <th rowspan="2" title="Game commencement time (EST)" style="text-align:left; font-size:0.75rem; color:var(--text-secondary); font-weight:700; cursor:help;">Date/Time</th>
                                <th rowspan="2" title="Team name and designation (Away/Home)" style="text-align:left; font-size:0.75rem; color:var(--text-secondary); font-weight:700; cursor:help;">Team</th>
                                <th colspan="3" title="Opening and live team implied run totals and movement delta" style="text-align:center; font-size:0.75rem; color:var(--text-secondary); font-weight:700; cursor:help;">Score (Implied Runs)</th>
                                <th colspan="3" title="Opening and live game totals, movement delta, and Over/Under consensus splits" style="text-align:center; font-size:0.75rem; color:var(--text-secondary); font-weight:700; cursor:help;">Over / Under</th>
                                <th colspan="5" title="Opening and live moneylines, movement delta, and consensus splits" style="text-align:center; font-size:0.75rem; color:var(--text-secondary); font-weight:700; cursor:help;">Moneyline</th>
                            </tr>
                            <tr style="font-size:0.7rem; font-weight:700; background:rgba(255,255,255,0.02);">
                                <th title="Opening team implied run total" style="text-align:center; color:var(--text-secondary); cursor:help;">Open</th>
                                <th title="Current live team implied run total" style="text-align:center; color:var(--text-secondary); cursor:help;">Live</th>
                                <th title="Run total movement delta" style="text-align:center; color:var(--text-secondary); cursor:help;">Diff</th>
                                <th title="Opening game Over/Under total" style="text-align:center; color:var(--text-secondary); cursor:help;">Open</th>
                                <th title="Current live game Over/Under total" style="text-align:center; color:var(--text-secondary); cursor:help;">Live</th>
                                <th title="Game total movement delta" style="text-align:center; color:var(--text-secondary); cursor:help;">Diff</th>
                                <th title="Consensus Bets: percentage of ticket bets placed on this team" style="text-align:center; color:var(--text-secondary); cursor:help;">Bets %</th>
                                <th title="Opening team moneyline" style="text-align:center; color:var(--text-secondary); cursor:help;">Open</th>
                                <th title="Current live team moneyline" style="text-align:center; color:var(--text-secondary); cursor:help;">Live</th>
                                <th title="Moneyline movement delta" style="text-align:center; color:var(--text-secondary); cursor:help;">Diff</th>
                                <th title="Consensus Money: percentage of total dollar handle placed on this team" style="text-align:center; color:var(--text-secondary); cursor:help;">Money %</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join(vegas_rows)}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <!-- ANALYSIS TAB -->
        <div id="analysis" class="tab-content">
            <div id="analysis-content">
                Loading analysis...
            </div>
        </div>
    </div>

    <!-- Details Modal -->
    <div id="details-modal" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background:rgba(0,0,0,0.85); z-index:1000; justify-content:center; align-items:center; backdrop-filter:blur(8px); padding:20px;">
        <div style="background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); padding:30px; max-width:550px; width:100%; position:relative; box-shadow:0 15px 50px rgba(0,0,0,0.8); animation:fadeIn 0.2s ease; overflow-y:auto; max-height:90%;">
            <span onclick="closeModal()" style="position:absolute; top:20px; right:25px; font-size:1.8rem; color:var(--text-secondary); cursor:pointer; font-weight:700; transition:color 0.2s;" onmouseover="this.style.color='#fff'" onmouseout="this.style.color='var(--text-secondary)'">&times;</span>
            <h2 id="modal-title" style="margin-top:0; font-size:1.6rem; font-weight:800; border-bottom:1px solid var(--border); padding-bottom:15px; margin-bottom:20px; color:#fff;">Details</h2>
            <div id="modal-body" style="font-size:0.95rem; color:var(--text-primary); line-height:1.6;">
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
        
        // Modal logic
        function showDetails(title, detailsHtml) {{
            document.getElementById('modal-title').innerText = title;
            document.getElementById('modal-body').innerHTML = detailsHtml;
            document.getElementById('details-modal').style.display = 'flex';
        }}
        function closeModal() {{
            document.getElementById('details-modal').style.display = 'none';
        }}
        window.onclick = function(event) {{
            const modal = document.getElementById('details-modal');
            if (event.target == modal) {{
                modal.style.display = "none";
            }}
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

                // Group children by H2 elements into separate visual cards
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
                        return;
                    }}

                    if (el.tagName === 'H2') {{
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
                        return;
                    }} else {{
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
            
        # Mirror to user's active sports_agent path
        try:
            mirror_path = os.path.join(os.path.dirname(config.BASE_DIR), "sports_agent", "konrad_sharp_model_v45.html")
            os.makedirs(os.path.dirname(mirror_path), exist_ok=True)
            with open(mirror_path, "w", encoding="utf-8") as f:
                f.write(html)
            print(f"[SYNC]: Mirrored dashboard to {mirror_path}")
        except Exception as e:
            print(f"[SYNC ERROR]: Could not mirror to sports_agent: {e}")
            
        return self.output_path
