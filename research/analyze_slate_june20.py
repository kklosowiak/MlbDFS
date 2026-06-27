"""Script to analyze the June 20 slate using omega-results(168).json and DKSalaries(23).csv."""
import json
import csv
import sys
from pathlib import Path
import pulp
from utils.normalization import normalize_player_name

TEAM_MAP_OMEGA_TO_DK = {
    "San Diego Padres": "SD",
    "Miami Marlins": "MIA",
    "Pittsburgh Pirates": "PIT",
    "Athletics": "ATH",
    "Los Angeles Angels": "LAA",
    "Chicago Cubs": "CHC",
    "Arizona Diamondbacks": "ARI",
    "Milwaukee Brewers": "MIL",
    "Minnesota Twins": "MIN",
    "Texas Rangers": "TEX",
    "Tampa Bay Rays": "TB",
    "Philadelphia Phillies": "PHI",
    "Houston Astros": "HOU",
    "Washington Nationals": "WSH",
    "Los Angeles Dodgers": "LAD",
    "Cleveland Guardians": "CLE",
    "Colorado Rockies": "COL",
    "Toronto Blue Jays": "TOR",
    "Atlanta Braves": "ATL",
    "Seattle Mariners": "SEA",
    "Baltimore Orioles": "BAL",
    "New York Mets": "NYM",
    "San Francisco Giants": "SF",
    "Boston Red Sox": "BOS",
}

TEAM_MAP_DK_TO_OMEGA = {v: k for k, v in TEAM_MAP_OMEGA_TO_DK.items()}

def load_salaries(path):
    salaries = []
    with open(path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            salaries.append({
                "Position": row["Position"],
                "Name": row["Name"],
                "Salary": int(row["Salary"]),
                "GameInfo": row["Game Info"],
                "Team": row["TeamAbbrev"],
                "AvgPts": float(row["AvgPointsPerGame"]) if row["AvgPointsPerGame"] else 0.0,
            })
    return salaries

def stack_sigs(t):
    out = []
    if t.get("is_whale"): out.append("WHALE")
    if t.get("is_shark"): out.append("SHARK")
    if t.get("is_sharp"): out.append("HEAVY$")
    if t.get("is_burst"): out.append("BURST")
    if t.get("is_blind_spot"): out.append("BLIND")
    if t.get("is_trap"): out.append("CHALK")
    bf = t.get("bullpen_fatigue", 0) or 0
    if bf >= 90: out.append("EXHAUSTED")
    elif bf >= 75: out.append("GASSED")
    elif bf >= 65: out.append("WEARY")
    if t.get("trend") == "SURGING": out.append("SURGE")
    return out

def pitcher_sigs(p):
    out = []
    if p.get("is_trap"): out.append("TRAP")
    if p.get("is_hazard"): out.append("HAZARD")
    if p.get("is_shark"): out.append("SHARK")
    if p.get("is_whale"): out.append("WHALE")
    if p.get("is_sharp"): out.append("HEAVY$")
    if p.get("form_status") == "SURGING": out.append("SURGING")
    if p.get("form_status") == "COLD": out.append("COLD")
    if p.get("is_low_ceiling"): out.append("LOW_CEIL")
    if p.get("is_paradox"): out.append("PARADOX")
    return out

def main():
    omega_path = Path(r"C:\Users\konra\Downloads\omega-results(168).json")
    dk_path = Path(r"C:\Users\konra\Downloads\DKSalaries(23).csv")
    
    if not omega_path.exists() or not dk_path.exists():
        print(f"Error: Missing files. Omega: {omega_path.exists()}, DK: {dk_path.exists()}")
        sys.exit(1)
        
    with open(omega_path, "r", encoding="utf-8") as f:
        omega_data = json.load(f)
        
    dk_players = load_salaries(dk_path)
    
    # 14 teams selected in the screenshot
    target_dk_teams = {'BAL', 'LAD', 'PIT', 'COL', 'LAA', 'ATH', 'MIN', 'ARI', 'NYM', 'PHI', 'BOS', 'SEA', 'CLE', 'HOU'}
    
    # Filter DK players to only target teams
    dk_players = [p for p in dk_players if p["Team"] in target_dk_teams]
    
    # Group DK players by normalized name
    dk_by_name = {}
    for p in dk_players:
        norm_name = normalize_player_name(p["Name"])
        dk_by_name[norm_name] = p
        
    print(f"Loaded {len(dk_players)} players from DK Salaries.")
    
    # 1. Stacks / Teams Analysis
    teams = [t for t in omega_data.get("teams", []) if TEAM_MAP_OMEGA_TO_DK.get(t["team"]) in target_dk_teams]
    for t in teams:
        t["dk_abbr"] = TEAM_MAP_OMEGA_TO_DK[t["team"]]
    
    # 2. Pitchers Analysis
    pitchers = [p for p in omega_data.get("pitchers", []) if TEAM_MAP_OMEGA_TO_DK.get(p["team"]) in target_dk_teams]
    matched_pitchers = []
    
    for p in pitchers:
        p_team_dk = TEAM_MAP_OMEGA_TO_DK[p["team"]]
        norm_p_name = normalize_player_name(p["pitcher"])
        
        # Match by name first
        if p["pitcher"].lower() == "tbd":
            dk_p = None
        else:
            dk_p = dk_by_name.get(norm_p_name)
            if not dk_p:
                # Try to search partial name
                for k, v in dk_by_name.items():
                    if (norm_p_name in k or k in norm_p_name) and v["Team"] == p_team_dk:
                        dk_p = v
                        break
            if not dk_p:
                # Try to match by team and position SP or RP
                team_sps = [x for x in dk_players if x["Team"] == p_team_dk and "P" in x["Position"]]
                if team_sps:
                    dk_p = team_sps[0]
                    print(f"[MATCH FALLBACK]: Matched pitcher {p['pitcher']} to {dk_p['Name']} by team {p_team_dk}")
                else:
                    print(f"[WARNING]: Could not match pitcher {p['pitcher']} ({p['team']}) to DraftKings salaries.")
                
        salary = dk_p["Salary"] if dk_p else 0
        p["salary"] = salary
        p["dk_abbr"] = p_team_dk
        p["value_score"] = (p.get("alpha_score", 0) / (salary / 1000)) if salary > 0 else 0
        p["dk_name"] = dk_p["Name"] if dk_p else f"TBD ({p['team']})"
        matched_pitchers.append(p)
        
    # 3. Hitters Analysis
    hitters = [h for h in omega_data.get("hitters", []) if TEAM_MAP_OMEGA_TO_DK.get(h["team"]) in target_dk_teams]
    matched_hitters = []
    for h in hitters:
        norm_h_name = normalize_player_name(h["name"])
        dk_h = dk_by_name.get(norm_h_name)
        
        if not dk_h:
            for name_key, dk_p in dk_by_name.items():
                if (norm_h_name in name_key or name_key in norm_h_name) and dk_p["Team"] == TEAM_MAP_OMEGA_TO_DK[h["team"]]:
                    dk_h = dk_p
                    break
                    
        if dk_h:
            h["salary"] = dk_h["Salary"]
            h["position"] = dk_h["Position"]
            h["dk_abbr"] = TEAM_MAP_OMEGA_TO_DK[h["team"]]
            h["value_score"] = (h.get("player_score", 0) / (dk_h["Salary"] / 1000)) if dk_h["Salary"] > 0 else 0
            matched_hitters.append(h)
            
    print(f"Matched {len(matched_pitchers)} pitchers and {len(matched_hitters)} hitters.")
    
    # Run PuLP Solver to optimize lineups
    def solve_pulp(stack1_team=None, stack1_size=0, stack2_team=None, stack2_size=0, avoid_traps=True):
        # We want to create variables for each player and position they can play.
        players = {}
        for p in matched_pitchers:
            if avoid_traps and p.get("is_trap"):
                continue
            players[p["dk_name"]] = {
                "name": p["dk_name"],
                "team": p["dk_abbr"],
                "salary": p["salary"],
                "score": p.get("alpha_score", 0),
                "is_pitcher": True,
                "positions": ["SP"]
            }
            
        for h in matched_hitters:
            pos_list = h["position"].split("/")
            players[h["name"]] = {
                "name": h["name"],
                "team": h["dk_abbr"],
                "salary": h["salary"],
                "score": h.get("player_score", 0),
                "is_pitcher": False,
                "positions": pos_list
            }
            
        prob = pulp.LpProblem("DK_DFS", pulp.LpMaximize)
        
        # Decision variables: x[player_name, position]
        x = {}
        for p_name, p_info in players.items():
            for pos in p_info["positions"]:
                var_key = f"x_{p_name}_{pos}".replace(" ", "_").replace("'", "_").replace("-", "_").replace(".", "_")
                x[(p_name, pos)] = pulp.LpVariable(var_key, cat="Binary")
                
        # Objective: Maximize OMEGA score
        prob += pulp.lpSum(players[p_name]["score"] * x[(p_name, pos)] for p_name, p_info in players.items() for pos in p_info["positions"])
        
        # Constraints
        # 1. Salary Cap
        prob += pulp.lpSum(players[p_name]["salary"] * x[(p_name, pos)] for p_name, p_info in players.items() for pos in p_info["positions"]) <= 50000
        
        # 2. Each player selected at most once
        for p_name, p_info in players.items():
            prob += pulp.lpSum(x[(p_name, pos)] for pos in p_info["positions"]) <= 1
            
        # 3. Position slots
        prob += pulp.lpSum(x[(p_name, "SP")] for p_name, p_info in players.items() if "SP" in p_info["positions"]) == 2
        prob += pulp.lpSum(x[(p_name, "C")] for p_name, p_info in players.items() if "C" in p_info["positions"]) == 1
        prob += pulp.lpSum(x[(p_name, "1B")] for p_name, p_info in players.items() if "1B" in p_info["positions"]) == 1
        prob += pulp.lpSum(x[(p_name, "2B")] for p_name, p_info in players.items() if "2B" in p_info["positions"]) == 1
        prob += pulp.lpSum(x[(p_name, "3B")] for p_name, p_info in players.items() if "3B" in p_info["positions"]) == 1
        prob += pulp.lpSum(x[(p_name, "SS")] for p_name, p_info in players.items() if "SS" in p_info["positions"]) == 1
        prob += pulp.lpSum(x[(p_name, "OF")] for p_name, p_info in players.items() if "OF" in p_info["positions"]) == 3
        
        # 4. Max 5 players per team
        teams_list = set(p_info["team"] for p_info in players.values())
        for t in teams_list:
            prob += pulp.lpSum(x[(p_name, pos)] for p_name, p_info in players.items() if p_info["team"] == t for pos in p_info["positions"]) <= 5
            
        # 5. Stacking constraints (hitters only)
        if stack1_team and stack1_size > 0:
            prob += pulp.lpSum(x[(p_name, pos)] for p_name, p_info in players.items() if p_info["team"] == stack1_team and not p_info["is_pitcher"] for pos in p_info["positions"] if pos != "SP") >= stack1_size
        if stack2_team and stack2_size > 0:
            prob += pulp.lpSum(x[(p_name, pos)] for p_name, p_info in players.items() if p_info["team"] == stack2_team and not p_info["is_pitcher"] for pos in p_info["positions"] if pos != "SP") >= stack2_size
            
        # Solve
        solver = pulp.PULP_CBC_CMD(msg=False)
        status = prob.solve(solver)
        
        if status == pulp.LpStatusOptimal:
            selected_players = []
            for p_name, p_info in players.items():
                for pos in p_info["positions"]:
                    if x[(p_name, pos)].varValue == 1:
                        selected_players.append({
                            "name": p_name,
                            "team": p_info["team"],
                            "salary": p_info["salary"],
                            "score": p_info["score"],
                            "slot": pos
                        })
            
            # Sort lineup
            sorted_lineup = []
            sps = [p for p in selected_players if p["slot"] == "SP"]
            for idx, sp in enumerate(sps, 1):
                sorted_lineup.append((f"SP{idx}", sp))
            for pos in ["C", "1B", "2B", "3B", "SS"]:
                p = next((x for x in selected_players if x["slot"] == pos), None)
                if p:
                    sorted_lineup.append((pos, p))
            ofs = [p for p in selected_players if p["slot"] == "OF"]
            for idx, of in enumerate(ofs, 1):
                sorted_lineup.append((f"OF{idx}", of))
                
            sal = sum(x["salary"] for x in selected_players)
            score = sum(x["score"] for x in selected_players)
            return sorted_lineup, sal, score
        return None

    def format_lineup_md(title, res):
        lines = []
        lines.append(f"### {title}")
        if res:
            lineup, sal, score = res
            lines.append(f"**Total OMEGA Projected Score: {score:.1f} | Salary: ${sal:,}**\n")
            lines.append("| Slot | Player | Team | Salary | OMEGA Score |")
            lines.append("| :--- | :--- | :--- | :--- | :--- |")
            for pos, p in lineup:
                lines.append(f"| {pos} | **{p['name']}** | {p['team']} | ${p['salary']:,} | {p['score']:.1f} |")
        else:
            lines.append("No valid lineup found under cap.")
        lines.append("\n")
        return "\n".join(lines)

    # Sort and print results to markdown
    report = []
    report.append(f"# 📊 OMEGA DFS Analysis: June 20 Slate")
    report.append(f"**DraftKings Salaries & OMEGA Model Export Matching** (Snapshot: {omega_data.get('timestamp')})\n")
    
    report.append("## ⚾ Stack Rankings (Team Offense)")
    report.append("Sorted by OMEGA Stack Score. High stack scores combined with high Attack Confidence represent prime targets.\n")
    report.append("| Rank | Team | Opponent | Stack Score | CONF | Implied Runs | Bullpen Fatigue | Signals | Opp Pitcher |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    teams_sorted = sorted(teams, key=lambda x: -x.get("stack_score", 0))
    for i, t in enumerate(teams_sorted, 1):
        sigs = stack_sigs(t)
        total_sig = t.get("total_signal") or "-"
        opp_abbr = TEAM_MAP_OMEGA_TO_DK.get(t.get("opponent"), t.get("opponent")[:3].upper())
        report.append(
            f"| {i} | **{t['team']}** ({t['dk_abbr']}) | {opp_abbr} | {t.get('stack_score', 0):.1f} | {t.get('attack_conf', 0)}% | {t.get('implied_total', 0.0):.1f} | {t.get('bullpen_fatigue', 0)}% | {','.join(sigs) or '-'} {total_sig} | {t.get('opp_pitcher', 'TBD')} |"
        )
    report.append("\n" + "---" + "\n")
    
    # --- Pitchers ---
    report.append("## 投 Pitcher Rankings")
    report.append("Sorted by Value Score (OMEGA Score / $1k Salary). Traps are highlighted separately.\n")
    report.append("| Rank | Pitcher | Team | Salary | OMEGA Score | CONF | Value Score | Form | Notes |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    pitchers_clean = [p for p in matched_pitchers if not p.get("is_trap")]
    pitchers_traps = [p for p in matched_pitchers if p.get("is_trap")]
    
    pitchers_clean_sorted = sorted(pitchers_clean, key=lambda x: -x["value_score"])
    for i, p in enumerate(pitchers_clean_sorted, 1):
        sigs = pitcher_sigs(p)
        report.append(
            f"| {i} | **{p['dk_name']}** | {p['dk_abbr']} | ${p['salary']:,} | {p.get('alpha_score', 0):.1f} | {p.get('attack_conf', 0)}% | **{p['value_score']:.2f}** | {p.get('form_status', 'Neutral')} | {','.join(sigs) or '-'} |"
        )
        
    if pitchers_traps:
        report.append("\n### 🚨 SP Trap Warnings")
        report.append("Vegas Traps / Short Leash arms to fade or stack against:\n")
        report.append("| Pitcher | Team | Salary | OMEGA Score | CONF | Value Score | Trap Type | Notes |")
        report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for p in sorted(pitchers_traps, key=lambda x: -x["value_score"]):
            sigs = pitcher_sigs(p)
            report.append(
                f"| **{p['dk_name']}** | {p['dk_abbr']} | ${p['salary']:,} | {p.get('alpha_score', 0):.1f} | {p.get('attack_conf', 0)}% | {p['value_score']:.2f} | **{p.get('trap_type', 'Trap')}** | {','.join(sigs) or '-'} |"
            )
            
    report.append("\n" + "---" + "\n")
    
    # --- Top Value Hitters ---
    report.append("## 🎯 Hitter Value Rankings")
    report.append("Top salary-saving values on the slate (OMEGA Score >= 65, sorted by Value Score = Score/$1k).\n")
    report.append("| Rank | Player | Pos | Team | Salary | OMEGA Score | Value Score | Platoon Label | Target | Opp Pitcher |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    hitters_value = [h for h in matched_hitters if h.get("player_score", 0) >= 65]
    hitters_value_sorted = sorted(hitters_value, key=lambda x: -x["value_score"])[:30]
    
    for i, h in enumerate(hitters_value_sorted, 1):
        target_str = "🎯 Yes" if h.get("is_juiced_target") else "No"
        report.append(
            f"| {i} | **{h['name']}** | {h['position']} | {h['dk_abbr']} | ${h['salary']:,} | {h.get('player_score', 0):.1f} | **{h['value_score']:.2f}** | {h.get('platoon_label', 'NEUTRAL')} | {target_str} | {h.get('opp_pitcher', 'TBD')} |"
        )
        
    report.append("\n" + "---" + "\n")
    
    # --- Slate Breakers ---
    report.append("## 👑 Slate-Breakers (Top Raw Projections)")
    report.append("The highest projected hitters on the 14-game slate, regardless of price:\n")
    report.append("| Rank | Player | Pos | Team | Salary | OMEGA Score | Value Score | Platoon Label | Target | Opp Pitcher |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    hitters_raw_sorted = sorted(matched_hitters, key=lambda x: -x.get("player_score", 0))[:20]
    for i, h in enumerate(hitters_raw_sorted, 1):
        target_str = "🎯 Yes" if h.get("is_juiced_target") else "No"
        report.append(
            f"| {i} | **{h['name']}** | {h['position']} | {h['dk_abbr']} | ${h['salary']:,} | {h.get('player_score', 0):.1f} | {h['value_score']:.2f} | {h.get('platoon_label', 'NEUTRAL')} | {target_str} | {h.get('opp_pitcher', 'TBD')} |"
        )
        
    # --- PuLP Optimizations ---
    report.append("\n" + "---" + "\n")
    report.append("## 🏆 Mathematically Optimal Lineups")
    report.append("Linear programming solutions utilizing PuLP. These find the highest projected scores possible under the $50k salary cap with strict position/team rules.\n")
    
    # Raw Optimal (no stack constraints)
    report.append(format_lineup_md("Raw Optimal (No Stack Constraints, Trap Pitchers Avoided)", solve_pulp()))
    
    # Find the top offenses based on stack score to run stacks for
    top_teams = [t["dk_abbr"] for t in teams_sorted[:4]]
    
    # We will generate stacks for the top offenses
    for team in top_teams:
        # 5-man stack of team, plus 3-man stack of the next best team
        other_teams = [t for t in top_teams if t != team]
        if other_teams:
            stack2 = other_teams[0]
            report.append(format_lineup_md(f"{team} (5) + {stack2} (3) Stack", solve_pulp(team, 5, stack2, 3)))
            
    # Write report to file
    report_text = "\n".join(report)
    out_md = Path(r"c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\june20_slate_analysis.md")
    out_md.write_text(report_text, encoding="utf-8")
    print(f"Report successfully written to {out_md}")

if __name__ == "__main__":
    main()
