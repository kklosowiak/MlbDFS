import json
import csv
import random
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

# Separate hitters by position
by_pos = {"C": [], "1B": [], "2B": [], "3B": [], "SS": [], "OF": []}
for h in matched_hitters:
    positions = h["position"].split("/")
    for pos in positions:
        if pos in by_pos:
            by_pos[pos].append(h)

def get_lineup_salary_and_score(lineup):
    sal = sum(p["salary"] for p in lineup)
    score = sum(p["score"] for p in lineup)
    return sal, score

def is_valid(lineup, stack1_team=None, stack1_size=0, stack2_team=None, stack2_size=0):
    sal = sum(p["salary"] for p in lineup)
    if sal > 50000:
        return False
        
    # Check duplicate names
    names = [p["name"] for p in lineup]
    if len(names) != len(set(names)):
        return False
        
    # Check 3+ teams represented
    teams = [p["team"] for p in lineup]
    if len(set(teams)) < 3:
        return False
        
    # Team count limit of 5 on DK
    team_counts = {}
    for t in teams:
        team_counts[t] = team_counts.get(t, 0) + 1
        if team_counts[t] > 5:
            return False
            
    # Check stack constraints
    if stack1_team and team_counts.get(stack1_team, 0) < stack1_size:
        return False
    if stack2_team and team_counts.get(stack2_team, 0) < stack2_size:
        return False
        
    return True

def optimize_gpp(stack1_team=None, stack1_size=0, stack2_team=None, stack2_size=0, forced_sps=None):
    best_lineup = None
    best_score = 0
    
    # Run hill climber multiple times with random restarts
    for restart in range(150):
        # 1. Generate a random valid starting lineup
        # Select SPs
        if forced_sps:
            sps = forced_sps
        else:
            sps = random.sample(matched_pitchers, 2)
            
        lineup = list(sps)
        # Select hitters
        lineup.append(random.choice(by_pos["C"]))
        lineup.append(random.choice(by_pos["1B"]))
        lineup.append(random.choice(by_pos["2B"]))
        lineup.append(random.choice(by_pos["3B"]))
        lineup.append(random.choice(by_pos["SS"]))
        
        ofs = random.sample(by_pos["OF"], 3)
        lineup.extend(ofs)
        
        # Make valid by random swaps if not valid
        for _ in range(50):
            if is_valid(lineup, stack1_team, stack1_size, stack2_team, stack2_size):
                break
            # Swap a random position
            pos_idx = random.randint(2, 9)
            if pos_idx == 2: lineup[2] = random.choice(by_pos["C"])
            elif pos_idx == 3: lineup[3] = random.choice(by_pos["1B"])
            elif pos_idx == 4: lineup[4] = random.choice(by_pos["2B"])
            elif pos_idx == 5: lineup[5] = random.choice(by_pos["3B"])
            elif pos_idx == 6: lineup[6] = random.choice(by_pos["SS"])
            else:
                of_idx = pos_idx - 7
                lineup[7 + of_idx] = random.choice(by_pos["OF"])
                
        if not is_valid(lineup, stack1_team, stack1_size, stack2_team, stack2_size):
            continue
            
        _, current_score = get_lineup_salary_and_score(lineup)
        
        # 2. Hill climb
        improved = True
        while improved:
            improved = False
            # Try swapping players at each position
            for pos_idx in range(10):
                # If SP is forced, skip swapping SPs
                if forced_sps and pos_idx < 2:
                    continue
                    
                old_player = lineup[pos_idx]
                
                # Get options for this position
                if pos_idx < 2:
                    options = matched_pitchers
                elif pos_idx == 2: options = by_pos["C"]
                elif pos_idx == 3: options = by_pos["1B"]
                elif pos_idx == 4: options = by_pos["2B"]
                elif pos_idx == 5: options = by_pos["3B"]
                elif pos_idx == 6: options = by_pos["SS"]
                else: options = by_pos["OF"]
                
                for new_player in options:
                    if new_player["name"] == old_player["name"]:
                        continue
                    lineup[pos_idx] = new_player
                    if is_valid(lineup, stack1_team, stack1_size, stack2_team, stack2_size):
                        _, new_score = get_lineup_salary_and_score(lineup)
                        if new_score > current_score:
                            current_score = new_score
                            improved = True
                            break
                    # revert
                    lineup[pos_idx] = old_player
                    
        if current_score > best_score:
            best_score = current_score
            best_lineup = list(lineup)
            
    return best_lineup

def print_lineup(title, lineup):
    print(f"\n=== {title.upper()} ===")
    if lineup:
        sal, score = get_lineup_salary_and_score(lineup)
        print(f"Total Score: {score:.1f} | Salary: ${sal:,}")
        
        # Sort display: SP, C, 1B, 2B, 3B, SS, OF
        sps = lineup[:2]
        c = lineup[2]
        b1 = lineup[3]
        b2 = lineup[4]
        b3 = lineup[5]
        ss = lineup[6]
        ofs = lineup[7:]
        
        print(f"- SP1: {sps[0]['name']} ({sps[0]['team']}) - ${sps[0]['salary']} (Score: {sps[0]['score']:.1f})")
        print(f"- SP2: {sps[1]['name']} ({sps[1]['team']}) - ${sps[1]['salary']} (Score: {sps[1]['score']:.1f})")
        print(f"- C:   {c['name']} ({c['team']}) - ${c['salary']} (Score: {c['score']:.1f})")
        print(f"- 1B:  {b1['name']} ({b1['team']}) - ${b1['salary']} (Score: {b1['score']:.1f})")
        print(f"- 2B:  {b2['name']} ({b2['team']}) - ${b2['salary']} (Score: {b2['score']:.1f})")
        print(f"- 3B:  {b3['name']} ({b3['team']}) - ${b3['salary']} (Score: {b3['score']:.1f})")
        print(f"- SS:  {ss['name']} ({ss['team']}) - ${ss['salary']} (Score: {ss['score']:.1f})")
        for i, of in enumerate(ofs, 1):
            print(f"- OF{i}: {of['name']} ({of['team']}) - ${of['salary']} (Score: {of['score']:.1f})")
    else:
        print("No valid lineup found.")

# Let's run optimizations for GPP options
# Get top pitchers to force
rodon = next((p for p in matched_pitchers if "rodón" in p["name"].lower() or "rodon" in p["name"].lower()), None)
whisenhunt = next((p for p in matched_pitchers if "whisenhunt" in p["name"].lower()), None)
kirby = next((p for p in matched_pitchers if "kirby" in p["name"].lower()), None)

forced_sp_set = None
if rodon and whisenhunt:
    forced_sp_set = [rodon, whisenhunt]
    print(f"Forcing SPs: {rodon['name']} + {whisenhunt['name']}")

l1 = optimize_gpp("NYY", 5, "TOR", 3, forced_sps=forced_sp_set)
print_lineup("Yankees (5) + Blue Jays (3) Stack (Rodon + Whisenhunt)", l1)

l2 = optimize_gpp("PIT", 5, "TOR", 3, forced_sps=forced_sp_set)
print_lineup("Pirates (5) + Blue Jays (3) Stack (Rodon + Whisenhunt)", l2)

# Also let's try with Kirby + Whisenhunt if possible
if kirby and whisenhunt:
    forced_sp_set_2 = [kirby, whisenhunt]
    l3 = optimize_gpp("NYY", 5, "TOR", 3, forced_sps=forced_sp_set_2)
    print_lineup("Yankees (5) + Blue Jays (3) Stack (Kirby + Whisenhunt)", l3)
