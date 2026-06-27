"""Script to run final optimizations and evaluate user's lineups using omega-results(158).json."""
import json
import csv
import itertools
from pathlib import Path
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

print(f"Loaded {len(dk_players)} players from DK Salaries.")

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
        # search partial
        for k, v in dk_players.items():
            if norm_p_name in k and v["team"] == dk_team:
                dk_p = v
                break
    if not dk_p:
        # Fallback to team search for TBD
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

print(f"Matched {len(matched_pitchers)} pitchers and {len(matched_hitters)} hitters.")

# Help find specific player scores
def get_player_info(name_str):
    norm = normalize_player_name(name_str)
    for h in matched_hitters:
        if norm in normalize_player_name(h["name"]) or normalize_player_name(h["name"]) in norm:
            return h
    for p in matched_pitchers:
        if norm in normalize_player_name(p["name"]) or normalize_player_name(p["name"]) in norm:
            return p
    return None

# Verify specific players requested by user
print("\n--- Individual Player Lookup ---")
players_to_check = [
    "George Kirby", "Braxton Ashcraft", "Alejandro Kirk", "Vladimir Guerrero", 
    "Ernie Clement", "Kazuma Okamoto", "Jp Crawford", "Jackson Chourio", 
    "Seiya Suzuki", "George Springer", "Connor Joe", "Brandon Lowe"
]
for p_name in players_to_check:
    info = get_player_info(p_name)
    if info:
        print(f"{info['name']} ({info['team']}) - {info['position'] if 'position' in info else 'SP'}: Salary = ${info['salary']:,}, OMEGA Score = {info['score']:.1f}")
    else:
        print(f"FAILED TO FIND: {p_name}")

def run_optimization(stack1_team=None, stack1_size=0, stack2_team=None, stack2_size=0, forced_sps=None, forced_hitters=None, max_salary=50000):
    expanded_hitters = []
    for h in matched_hitters:
        positions = h["position"].split("/")
        for pos in positions:
            expanded_hitters.append({
                "name": h["name"],
                "salary": h["salary"],
                "position": pos,
                "team": h["team"],
                "score": h["score"]
            })
            
    by_pos = {"SP": [], "C": [], "1B": [], "2B": [], "3B": [], "SS": [], "OF": []}
    for p in matched_pitchers:
        by_pos["SP"].append(p)
        
    for h in expanded_hitters:
        if h["position"] in by_pos:
            by_pos[h["position"]].append(h)
            
    for k in by_pos:
        by_pos[k].sort(key=lambda x: -x["score"])
        
    best_lineup = None
    best_score = 0
    
    if forced_sps:
        sp_pairs = [forced_sps]
    else:
        sp_pairs = list(itertools.combinations(by_pos["SP"], 2))
        sp_pairs.sort(key=lambda x: -(x[0]["score"] + x[1]["score"]))
        
    # Minimum salary by position to prune based on budget
    min_sal = {}
    for pos in ["C", "1B", "2B", "3B", "SS", "OF"]:
        min_sal[pos] = min(x["salary"] for x in by_pos[pos]) if by_pos[pos] else 0
        
    # Search top 4 SP pairs
    for sp1, sp2 in sp_pairs[:4]:
        sp_sal = sp1["salary"] + sp2["salary"]
        if sp_sal > max_salary - 15000: # must leave at least $15k for hitters
            continue
            
        sp_teams = {}
        sp_teams[sp1["team"]] = sp_teams.get(sp1["team"], 0) + 1
        sp_teams[sp2["team"]] = sp_teams.get(sp2["team"], 0) + 1
        
        pos_list = ["C", "1B", "2B", "3B", "SS"]
        limit_pos = 5
        limit_of = 8
        
        # Build dynamic option pools for each position to include stack players and forced players
        opts_by_pos = {}
        stack_teams = {stack1_team, stack2_team}
        
        for pos in pos_list:
            opts = [p for p in by_pos[pos][:limit_pos]]
            for p in by_pos[pos]:
                if p["team"] in stack_teams and p not in opts:
                    opts.append(p)
                if forced_hitters:
                    for fh in forced_hitters:
                        fh_norm = normalize_player_name(fh)
                        if fh_norm in normalize_player_name(p["name"]) and p not in opts:
                            opts.append(p)
            opts_by_pos[pos] = opts
            
        # For OF
        of_opts = [p for p in by_pos["OF"][:limit_of]]
        for p in by_pos["OF"]:
            if p["team"] in stack_teams and p not in of_opts:
                of_opts.append(p)
            if forced_hitters:
                for fh in forced_hitters:
                    fh_norm = normalize_player_name(fh)
                    if fh_norm in normalize_player_name(p["name"]) and p not in of_opts:
                        of_opts.append(p)
        opts_by_pos["OF"] = of_opts
        
        def search_hitters(idx, current_salary, current_score, selected_players, team_counts):
            nonlocal best_score, best_lineup
            
            # 1. Score Pruning
            max_rem = 0
            if idx < len(pos_list):
                for p_idx in range(idx, len(pos_list)):
                    pos = pos_list[p_idx]
                    if opts_by_pos[pos]:
                        max_rem += opts_by_pos[pos][0]["score"]
                max_rem += sum(x["score"] for x in opts_by_pos["OF"][:3])
            else:
                rem_ofs = 3 - (len(selected_players) - 7)
                if rem_ofs > 0:
                    max_rem += sum(x["score"] for x in opts_by_pos["OF"][:rem_ofs])
            if current_score + max_rem <= best_score:
                return
                
            # 2. Salary Pruning
            min_rem_sal = 0
            if idx < len(pos_list):
                for p_idx in range(idx, len(pos_list)):
                    min_rem_sal += min_sal[pos_list[p_idx]]
                min_rem_sal += sum(sorted([x["salary"] for x in opts_by_pos["OF"]])[:3])
            else:
                rem_ofs = 3 - (len(selected_players) - 7)
                if rem_ofs > 0:
                    min_rem_sal += sum(sorted([x["salary"] for x in opts_by_pos["OF"]])[:rem_ofs])
            if current_salary + min_rem_sal > max_salary:
                return
                
            if idx == len(pos_list):
                search_ofs(0, current_salary, current_score, selected_players, team_counts, 0)
                return
                
            pos = pos_list[idx]
            for p in opts_by_pos[pos]:
                if any(x["name"] == p["name"] for x in selected_players):
                    continue
                new_sal = current_salary + p["salary"]
                if new_sal > max_salary:
                    continue
                    
                new_team_counts = team_counts.copy()
                new_team_counts[p["team"]] = new_team_counts.get(p["team"], 0) + 1
                if new_team_counts[p["team"]] > 5:
                    continue
                    
                search_hitters(idx + 1, new_sal, current_score + p["score"], selected_players + [p], new_team_counts)
                
        def search_ofs(of_idx, current_salary, current_score, selected_players, team_counts, start_of_idx):
            nonlocal best_score, best_lineup
            
            # Score Pruning
            rem_ofs = 3 - of_idx
            if rem_ofs > 0:
                max_rem = sum(x["score"] for x in opts_by_pos["OF"][start_of_idx : start_of_idx + rem_ofs])
                if current_score + max_rem <= best_score:
                    return
            # Salary Pruning
            if rem_ofs > 0:
                min_rem_sal = sum(sorted([x["salary"] for x in opts_by_pos["OF"][start_of_idx:]])[:rem_ofs])
                if current_salary + min_rem_sal > max_salary:
                    return
                    
            if of_idx == 3:
                if stack1_team:
                    if team_counts.get(stack1_team, 0) < stack1_size:
                        return
                if stack2_team:
                    if team_counts.get(stack2_team, 0) < stack2_size:
                        return
                if forced_hitters:
                    for fh in forced_hitters:
                        fh_norm = normalize_player_name(fh)
                        if not any(fh_norm in normalize_player_name(x["name"]) for x in selected_players):
                            return
                all_teams = set(x["team"] for x in selected_players)
                if len(all_teams) < 3:
                    return
                if current_score > best_score:
                    best_score = current_score
                    best_lineup = (selected_players, current_salary, current_score)
                return
                
            for i in range(start_of_idx, len(opts_by_pos["OF"])):
                p = opts_by_pos["OF"][i]
                if any(x["name"] == p["name"] for x in selected_players):
                    continue
                new_sal = current_salary + p["salary"]
                if new_sal > max_salary:
                    continue
                new_team_counts = team_counts.copy()
                new_team_counts[p["team"]] = new_team_counts.get(p["team"], 0) + 1
                if new_team_counts[p["team"]] > 5:
                    continue
                search_ofs(of_idx + 1, new_sal, current_score + p["score"], selected_players + [p], new_team_counts, i + 1)
                
        search_hitters(0, sp_sal, sp1["score"] + sp2["score"], [sp1, sp2], sp_teams)
        
    return best_lineup

def format_lineup_result(title, res):
    lines = []
    lines.append(f"### {title}")
    if res:
        players, sal, score = res
        lines.append(f"**Total Score: {score:.1f} | Salary: ${sal:,}**\n")
        lines.append("| Slot | Player | Team | Salary | OMEGA Score |")
        lines.append("| :--- | :--- | :--- | :--- | :--- |")
        
        sps = [p for p in players if "position" not in p]
        hitters_sel = [p for p in players if p not in sps]
        
        display_list = [("SP1", sps[0]), ("SP2", sps[1])]
        for pos in ["C", "1B", "2B", "3B", "SS"]:
            p = next((x for x in hitters_sel if x["position"] == pos), None)
            if p:
                display_list.append((pos, p))
                hitters_sel.remove(p)
        for i, p in enumerate(hitters_sel, 1):
            display_list.append((f"OF{i}", p))
            
        for pos, p in display_list:
            lines.append(f"| {pos} | **{p['name']}** | {p['team']} | ${p['salary']:,} | {p['score']:.1f} |")
    else:
        lines.append("No valid lineup found under cap.")
    lines.append("\n")
    return "\n".join(lines)

# Run different optimization tests
report_out = []
report_out.append("# 🚀 Final OMEGA Optimization Run (Snapshot 158)")
report_out.append(f"Evaluating optimal stack alignments and player integrations for lock.\n")

kirby_p = get_player_info("George Kirby")
ashcraft_p = get_player_info("Braxton Ashcraft")
if kirby_p and ashcraft_p:
    report_out.append("## 👤 Evaluating User's Lineup Options")
    
    # User Lineup: Kirby + Ashcraft, 5-man Blue Jays Stack
    user_lineup = run_optimization(stack1_team="TOR", stack1_size=5, forced_sps=(kirby_p, ashcraft_p))
    report_out.append(format_lineup_result("User's Base Lineup (5-man Blue Jays Stack, Kirby + Ashcraft)", user_lineup))
    
    # Connor Joe Integration: Force Kirby + Ashcraft, force Connor Joe ($2,000, 74.3 score), force 5-man Blue Jays Stack
    user_joe_lineup = run_optimization(stack1_team="TOR", stack1_size=5, forced_sps=(kirby_p, ashcraft_p), forced_hitters=["Connor Joe"])
    report_out.append(format_lineup_result("User's Lineup with Connor Joe forced (5-man Blue Jays Stack, Kirby + Ashcraft)", user_joe_lineup))

# Run general optimizations
report_out.append("## 🏆 Mathematically Optimal Lineups by Stack Type")

# Raw Optimal (no stack constraints)
report_out.append(format_lineup_result("Raw Optimal (No Stack Constraints)", run_optimization()))

# Yankees (5) + Pirates (3) Stack
report_out.append(format_lineup_result("Yankees (5) + Pirates (3) Stack", run_optimization("NYY", 5, "PIT", 3)))

# Pirates (5) + Cubs (3) Stack
report_out.append(format_lineup_result("Pirates (5) + Cubs (3) Stack", run_optimization("PIT", 5, "CHC", 3)))

# Cubs (5) + Yankees (3) Stack
report_out.append(format_lineup_result("Cubs (5) + Yankees (3) Stack", run_optimization("CHC", 5, "NYY", 3)))

# SF Giants (5) + Pirates (3) Stack
report_out.append(format_lineup_result("SF Giants (5) + Pirates (3) Stack", run_optimization("SF", 5, "PIT", 3)))

# Toronto Blue Jays (5) + Seattle Mariners (3) Stack
report_out.append(format_lineup_result("Blue Jays (5) + Mariners (3) Stack", run_optimization("TOR", 5, "SEA", 3)))

out_path = Path(r"c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\optimizer_final_results.md")
out_path.write_text("\n".join(report_out), encoding="utf-8")
print(f"\nFinal optimizer results written to {out_path}")
