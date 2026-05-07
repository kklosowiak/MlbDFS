import json
from collections import defaultdict

def generate_report():
    with open('reports/latest_results.json', 'r') as f:
        data = json.load(f)

    # Dictionaries for quick lookup
    teams_dict = {t['team']: t for t in data['teams']}
    pitchers_dict = {p['pitcher']: p for p in data['pitchers']}
    
    # Group hitters by team
    hitters_by_team = defaultdict(list)
    for h in data['hitters']:
        hitters_by_team[h['team']].append(h)
    
    for team in hitters_by_team:
        hitters_by_team[team] = sorted(hitters_by_team[team], key=lambda x: x.get('player_score', 0), reverse=True)[:3]

    # Reconstruct games
    # We have away @ home. We can group by opponent pairs.
    processed_teams = set()
    games = []
    
    for t in data['teams']:
        if t['team'] in processed_teams: continue
        away = t['team']
        home = t['opponent']
        processed_teams.add(away)
        processed_teams.add(home)
        games.append((away, home))

    md = []
    md.append("# ⚾ OMEGA Main Slate Analysis (10 Games)\n\n")
    
    for away, home in games:
        away_t = teams_dict.get(away, {})
        home_t = teams_dict.get(home, {})
        
        md.append(f"## {away} @ {home}")
        
        # Totals & Movement
        signal_away = away_t.get('total_signal', '')
        signal_home = home_t.get('total_signal', '')
        signal = signal_away if signal_away else signal_home
        
        md.append(f"**Vegas Implied Totals:** {away}: {away_t.get('implied_total', '?')} | {home}: {home_t.get('implied_total', '?')}")
        md.append(f"**Over/Under Signal:** {signal}")
        
        # Market Flags
        for team, t_data in [(away, away_t), (home, home_t)]:
            flags = [k.replace('is_', '').upper() for k, v in t_data.items() if k.startswith('is_') and v and k not in ['is_gassed', 'is_fatigued', 'is_burst']]
            if flags:
                md.append(f"**{team} Market Movement:** {', '.join(flags)} (ML Move: {t_data.get('ml_move', 0)})")
        md.append("\n")

        # Pitching Analysis
        md.append("### 🎯 Pitching Matchup")
        away_p_name = home_t.get('opp_pitcher', 'TBD') # Away pitcher faces home team
        home_p_name = away_t.get('opp_pitcher', 'TBD') # Home pitcher faces away team
        
        away_p = pitchers_dict.get(away_p_name, {})
        home_p = pitchers_dict.get(home_p_name, {})
        
        def format_pitcher(name, p):
            if not p: return f"- **{name}:** No data"
            p_flags = []
            if p.get('is_hazard'): p_flags.append('HAZARD')
            if p.get('is_paradox'): p_flags.append('PARADOX')
            flags_str = f" [{', '.join(p_flags)}]" if p_flags else ""
            return f"- **{name}:** Alpha {p.get('alpha_score', 0):.1f} | K-line {p.get('k_line', '?')} | CSW {p.get('csw', 0):.3f}{flags_str}"
        
        md.append(format_pitcher(away_p_name, away_p))
        md.append(format_pitcher(home_p_name, home_p))
        md.append("\n")
        
        # Stack & Hitter Analysis
        md.append("### 🏏 Stacks & Hitters")
        for team, t_data in [(away, away_t), (home, home_t)]:
            md.append(f"- **{team} Stack (Score: {t_data.get('stack_score', 0):.1f}):** xwOBA {t_data.get('team_xwoba', 0):.3f} | Conc: {t_data.get('power_concentration', 0):.3f}")
            targets = []
            for h in hitters_by_team.get(team, []):
                h_flags = "🔥" if h.get('is_hot') else ""
                h_flags += "🎯" if h.get('is_juiced_target') else ""
                targets.append(f"{h['name']} ({h.get('matchup_xwoba', 0):.3f} xwOBA){h_flags}")
            if targets:
                md.append(f"  - *Top Bats:* {', '.join(targets)}")
        
        md.append("\n---\n")

    md.append("## 🏆 Final DFS Convictions\n")
    md.append("**Top Pitching Anchor (SP1):**\n")
    md.append("**Top Pitching Value (SP2):**\n")
    md.append("**The Priority Stack (RUNS):**\n")
    md.append("**The Contrarian Pivot Stack:**\n")

    with open('reports/slate_analysis.md', 'w', encoding='utf-8') as f:
        f.write('\n'.join(md))

if __name__ == '__main__':
    generate_report()
