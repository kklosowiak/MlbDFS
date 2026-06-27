import json
import csv
import random
import sys
from pathlib import Path

downloads = Path(r"C:\Users\konra\Downloads")
f155 = downloads / "omega-results(156).json"
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

def is_valid_lineup(lineup, stack1_team=None, stack1_size=0, stack2_team=None, stack2_size=0):
    sal = sum(p["salary"] for p in lineup)
    if sal > 50000:
        return False
        
    names = [p["name"] for p in lineup]
    if len(names) != len(set(names)):
        return False
        
    teams = [p["team"] for p in lineup]
    if len(set(teams)) < 3:
        return False
        
    team_counts = {}
    for t in teams:
        team_counts[t] = team_counts.get(t, 0) + 1
        if team_counts[t] > 5:
            return False
            
    if stack1_team and team_counts.get(stack1_team, 0) < stack1_size:
        return False
    if stack2_team and team_counts.get(stack2_team, 0) < stack2_size:
        return False
        
    return True

def optimize_gpp_smart(stack1_team=None, stack1_size=0, stack2_team=None, stack2_size=0, forced_sps=None):
    best_lineup = None
    best_score = 0
    
    # Try 500 iterations of smart seeding
    for _ in range(500):
        # 1. Select SPs
        if forced_sps:
            sps = forced_sps
        else:
            sps = random.sample(matched_pitchers, 2)
            
        # We need to assign players to slots:
        # Slots: C, 1B, 2B, 3B, SS, OF1, OF2, OF3
        slots = {"C": None, "1B": None, "2B": None, "3B": None, "SS": None, "OF1": None, "OF2": None, "OF3": None}
        
        # Helper to assign player to a valid empty slot
        def assign_player(player):
            p_pos = player["position"].split("/")
            # Shuffle positions to prevent bias
            random.shuffle(p_pos)
            for pos in p_pos:
                if pos in ["C", "1B", "2B", "3B", "SS"]:
                    if slots[pos] is None:
                        slots[pos] = player
                        return True
                elif pos == "OF":
                    for of_pos in ["OF1", "OF2", "OF3"]:
                        if slots[of_pos] is None:
                            slots[of_pos] = player
                            return True
            return False
            
        # Get stack hitters
        stack1_hitters = [h for h in matched_hitters if h["team"] == stack1_team]
        stack2_hitters = [h for h in matched_hitters if h["team"] == stack2_team]
        
        # Randomly sample the stack players
        s1_size_needed = stack1_size
        s2_size_needed = stack2_size
        
        # If SP belongs to stack1 or stack2, it counts towards stack sizes
        sp_teams = [p["team"] for p in sps]
        s1_size_needed -= sp_teams.count(stack1_team)
        s2_size_needed -= sp_teams.count(stack2_team)
        
        s1_size_needed = max(0, s1_size_needed)
        s2_size_needed = max(0, s2_size_needed)
        
        if len(stack1_hitters) < s1_size_needed or len(stack2_hitters) < s2_size_needed:
            continue
            
        s1_sample = random.sample(stack1_hitters, s1_size_needed)
        s2_sample = random.sample(stack2_hitters, s2_size_needed)
        
        # Try to assign them to slots
        success = True
        for p in s1_sample + s2_sample:
            if not assign_player(p):
                success = False
                break
        if not success:
            continue
            
        # Fill remaining slots with random players of correct positions
        for pos in ["C", "1B", "2B", "3B", "SS"]:
            if slots[pos] is None:
                # choose random player not already selected
                selected_names = [p["name"] for p in sps + list(slots.values()) if p is not None]
                opts = [x for x in by_pos[pos] if x["name"] not in selected_names]
                if not opts:
                    success = False
                    break
                slots[pos] = random.choice(opts)
                
        for of_pos in ["OF1", "OF2", "OF3"]:
            if slots[of_pos] is None:
                selected_names = [p["name"] for p in sps + list(slots.values()) if p is not None]
                opts = [x for x in by_pos["OF"] if x["name"] not in selected_names]
                if not opts:
                    success = False
                    break
                slots[of_pos] = random.choice(opts)
                
        if not success:
            continue
            
        # Construct lineup
        lineup = list(sps) + [slots["C"], slots["1B"], slots["2B"], slots["3B"], slots["SS"], slots["OF1"], slots["OF2"], slots["OF3"]]
        
        if not is_valid_lineup(lineup, stack1_team, stack1_size, stack2_team, stack2_size):
            continue
            
        current_sal = sum(p["salary"] for p in lineup)
        current_score = sum(p["score"] for p in lineup)
        
        # 2. Hill climb
        improved = True
        while improved:
            improved = False
            for pos_idx in range(10):
                if forced_sps and pos_idx < 2:
                    continue
                    
                old_player = lineup[pos_idx]
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
                    if is_valid_lineup(lineup, stack1_team, stack1_size, stack2_team, stack2_size):
                        new_score = sum(p["score"] for p in lineup)
                        if new_score > current_score:
                            current_score = new_score
                            improved = True
                            break
                    lineup[pos_idx] = old_player
                    
        if current_score > best_score:
            best_score = current_score
            best_lineup = list(lineup)
            
    return best_lineup

def print_lineup(title, lineup):
    print(f"\n=== {title.upper()} ===")
    if lineup:
        sal = sum(p["salary"] for p in lineup)
        score = sum(p["score"] for p in lineup)
        print(f"Total Score: {score:.1f} | Salary: ${sal:,}")
        
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
ashcraft = next((p for p in matched_pitchers if "ashcraft" in p["name"].lower()), None)

forced_sp_set = None
if rodon and whisenhunt:
    forced_sp_set = [rodon, whisenhunt]
    print(f"Forcing SPs: {rodon['name']} + {whisenhunt['name']}")

l1 = optimize_gpp_smart("NYY", 5, "TOR", 3, forced_sps=forced_sp_set)
print_lineup("Yankees (5) + Blue Jays (3) Stack (Rodon + Whisenhunt)", l1)

l2 = optimize_gpp_smart("PIT", 5, "TOR", 3, forced_sps=forced_sp_set)
print_lineup("Pirates (5) + Blue Jays (3) Stack (Rodon + Whisenhunt)", l2)

# Also let's try with Kirby + Whisenhunt if possible
if kirby and whisenhunt:
    forced_sp_set_2 = [kirby, whisenhunt]
    l3 = optimize_gpp_smart("NYY", 5, "TOR", 3, forced_sps=forced_sp_set_2)
    print_lineup("Yankees (5) + Blue Jays (3) Stack (Kirby + Whisenhunt)", l3)

    l4 = optimize_gpp_smart("PIT", 5, "TOR", 3, forced_sps=forced_sp_set_2)
    print_lineup("Pirates (5) + Blue Jays (3) Stack (Kirby + Whisenhunt)", l4)

    # Added Chicago Cubs Stack runs
    l5 = optimize_gpp_smart("CHC", 5, "TOR", 3, forced_sps=[kirby, rodon] if kirby and rodon else None)
    print_lineup("Cubs (5) + Blue Jays (3) Stack (Kirby + Rodon)", l5)

    l6 = optimize_gpp_smart("CHC", 5, "PIT", 3, forced_sps=[kirby, rodon] if kirby and rodon else None)
    print_lineup("Cubs (5) + Pirates (3) Stack (Kirby + Rodon)", l6)

    # Force Kirby + Ashcraft with 5-man TOR Stack
    if kirby and ashcraft:
        l7 = optimize_gpp_smart("TOR", 5, None, 0, forced_sps=[kirby, ashcraft])
        print_lineup("Optimal 5-man Blue Jays Stack (Kirby + Ashcraft)", l7)


