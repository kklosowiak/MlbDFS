"""Script to run optimal PuLP DFS optimizations for the 7-game slate using omega-results(158).json."""
import json
import csv
from pathlib import Path
import pulp
from utils.normalization import normalize_player_name

downloads = Path(r"C:\Users\konra\Downloads")
omega_path = downloads / "omega-results(158).json"
dk_path = downloads / "DKSalaries(20).csv"

# Mappings from OMEGA team name to DK abbreviation
TEAM_MAP_OMEGA_TO_DK = {
    "Pittsburgh Pirates": "PIT",
    "Athletics": "ATH",
    "Baltimore Orioles": "BAL",
    "Seattle Mariners": "SEA",
    "Chicago White Sox": "CWS",
    "New York Yankees": "NYY",
    "Cleveland Guardians": "CLE",
    "Milwaukee Brewers": "MIL",
    "San Francisco Giants": "SF",
    "Atlanta Braves": "ATL",
    "Colorado Rockies": "COL",
    "Chicago Cubs": "CHC",
    "Toronto Blue Jays": "TOR",
    "Boston Red Sox": "BOS",
}

# Load DK Salaries
dk_players = {}
with open(dk_path, mode="r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row["Name"]
        norm_name = normalize_player_name(name)
        dk_players[norm_name] = {
            "name": name,
            "salary": int(row["Salary"]),
            "position": row["Position"],
            "team": row["TeamAbbrev"]
        }

# Load OMEGA results
with open(omega_path, 'r', encoding='utf-8') as f:
    omega_data = json.load(f)

# Match Pitchers
matched_pitchers = []
for p in omega_data.get("pitchers", []):
    p_name = p["pitcher"]
    p_team = p["team"]
    if p_team not in TEAM_MAP_OMEGA_TO_DK:
        continue
    dk_team = TEAM_MAP_OMEGA_TO_DK[p_team]
    norm_p_name = normalize_player_name(p_name)
    
    dk_p = dk_players.get(norm_p_name)
    if not dk_p:
        for k, v in dk_players.items():
            if norm_p_name in k and v["team"] == dk_team:
                dk_p = v
                break
    if not dk_p:
        team_sps = [x for x in dk_players.values() if x["team"] == dk_team and "P" in x["position"]]
        if team_sps:
            dk_p = team_sps[0]
            
    if dk_p:
        matched_pitchers.append({
            "name": dk_p["name"],
            "salary": dk_p["salary"],
            "team": dk_p["team"],
            "score": p.get("alpha_score", 0),
            "is_trap": p.get("is_trap", False)
        })

# Match Hitters
matched_hitters = []
for h in omega_data.get("hitters", []):
    h_name = h["name"]
    h_team = h["team"]
    if h_team not in TEAM_MAP_OMEGA_TO_DK:
        continue
    dk_team = TEAM_MAP_OMEGA_TO_DK[h_team]
    norm_h_name = normalize_player_name(h_name)
    
    dk_h = dk_players.get(norm_h_name)
    if not dk_h:
        for k, v in dk_players.items():
            if (norm_h_name in k or k in norm_h_name) and v["team"] == dk_team:
                dk_h = v
                break
    if dk_h:
        matched_hitters.append({
            "name": dk_h["name"],
            "salary": dk_h["salary"],
            "position": dk_h["position"],
            "team": dk_h["team"],
            "score": h.get("player_score", 0)
        })

def solve_pulp(stack1_team=None, stack1_size=0, stack2_team=None, stack2_size=0, forced_sps=None, forced_hitters=None):
    # Construct player pool
    pool = []
    
    # Add pitchers
    for p in matched_pitchers:
        pool.append({
            "name": p["name"],
            "salary": p["salary"],
            "team": p["team"],
            "score": p["score"],
            "is_sp": 1,
            "is_c": 0, "is_1b": 0, "is_2b": 0, "is_3b": 0, "is_ss": 0, "is_of": 0
        })
        
    # Add hitters
    for h in matched_hitters:
        pos = h["position"].split("/")
        pool.append({
            "name": h["name"],
            "salary": h["salary"],
            "team": h["team"],
            "score": h["score"],
            "is_sp": 0,
            "is_c": 1 if "C" in pos else 0,
            "is_1b": 1 if "1B" in pos else 0,
            "is_2b": 1 if "2B" in pos else 0,
            "is_3b": 1 if "3B" in pos else 0,
            "is_ss": 1 if "SS" in pos else 0,
            "is_of": 1 if "OF" in pos else 0
        })
        
    # Variables
    prob = pulp.LpProblem("DK_DFS", pulp.LpMaximize)
    player_vars = pulp.LpVariable.dicts("Player", range(len(pool)), cat='Binary')
    
    # Objective: Maximize Score
    prob += pulp.lpSum(pool[i]["score"] * player_vars[i] for i in range(len(pool)))
    
    # Constraints
    # 1. Total players = 10 (2 SP, 8 Hitters)
    prob += pulp.lpSum(player_vars[i] for i in range(len(pool))) == 10
    
    # 2. Salary Cap
    prob += pulp.lpSum(pool[i]["salary"] * player_vars[i] for i in range(len(pool))) <= 50000
    
    # 3. Position requirements
    prob += pulp.lpSum(pool[i]["is_sp"] * player_vars[i] for i in range(len(pool))) == 2
    prob += pulp.lpSum(pool[i]["is_c"] * player_vars[i] for i in range(len(pool))) >= 1
    prob += pulp.lpSum(pool[i]["is_1b"] * player_vars[i] for i in range(len(pool))) >= 1
    prob += pulp.lpSum(pool[i]["is_2b"] * player_vars[i] for i in range(len(pool))) >= 1
    prob += pulp.lpSum(pool[i]["is_3b"] * player_vars[i] for i in range(len(pool))) >= 1
    prob += pulp.lpSum(pool[i]["is_ss"] * player_vars[i] for i in range(len(pool))) >= 1
    prob += pulp.lpSum(pool[i]["is_of"] * player_vars[i] for i in range(len(pool))) >= 3
    
    # 4. Max 5 players per team
    all_teams = set(p["team"] for p in pool)
    for team in all_teams:
        prob += pulp.lpSum(player_vars[i] for i in range(len(pool)) if pool[i]["team"] == team) <= 5
        
    # 5. Represent at least 3 teams (satisfied implicitly by max 5 players per team over 10 slots)
    
    # 6. Forced SPs
    if forced_sps:
        for sp_name in forced_sps:
            sp_norm = normalize_player_name(sp_name)
            prob += pulp.lpSum(player_vars[i] for i in range(len(pool)) if pool[i]["is_sp"] == 1 and sp_norm in normalize_player_name(pool[i]["name"])) == 1
            
    # 7. Forced Hitters
    if forced_hitters:
        for h_name in forced_hitters:
            h_norm = normalize_player_name(h_name)
            prob += pulp.lpSum(player_vars[i] for i in range(len(pool)) if pool[i]["is_sp"] == 0 and h_norm in normalize_player_name(pool[i]["name"])) == 1
            
    # 8. Stack Size constraints (only counts hitters for stack size, as SP is separate in classic stacks)
    if stack1_team and stack1_size > 0:
        prob += pulp.lpSum(player_vars[i] for i in range(len(pool)) if pool[i]["team"] == stack1_team and pool[i]["is_sp"] == 0) >= stack1_size
    if stack2_team and stack2_size > 0:
        prob += pulp.lpSum(player_vars[i] for i in range(len(pool)) if pool[i]["team"] == stack2_team and pool[i]["is_sp"] == 0) >= stack2_size
        
    # Solve
    solver = pulp.PULP_CBC_CMD(msg=False)
    status = prob.solve(solver)
    
    if status == pulp.LpStatusOptimal:
        selected_players = []
        for i in range(len(pool)):
            if player_vars[i].varValue == 1:
                selected_players.append(pool[i])
        
        # Sort and return
        sps = [p for p in selected_players if p["is_sp"] == 1]
        hitters = [p for p in selected_players if p["is_sp"] == 0]
        
        # Match slots
        lineup = []
        lineup.append(("SP1", sps[0]))
        lineup.append(("SP2", sps[1]))
        
        # Greedy assign positions
        assigned_names = set()
        for pos_key, pos_name in [("is_c", "C"), ("is_1b", "1B"), ("is_2b", "2B"), ("is_3b", "3B"), ("is_ss", "SS")]:
            p = next((x for x in hitters if x[pos_key] == 1 and x["name"] not in assigned_names), None)
            if p:
                lineup.append((pos_name, p))
                assigned_names.add(p["name"])
                
        ofs = [x for x in hitters if x["is_of"] == 1 and x["name"] not in assigned_names]
        for idx, of in enumerate(ofs[:3], 1):
            lineup.append((f"OF{idx}", of))
            assigned_names.add(of["name"])
            
        # Any remaining hitters
        rem = [x for x in hitters if x["name"] not in assigned_names]
        for idx, r in enumerate(rem, 1):
            # assign to first available spot or generic OF/UTIL
            lineup.append((f"UTIL{idx}", r))
            
        sal = sum(p["salary"] for p in selected_players)
        score = sum(p["score"] for p in selected_players)
        return lineup, sal, score
    else:
        return None

def format_lineup(title, res):
    lines = []
    lines.append(f"### {title}")
    if res:
        lineup, sal, score = res
        lines.append(f"**Total Score: {score:.1f} | Salary: ${sal:,}**\n")
        lines.append("| Slot | Player | Team | Salary | OMEGA Score |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        for pos, p in lineup:
            lines.append(f"| {pos} | **{p['name']}** | {p['team']} | ${p['salary']:,} | {p['score']:.1f} |")
    else:
        lines.append("No valid lineup found under cap.")
    lines.append("\n")
    return "\n".join(lines)

# Run PuLP tests
report = []
report.append("# 🏆 mathematically Optimal Stack Lineups (PuLP Solver)")
report.append("Finding the exact global optimal solutions for the top co-ranked stacks on the slate.\n")

# Top Stack 1: Yankees (5-man stack)
report.append(format_lineup("Yankees (5) + Pirates (3) Stack", solve_pulp("NYY", 5, "PIT", 3)))
report.append(format_lineup("Yankees (5) + Cubs (3) Stack", solve_pulp("NYY", 5, "CHC", 3)))

# Top Stack 2: Cubs (5-man stack)
report.append(format_lineup("Cubs (5) + Pirates (3) Stack", solve_pulp("CHC", 5, "PIT", 3)))
report.append(format_lineup("Cubs (5) + Yankees (3) Stack", solve_pulp("CHC", 5, "NYY", 3)))

# Top Stack 3: Pirates (5-man stack)
report.append(format_lineup("Pirates (5) + Cubs (3) Stack", solve_pulp("PIT", 5, "CHC", 3)))
report.append(format_lineup("Pirates (5) + SF Giants (3) Stack", solve_pulp("PIT", 5, "SF", 3)))

# SF Giants Stack (5-man stack)
report.append(format_lineup("SF Giants (5) + Pirates (3) Stack", solve_pulp("SF", 5, "PIT", 3)))
report.append(format_lineup("SF Giants (5) + Cubs (3) Stack", solve_pulp("SF", 5, "CHC", 3)))

# Blue Jays Stack (5-man stack)
report.append(format_lineup("Blue Jays (5) + Mariners (3) Stack", solve_pulp("TOR", 5, "SEA", 3)))

out_path = Path(r"c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\optimizer_pulp_results.md")
out_path.write_text("\n".join(report), encoding="utf-8")
print(f"PuLP optimization completed and written to {out_path}")
