"""Script to optimize a DraftKings lineup with Skenes + Hancock, 5 ATH hitters, and at least 2 PIT hitters."""
import json
import csv
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

def load_salaries(path):
    salaries = []
    with open(path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            salaries.append({
                "Position": row["Position"],
                "Name": row["Name"],
                "Salary": int(row["Salary"]),
                "Team": row["TeamAbbrev"],
            })
    return salaries

def main():
    omega_path = Path(r"C:\Users\konra\Downloads\omega-results(168).json")
    dk_path = Path(r"C:\Users\konra\Downloads\DKSalaries(23).csv")
    
    with open(omega_path, "r", encoding="utf-8") as f:
        omega_data = json.load(f)
        
    dk_players = load_salaries(dk_path)
    target_dk_teams = {'BAL', 'LAD', 'PIT', 'COL', 'LAA', 'ATH', 'MIN', 'ARI', 'NYM', 'PHI', 'BOS', 'SEA', 'CLE', 'HOU'}
    dk_players = [p for p in dk_players if p["Team"] in target_dk_teams]
    
    dk_by_name = {}
    for p in dk_players:
        norm_name = normalize_player_name(p["Name"])
        dk_by_name[norm_name] = p
        
    # Pitchers
    pitchers = [p for p in omega_data.get("pitchers", []) if TEAM_MAP_OMEGA_TO_DK.get(p["team"]) in target_dk_teams]
    matched_pitchers = []
    for p in pitchers:
        p_team_dk = TEAM_MAP_OMEGA_TO_DK[p["team"]]
        norm_p_name = normalize_player_name(p["pitcher"])
        dk_p = dk_by_name.get(norm_p_name)
        if not dk_p:
            for k, v in dk_by_name.items():
                if (norm_p_name in k or k in norm_p_name) and v["Team"] == p_team_dk:
                    dk_p = v
                    break
        if not dk_p:
            team_sps = [x for x in dk_players if x["Team"] == p_team_dk and "P" in x["Position"]]
            if team_sps:
                dk_p = team_sps[0]
        if dk_p:
            p["salary"] = dk_p["Salary"]
            p["dk_abbr"] = p_team_dk
            p["dk_name"] = dk_p["Name"]
            matched_pitchers.append(p)
            
    # Hitters
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
            matched_hitters.append(h)

    # Solve PuLP
    players = {}
    for p in matched_pitchers:
        if p.get("is_trap"):
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
        
    prob = pulp.LpProblem("DK_DFS_FORCED_SPS", pulp.LpMaximize)
    x = {}
    for p_name, p_info in players.items():
        for pos in p_info["positions"]:
            var_key = f"x_{p_name}_{pos}".replace(" ", "_").replace("'", "_").replace("-", "_").replace(".", "_")
            x[(p_name, pos)] = pulp.LpVariable(var_key, cat="Binary")
            
    # Objective
    prob += pulp.lpSum(players[p_name]["score"] * x[(p_name, pos)] for p_name, p_info in players.items() for pos in p_info["positions"])
    
    # Constraints
    prob += pulp.lpSum(players[p_name]["salary"] * x[(p_name, pos)] for p_name, p_info in players.items() for pos in p_info["positions"]) <= 50000
    for p_name, p_info in players.items():
        prob += pulp.lpSum(x[(p_name, pos)] for pos in p_info["positions"]) <= 1
        
    prob += pulp.lpSum(x[(p_name, "SP")] for p_name, p_info in players.items() if "SP" in p_info["positions"]) == 2
    prob += pulp.lpSum(x[(p_name, "C")] for p_name, p_info in players.items() if "C" in p_info["positions"]) == 1
    prob += pulp.lpSum(x[(p_name, "1B")] for p_name, p_info in players.items() if "1B" in p_info["positions"]) == 1
    prob += pulp.lpSum(x[(p_name, "2B")] for p_name, p_info in players.items() if "2B" in p_info["positions"]) == 1
    prob += pulp.lpSum(x[(p_name, "3B")] for p_name, p_info in players.items() if "3B" in p_info["positions"]) == 1
    prob += pulp.lpSum(x[(p_name, "SS")] for p_name, p_info in players.items() if "SS" in p_info["positions"]) == 1
    prob += pulp.lpSum(x[(p_name, "OF")] for p_name, p_info in players.items() if "OF" in p_info["positions"]) == 3
    
    # Max 5 players per team
    teams_list = set(p_info["team"] for p_info in players.values())
    for t in teams_list:
        prob += pulp.lpSum(x[(p_name, pos)] for p_name, p_info in players.items() if p_info["team"] == t for pos in p_info["positions"]) <= 5
        
    # Oakland (ATH) 5-man Hitter Stack Constraint
    prob += pulp.lpSum(x[(p_name, pos)] for p_name, p_info in players.items() if p_info["team"] == "ATH" and not p_info["is_pitcher"] for pos in p_info["positions"] if pos != "SP") == 5

    # Pittsburgh (PIT) Hitter Stack Constraint (at least 2 hitters)
    prob += pulp.lpSum(x[(p_name, pos)] for p_name, p_info in players.items() if p_info["team"] == "PIT" and not p_info["is_pitcher"] for pos in p_info["positions"] if pos != "SP") >= 2

    # Force Skenes and Hancock
    prob += pulp.lpSum(x[(p_name, pos)] for p_name, p_info in players.items() if p_name == "Paul Skenes" for pos in p_info["positions"]) == 1
    prob += pulp.lpSum(x[(p_name, pos)] for p_name, p_info in players.items() if p_name == "Emerson Hancock" for pos in p_info["positions"]) == 1

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
        
        print("\n--- OAKLAND 5-MAN STACK WITH PIT BAT(S) (FORCED PITCHERS: SKENES + HANCOCK) ---")
        print(f"Total Score: {score:.1f} | Salary: ${sal:,}")
        for pos, p in sorted_lineup:
            print(f"{pos:6} | {p['name']:25} | {p['team']:4} | ${p['salary']:,} | OMEGA: {p['score']:.1f}")
    else:
        print("No optimal lineup found satisfying the constraints.")

if __name__ == "__main__":
    main()
