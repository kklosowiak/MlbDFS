import os
import sys
import csv
import json
import argparse
import glob
import pulp

# Force stdout to UTF-8/ASCII friendly formatting to prevent cp1252 crash
sys.stdout.reconfigure(encoding='utf-8')

# Team Abbreviation Map from DK -> OMEGA
TEAM_MAP = {
    'MIL': 'Milwaukee Brewers',
    'LAD': 'Los Angeles Dodgers',
    'CIN': 'Cincinnati Reds',
    'ATL': 'Atlanta Braves',
    'TOR': 'Toronto Blue Jays',
    'HOU': 'Houston Astros',
    'MIN': 'Minnesota Twins',
    'SD': 'San Diego Padres',
    'NYM': 'New York Mets',
    'CHC': 'Chicago Cubs',
    'STL': 'St. Louis Cardinals',
    'SF': 'San Francisco Giants',
    'SFG': 'San Francisco Giants',
    'ATH': 'Athletics',
    'OAK': 'Athletics',
    'MIA': 'Miami Marlins',
    'PHI': 'Philadelphia Phillies',
    'WSH': 'Washington Nationals',
    'PIT': 'Pittsburgh Pirates',
    'TB': 'Tampa Bay Rays',
    'TBR': 'Tampa Bay Rays',
    'BOS': 'Boston Red Sox',
    'BAL': 'Baltimore Orioles',
    'NYY': 'New York Yankees',
    'CLE': 'Cleveland Guardians',
    'DET': 'Detroit Tigers',
    'CWS': 'Chicago White Sox',
    'CHW': 'Chicago White Sox',
    'KC': 'Kansas City Royals',
    'KCR': 'Kansas City Royals',
    'TEX': 'Texas Rangers',
    'SEA': 'Seattle Mariners',
    'ARI': 'Arizona Diamondbacks',
    'COL': 'Colorado Rockies',
    'LAA': 'Los Angeles Angels'
}

def clean_name(name):
    if not name:
        return ""
    name = name.lower().strip()
    parts = name.split()
    # Remove suffixes
    parts = [p for p in parts if p not in ['jr', 'sr', 'ii', 'iii', 'iv', 'v']]
    name = "".join(parts)
    # Strip characters and map accents
    replacements = {
        "ñ": "n", "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
        ".": "", "'": "", "-": "", " ": "", ",": ""
    }
    for char, repl in replacements.items():
        name = name.replace(char, repl)
    return name

def find_latest_file(directory, pattern):
    files = glob.glob(os.path.join(directory, pattern))
    if not files:
        return None
    files.sort(key=os.path.getmtime, reverse=True)
    return files[0]

def load_salaries(file_path):
    players = []
    with open(file_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            players.append(row)
    return players

def load_projections(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)

def run_optimization(salaries_path, results_path, args):
    from config import config
    allowed_teams = config.get_slate_filter()
    if allowed_teams is not None:
        print(f"Applying slate filter: {len(allowed_teams)} teams allowed.")
        
    print(f"Loading DK Salaries: {os.path.basename(salaries_path)}")
    dk_players = load_salaries(salaries_path)
    
    print(f"Loading Model Projections: {os.path.basename(results_path)}")
    proj_data = load_projections(results_path)
    
    # Map results by normalized name
    pitcher_scores = {}
    for p in proj_data.get('pitchers', []):
        pitcher_scores[clean_name(p['pitcher'])] = p
        
    hitter_scores = {}
    for h in proj_data.get('hitters', []):
        hitter_scores[clean_name(h['name'])] = h

    # Merge players
    hitters = []
    pitchers = []
    
    unmatched_count = 0
    for dk in dk_players:
        team_abbr = dk['TeamAbbrev']
        full_team = TEAM_MAP.get(team_abbr, team_abbr)
        if allowed_teams is not None and full_team not in allowed_teams:
            continue
            
        name = dk['Name']
        cn = clean_name(name)
        sal = int(dk['Salary'])
        pos = dk['Position']
        roster_pos = dk['Roster Position']
        
        is_p = (roster_pos == 'P' or 'SP' in pos or 'RP' in pos)
        
        if is_p:
            proj = pitcher_scores.get(cn, {})
            # Try fallback search
            if not proj:
                for k, v in pitcher_scores.items():
                    if cn in k or k in cn:
                        proj = v
                        break
            
            score = 0.0
            if proj:
                score = proj.get('blended_rating') or proj.get('rating') or 0.0
            else:
                unmatched_count += 1
                
            pitchers.append({
                'name': name,
                'salary': sal,
                'pos_list': ['P'],
                'team': team_abbr,
                'score': score,
                'raw_proj': proj
            })
        else:
            proj = hitter_scores.get(cn, {})
            # Try fallback search
            if not proj:
                for k, v in hitter_scores.items():
                    if cn in k or k in cn:
                        proj = v
                        break
            
            score = 0.0
            if proj:
                if args.metric == 'stack_adjusted' and 'stack_adjusted_score' in proj:
                    score = proj['stack_adjusted_score']
                else:
                    score = proj.get('player_score') or proj.get('score') or 0.0
            else:
                unmatched_count += 1
                
            hitters.append({
                'name': name,
                'salary': sal,
                'pos_list': pos.split('/'),
                'team': team_abbr,
                'score': score,
                'raw_proj': proj
            })

    print(f"Merged {len(pitchers)} Pitchers and {len(hitters)} Hitters.")
    if unmatched_count > 0:
        print(f"[NOTE]: {unmatched_count} players in DK salaries did not match model projections (assigned 0.0).")

    # Define standard LP problem
    prob = pulp.LpProblem("DK_Classic_Optimizer", pulp.LpMaximize)
    
    # Decision variables
    h_vars = {i: pulp.LpVariable(f"h_{i}", cat='Binary') for i in range(len(hitters))}
    p_vars = {j: pulp.LpVariable(f"p_{j}", cat='Binary') for j in range(len(pitchers))}
    
    # 1. Salary Constraint: Total Salary <= 50,000
    prob += (
        pulp.lpSum(h_vars[i] * hitters[i]['salary'] for i in range(len(hitters))) +
        pulp.lpSum(p_vars[j] * pitchers[j]['salary'] for j in range(len(pitchers)))
        <= 50000
    )
    
    # 2. Roster count requirements: 2 Pitchers, 8 Hitters
    prob += pulp.lpSum(p_vars[j] for j in range(len(pitchers))) == 2
    prob += pulp.lpSum(h_vars[i] for i in range(len(hitters))) == 8
    
    # 3. Position slots assignment constraints (C, 1B, 2B, 3B, SS, OF1, OF2, OF3)
    slots = ['C', '1B', '2B', '3B', 'SS', 'OF1', 'OF2', 'OF3']
    assign = {}
    for i in range(len(hitters)):
        for s in slots:
            assign[(i, s)] = pulp.LpVariable(f"assign_{i}_{s}", cat='Binary')
            
    for i in range(len(hitters)):
        prob += pulp.lpSum(assign[(i, s)] for s in slots) == h_vars[i]
        for s in slots:
            pos_req = 'OF' if s.startswith('OF') else s
            if pos_req not in hitters[i]['pos_list']:
                prob += assign[(i, s)] == 0
                
    prob += pulp.lpSum(assign[(i, 'C')] for i in range(len(hitters))) == 1
    prob += pulp.lpSum(assign[(i, '1B')] for i in range(len(hitters))) == 1
    prob += pulp.lpSum(assign[(i, '2B')] for i in range(len(hitters))) == 1
    prob += pulp.lpSum(assign[(i, '3B')] for i in range(len(hitters))) == 1
    prob += pulp.lpSum(assign[(i, 'SS')] for i in range(len(hitters))) == 1
    prob += pulp.lpSum(assign[(i, 'OF1')] for i in range(len(hitters))) == 1
    prob += pulp.lpSum(assign[(i, 'OF2')] for i in range(len(hitters))) == 1
    prob += pulp.lpSum(assign[(i, 'OF3')] for i in range(len(hitters))) == 1

    # 4. Roster Team Diversity: Hitters + Pitchers must span at least 3 teams
    all_teams = list(set([p['team'] for p in hitters] + [p['team'] for p in pitchers]))
    team_used = {t: pulp.LpVariable(f"team_used_{t}", cat='Binary') for t in all_teams}
    for t in all_teams:
        prob += (
            pulp.lpSum(h_vars[i] for i in range(len(hitters)) if hitters[i]['team'] == t) +
            pulp.lpSum(p_vars[j] for j in range(len(pitchers)) if pitchers[j]['team'] == t)
            <= 10 * team_used[t]
        )
    prob += pulp.lpSum(team_used[t] for t in all_teams) >= 3

    # 5. Stacking Rules: Max 5 hitters from any team (DK rule limit)
    for t in all_teams:
        prob += pulp.lpSum(h_vars[i] for i in range(len(hitters)) if hitters[i]['team'] == t) <= 5

    # 6. Apply Custom Stacks
    if args.stack:
        parts = args.stack.split(':')
        stack_team = parts[0].upper()
        stack_size = int(parts[1])
        prob += pulp.lpSum(h_vars[i] for i in range(len(hitters)) if hitters[i]['team'] == stack_team) == stack_size
        print(f"Applying Stack Lock: {stack_size} hitters from {stack_team}")
        
    if args.secondary_stack:
        parts = args.secondary_stack.split(':')
        sec_team = parts[0].upper()
        sec_size = int(parts[1])
        prob += pulp.lpSum(h_vars[i] for i in range(len(hitters)) if hitters[i]['team'] == sec_team) == sec_size
        print(f"Applying Secondary Stack Lock: {sec_size} hitters from {sec_team}")

    # 7. Apply Locks
    if args.lock:
        for lock_name in args.lock:
            l_cn = clean_name(lock_name)
            p_found = False
            for j, p in enumerate(pitchers):
                if clean_name(p['name']) == l_cn or l_cn in clean_name(p['name']):
                    prob += p_vars[j] == 1
                    p_found = True
                    print(f"Locking Pitcher: {p['name']} (${p['salary']})")
                    break
            if not p_found:
                h_found = False
                for i, h in enumerate(hitters):
                    if clean_name(h['name']) == l_cn or l_cn in clean_name(h['name']):
                        prob += h_vars[i] == 1
                        h_found = True
                        print(f"Locking Hitter: {h['name']} (${h['salary']})")
                        break
                if not h_found:
                    print(f"[WARNING]: Lock player '{lock_name}' not found!")

    # 8. Apply Exclusions
    if args.exclude:
        for excl_name in args.exclude:
            e_cn = clean_name(excl_name)
            for j, p in enumerate(pitchers):
                if clean_name(p['name']) == e_cn or e_cn in clean_name(p['name']):
                    prob += p_vars[j] == 0
                    print(f"Excluding Pitcher: {p['name']}")
            for i, h in enumerate(hitters):
                if clean_name(h['name']) == e_cn or e_cn in clean_name(h['name']):
                    prob += h_vars[i] == 0
                    print(f"Excluding Hitter: {h['name']}")

    # Objective function setup
    prob.setObjective(
        pulp.lpSum(h_vars[i] * hitters[i]['score'] for i in range(len(hitters))) +
        pulp.lpSum(p_vars[j] * pitchers[j]['score'] for j in range(len(pitchers)))
    )

    # Loop to generate num_lineups
    generated_lineups = 0
    while generated_lineups < args.num_lineups:
        status = prob.solve(pulp.PULP_CBC_CMD(msg=False))
        
        if pulp.LpStatus[status] != 'Optimal':
            if generated_lineups == 0:
                print("ERROR: Solver could not find an optimal solution under these constraints.")
            else:
                print(f"\nGenerated {generated_lineups} lineups. No further unique combinations possible.")
            break
            
        # Get selected players
        sel_pitchers = [pitchers[j] for j in range(len(pitchers)) if p_vars[j].varValue > 0.5]
        
        roster_hitters = {}
        for s in slots:
            for i in range(len(hitters)):
                if assign[(i, s)].varValue > 0.5:
                    roster_hitters[s] = hitters[i]
                    
        total_salary = sum(p['salary'] for p in sel_pitchers) + sum(h['salary'] for h in roster_hitters.values())
        total_score = sum(p['score'] for p in sel_pitchers) + sum(h['score'] for h in roster_hitters.values())
        
        generated_lineups += 1
        print(f"\n{'='*72}")
        print(f"LINEUP #{generated_lineups} | Score: {total_score:.2f} | Salary: ${total_salary:,} / $50,000")
        print(f"{'='*72}")
        
        # Display nicely in ASCII
        print(f"SP1:  {sel_pitchers[0]['name']:<24} {sel_pitchers[0]['team']:<6} ${sel_pitchers[0]['salary']:<6,} Score: {sel_pitchers[0]['score']:.1f}")
        print(f"SP2:  {sel_pitchers[1]['name']:<24} {sel_pitchers[1]['team']:<6} ${sel_pitchers[1]['salary']:<6,} Score: {sel_pitchers[1]['score']:.1f}")
        for s in ['C', '1B', '2B', '3B', 'SS', 'OF1', 'OF2', 'OF3']:
            p = roster_hitters[s]
            print(f"{s:<5} {p['name']:<24} {p['team']:<6} ${p['salary']:<6,} Score: {p['score']:.1f}")
            
        # Display team stacks
        stacks = {}
        for p in sel_pitchers + list(roster_hitters.values()):
            stacks[p['team']] = stacks.get(p['team'], 0) + 1
        stack_str = ", ".join([f"{t}({c})" for t, c in sorted(stacks.items(), key=lambda x: -x[1]) if c > 1])
        print(f"Stacks: {stack_str}")
        
        # Add constraint to prevent this exact combination in subsequent loops
        # overlap limit (max players sharing this lineup in subsequent ones)
        overlap_limit = 8 # forces at least 2 player difference
        prob += (
            pulp.lpSum(h_vars[i] for i in range(len(hitters)) if h_vars[i].varValue > 0.5) +
            pulp.lpSum(p_vars[j] for j in range(len(pitchers)) if p_vars[j].varValue > 0.5)
            <= overlap_limit
        )

def main():
    parser = argparse.ArgumentParser(description="MLB DFS DraftKings Lineup Optimizer")
    parser.add_argument("--salaries", help="Path to DraftKings Salaries CSV file")
    parser.add_argument("--results", help="Path to OMEGA Projections JSON results file")
    parser.add_argument("--stack", help="Lock stack: e.g. ARI:5")
    parser.add_argument("--secondary-stack", help="Lock secondary stack: e.g. TOR:3")
    parser.add_argument("--lock", nargs="+", help="Space-separated list of player names to lock in")
    parser.add_argument("--exclude", nargs="+", help="Space-separated list of player names to exclude")
    parser.add_argument("--metric", choices=['stack_adjusted', 'raw'], default='stack_adjusted', 
                        help="Metric to optimize: stack_adjusted (default) or raw")
    parser.add_argument("--num-lineups", type=int, default=1, help="Number of unique lineups to output")
    
    args = parser.parse_args()
    
    downloads_dir = r"C:\Users\konra\Downloads"
    
    # 1. Resolve salaries path
    salaries_path = args.salaries
    if not salaries_path:
        salaries_path = find_latest_file(downloads_dir, "DKSalaries*.csv")
        if not salaries_path:
            print("ERROR: Could not find any DKSalaries*.csv in Downloads directory. Please specify with --salaries.")
            sys.exit(1)
            
    # 2. Resolve results path
    results_path = args.results
    if not results_path:
        # Check Downloads
        results_path = find_latest_file(downloads_dir, "omega-results*.json")
        if not results_path:
            # Check reports/latest_results.json
            fallback = os.path.join(os.getcwd(), "reports", "latest_results.json")
            if os.path.exists(fallback):
                results_path = fallback
            else:
                print("ERROR: Could not find any omega-results*.json in Downloads or reports/latest_results.json. Specify with --results.")
                sys.exit(1)
                
    run_optimization(salaries_path, results_path, args)

if __name__ == "__main__":
    main()
