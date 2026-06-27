import json
import csv
import itertools
from pathlib import Path

downloads = Path(r"C:\Users\konra\Downloads")
f155 = downloads / "omega-results(155).json"
dk_path = Path(r"C:\Users\konra\Downloads\DKSalaries(20).csv")

# Load DK Salaries
dk_players = {}
with open(dk_path, mode="r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        name = row["Name"].lower()
        dk_players[name] = {
            "name": row["Name"],
            "salary": int(row["Salary"]),
            "position": row["Position"],
            "team": row["TeamAbbrev"]
        }

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

# Load OMEGA results
with open(f155, 'r', encoding='utf-8') as f:
    omega_data = json.load(f)

# Match Pitchers
matched_pitchers = []
for p in omega_data.get("pitchers", []):
    p_name = p["pitcher"]
    p_team = p["team"]
    if p_team not in TEAM_MAP_OMEGA_TO_DK:
        continue
    dk_team = TEAM_MAP_OMEGA_TO_DK[p_team]
    norm_p_name = p_name.lower()
    dk_p = dk_players.get(norm_p_name)
    if not dk_p:
        # search partial
        for k, v in dk_players.items():
            if norm_p_name in k and v["team"] == dk_team:
                dk_p = v
                break
    if not dk_p:
        # Fallback to team search
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
    norm_h_name = h_name.lower()
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

print(f"Matched {len(matched_pitchers)} pitchers and {len(matched_hitters)} hitters.")

def solve_lineup(pitchers, hitters, stack1_team=None, stack1_size=0, stack2_team=None, stack2_size=0):
    expanded_hitters = []
    for h in hitters:
        positions = h["position"].split("/")
        for pos in positions:
            expanded_hitters.append({
                "name": h["name"],
                "salary": h["salary"],
                "position": pos,
                "team": h["team"],
                "score": h["score"]
            })
            
    # Group by position
    by_pos = {"SP": [], "C": [], "1B": [], "2B": [], "3B": [], "SS": [], "OF": []}
    for p in pitchers:
        by_pos["SP"].append(p)
        
    for h in expanded_hitters:
        if h["position"] in by_pos:
            by_pos[h["position"]].append(h)
            
    # Sort options by score to prune search quickly
    for k in by_pos:
        by_pos[k].sort(key=lambda x: -x["score"])
        
    best_lineup = None
    best_score = 0
    
    # Pre-select SP pairs
    sp_pairs = list(itertools.combinations(by_pos["SP"], 2))
    sp_pairs.sort(key=lambda x: -(x[0]["score"] + x[1]["score"]))
    
    print(f"Searching combinations for stack: {stack1_team} ({stack1_size}) + {stack2_team} ({stack2_size})")
    
    # We search the top 15 SP pairs
    for sp1, sp2 in sp_pairs[:15]:
        sp_sal = sp1["salary"] + sp2["salary"]
        if sp_sal > 22000: # avoid overspending on pitchers
            continue
            
        sp_teams = {}
        sp_teams[sp1["team"]] = sp_teams.get(sp1["team"], 0) + 1
        sp_teams[sp2["team"]] = sp_teams.get(sp2["team"], 0) + 1
        
        # Hitter positions order: C, 1B, 2B, 3B, SS
        pos_list = ["C", "1B", "2B", "3B", "SS"]
        
        # Tighter search limits to make it run in < 1 second:
        # C: top 8, 1B: top 8, 2B: top 8, 3B: top 8, SS: top 8, OF: top 12
        limit_pos = 7
        limit_of = 10
        
        def search_hitters(idx, current_salary, current_score, selected_players, team_counts):
            nonlocal best_score, best_lineup
            
            # Pruning
            max_rem = 0
            if idx < len(pos_list):
                for p_idx in range(idx, len(pos_list)):
                    pos = pos_list[p_idx]
                    if by_pos[pos]:
                        max_rem += by_pos[pos][0]["score"]
                # OFs
                max_rem += sum(x["score"] for x in by_pos["OF"][:3])
            else:
                rem_ofs = 3 - (len(selected_players) - 7)
                if rem_ofs > 0:
                    max_rem += sum(x["score"] for x in by_pos["OF"][:rem_ofs])
            if current_score + max_rem <= best_score:
                return
                
            if idx == len(pos_list):
                search_ofs(0, current_salary, current_score, selected_players, team_counts, 0)
                return
                
            pos = pos_list[idx]
            for p in by_pos[pos][:limit_pos]:
                if any(x["name"] == p["name"] for x in selected_players):
                    continue
                new_sal = current_salary + p["salary"]
                if new_sal > 50000:
                    continue
                    
                new_team_counts = team_counts.copy()
                new_team_counts[p["team"]] = new_team_counts.get(p["team"], 0) + 1
                if new_team_counts[p["team"]] > 5:
                    continue
                    
                search_hitters(idx + 1, new_sal, current_score + p["score"], selected_players + [p], new_team_counts)
                
        def search_ofs(of_idx, current_salary, current_score, selected_players, team_counts, start_of_idx):
            nonlocal best_score, best_lineup
            
            # Pruning
            rem_ofs = 3 - of_idx
            if rem_ofs > 0:
                max_rem = sum(x["score"] for x in by_pos["OF"][start_of_idx : start_of_idx + rem_ofs])
                if current_score + max_rem <= best_score:
                    return
                    
            if of_idx == 3:
                # Validate stack constraints
                if stack1_team:
                    if team_counts.get(stack1_team, 0) < stack1_size:
                        return
                if stack2_team:
                    if team_counts.get(stack2_team, 0) < stack2_size:
                        return
                        
                # Check team count rule: must have at least 3 teams represented
                all_teams = set(x["team"] for x in selected_players)
                if len(all_teams) < 3:
                    return
                    
                if current_score > best_score:
                    best_score = current_score
                    best_lineup = (selected_players, current_salary, current_score)
                return
                
            # Search OFs
            for i in range(start_of_idx, min(limit_of, len(by_pos["OF"]))):
                p = by_pos["OF"][i]
                if any(x["name"] == p["name"] for x in selected_players):
                    continue
                new_sal = current_salary + p["salary"]
                if new_sal > 50000:
                    continue
                new_team_counts = team_counts.copy()
                new_team_counts[p["team"]] = new_team_counts.get(p["team"], 0) + 1
                if new_team_counts[p["team"]] > 5:
                    continue
                    
                search_ofs(of_idx + 1, new_sal, current_score + p["score"], selected_players + [p], new_team_counts, i + 1)
                
        search_hitters(0, sp_sal, sp1["score"] + sp2["score"], [sp1, sp2], sp_teams)
        
    return best_lineup

# Run optimizations
results = {}

print("\n--- Running Raw Optimization ---")
raw = solve_lineup(matched_pitchers, matched_hitters)
results["raw"] = raw

print("\n--- Running Yankees (5) + Pirates (3) Stack ---")
nyy_pit = solve_lineup(matched_pitchers, matched_hitters, "NYY", 5, "PIT", 3)
results["nyy_pit"] = nyy_pit

print("\n--- Running Pirates (5) + Cubs (3) Stack ---")
pit_chc = solve_lineup(matched_pitchers, matched_hitters, "PIT", 5, "CHC", 3)
results["pit_chc"] = pit_chc

print("\n--- Running Cubs (5) + Yankees (3) Stack ---")
chc_nyy = solve_lineup(matched_pitchers, matched_hitters, "CHC", 5, "NYY", 3)
results["chc_nyy"] = chc_nyy

print("\n--- Running Yankees (5) + Cubs (3) Stack ---")
nyy_chc = solve_lineup(matched_pitchers, matched_hitters, "NYY", 5, "CHC", 3)
results["nyy_chc"] = nyy_chc

# Output formatting to markdown file
report = []
report.append("# 🎮 OMEGA DFS Optimizer Results: 7-Game Slate")
report.append("Generated optimal cap-compliant GPP lineups based on OMEGA score matching.\n")

for name, res in results.items():
    title = name.upper().replace("_", " ")
    report.append(f"## 🏆 {title} Lineup")
    if res:
        players, sal, score = res
        report.append(f"**Total Score: {score:.1f} | Total Salary: ${sal:,}**\n")
        report.append("| Position | Player | Team | Salary | OMEGA Score |")
        report.append("| :--- | :--- | :--- | :--- | :--- |")
        
        # Sort players to display nicely: SP, C, 1B, 2B, 3B, SS, OF
        sps = [p for p in players if "position" not in p]
        hitters_sel = [p for p in players if p not in sps]
        
        # For display, map positions
        display_list = []
        # SP1, SP2
        display_list.append(("SP1", sps[0]))
        display_list.append(("SP2", sps[1]))
        
        for pos in ["C", "1B", "2B", "3B", "SS"]:
            p = next((x for x in hitters_sel if x["position"] == pos), None)
            if p:
                display_list.append((pos, p))
                hitters_sel.remove(p)
        # remaining are OFs
        for i, p in enumerate(hitters_sel, 1):
            display_list.append((f"OF{i}", p))
            
        for pos, p in display_list:
            report.append(f"| {pos} | **{p['name']}** | {p['team']} | ${p['salary']:,} | {p['score']:.1f} |")
    else:
        report.append("No valid combination found under cap.")
    report.append("\n" + "---" + "\n")

out_md = Path(r"c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\optimizer_lineups.md")
out_md.write_text("\n".join(report), encoding="utf-8")
print(f"\nOptimizer results written to {out_md}")
