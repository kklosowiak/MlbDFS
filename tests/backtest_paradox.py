import os
import json
import re
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure project root is in the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
archive_dir = os.path.join(base_dir, "reports", "archive")

def load_slates():
    slates = []
    files = os.listdir(archive_dir)
    results_files = sorted([f for f in files if f.startswith("results_") and f.endswith(".json")])
    for rf in results_files:
        date_match = re.search(r'results_(\d{4}-\d{2}-\d{2})', rf)
        if not date_match:
            continue
        date_str = date_match.group(1)
        actuals_path = os.path.join(archive_dir, f"actuals_cache_{date_str}.json")
        if os.path.exists(actuals_path):
            try:
                with open(os.path.join(archive_dir, rf), "r", encoding="utf-8") as f:
                    proj = json.load(f)
                with open(actuals_path, "r", encoding="utf-8") as f:
                    act = json.load(f)
                slates.append({
                    "date": date_str,
                    "projections": proj,
                    "actuals": act
                })
            except Exception as e:
                print(f"Error loading {date_str}: {e}")
    return slates

def get_momentum_signals(t):
    # Counts active momentum signals
    sig = 0
    if t.get("is_burst"): sig += 1
    if t.get("is_hot_run_msmi") or t.get("is_hot_run_msmi_support"): sig += 1
    return sig

def resolve_proposed(t1, t2):
    #Proposed hierarchy:
    # 1. Higher ITT wins
    # 2. If ITT within 0.3, higher momentum wins
    # 3. If tied, higher bullpen fatigue wins
    # 4. Higher raw xwOBA wins
    itt1 = float(t1.get("implied_total", 4.5) or 4.5)
    itt2 = float(t2.get("implied_total", 4.5) or 4.5)
    
    if abs(itt1 - itt2) > 0.301: # 0.3 runs threshold
        return t1 if itt1 > itt2 else t2
        
    m1 = get_momentum_signals(t1)
    m2 = get_momentum_signals(t2)
    if m1 != m2:
        return t1 if m1 > m2 else t2
        
    f1 = float(t1.get("bullpen_fatigue", 0) or 0)
    f2 = float(t2.get("bullpen_fatigue", 0) or 0)
    if f1 != f2:
        return t1 if f1 > f2 else t2
        
    xw1 = float(t1.get("team_xwoba", 0) or 0)
    xw2 = float(t2.get("team_xwoba", 0) or 0)
    return t1 if xw1 > xw2 else t2

def main():
    slates = load_slates()
    print(f"Loaded {len(slates)} slates with both projections and actuals.")
    
    paradox_games = []
    
    for slate in slates:
        date = slate["date"]
        proj = slate["projections"]
        act = slate["actuals"]
        
        pitchers = proj.get("pitchers", [])
        teams = proj.get("teams", [])
        
        # Find games with at least one paradox pitcher
        for p in pitchers:
            if p.get("is_paradox"):
                # Game is between p["team"] and p["opponent"]
                t_opp = p["opponent"] # Stacks attacking this pitcher
                t_self = p["team"]    # Stacks of this pitcher's team, attacking the other pitcher
                
                # Find team objects
                team_opp = next((t for t in teams if t["team"] == t_opp), None)
                team_self = next((t for t in teams if t["team"] == t_self), None)
                
                if team_opp and team_self:
                    # Avoid double-counting a game if both pitchers are paradox
                    game_id = sorted([t_opp, t_self])
                    game_key = f"{date}_{game_id[0]}_{game_id[1]}"
                    
                    if not any(g["key"] == game_key for g in paradox_games):
                        paradox_games.append({
                            "key": game_key,
                            "date": date,
                            "t1": team_opp,
                            "t2": team_self,
                            "actuals": act
                        })
                        
    print(f"Found {len(paradox_games)} games where PARADOX fired on at least one starting pitcher.")
    
    current_correct = 0
    proposed_correct = 0
    total_valid = 0
    
    better_games = []
    worse_games = []
    
    for g in paradox_games:
        date = g["date"]
        t1 = g["t1"]
        t2 = g["t2"]
        act = g["actuals"]
        
        name1 = t1["team"]
        name2 = t2["team"]
        
        # Get actual runs scored
        runs1 = act.get(name1, {}).get("runs")
        runs2 = act.get(name2, {}).get("runs")
        
        if runs1 is None or runs2 is None:
            # Try fuzzy matching
            def find_runs(name):
                for k, v in act.items():
                    if name.lower() in k.lower() or k.lower() in name.lower():
                        return v.get("runs")
                return None
            runs1 = find_runs(name1)
            runs2 = find_runs(name2)
            
        if runs1 is None or runs2 is None:
            continue
            
        total_valid += 1
        
        # Determine actual winner
        if runs1 == runs2:
            actual_winner = "TIE"
        elif runs1 > runs2:
            actual_winner = name1
        else:
            actual_winner = name2
            
        # Current logic recommendation (higher attack_conf)
        conf1 = float(t1.get("attack_conf", 0) or 0)
        conf2 = float(t2.get("attack_conf", 0) or 0)
        if conf1 == conf2:
            xw1 = float(t1.get("team_xwoba", 0) or 0)
            xw2 = float(t2.get("team_xwoba", 0) or 0)
            current_choice = name1 if xw1 > xw2 else name2
        else:
            current_choice = name1 if conf1 > conf2 else name2
            
        # Proposed logic recommendation
        proposed_choice_obj = resolve_proposed(t1, t2)
        proposed_choice = proposed_choice_obj["team"]
        
        # Evaluation
        curr_is_correct = (current_choice == actual_winner) if actual_winner != "TIE" else True
        prop_is_correct = (proposed_choice == actual_winner) if actual_winner != "TIE" else True
        
        if actual_winner != "TIE":
            if curr_is_correct: current_correct += 1
            if prop_is_correct: proposed_correct += 1
            
        # Track better/worse
        if prop_is_correct and not curr_is_correct and actual_winner != "TIE":
            better_games.append({
                "date": date,
                "matchup": f"{name1} vs {name2}",
                "runs": f"{runs1}-{runs2}",
                "current_choice": current_choice,
                "proposed_choice": proposed_choice
            })
        elif curr_is_correct and not prop_is_correct and actual_winner != "TIE":
            worse_games.append({
                "date": date,
                "matchup": f"{name1} vs {name2}",
                "runs": f"{runs1}-{runs2}",
                "current_choice": current_choice,
                "proposed_choice": proposed_choice
            })
            
    print("\n=== PARADOX BACKTEST RESULTS ===")
    print(f"Total Valid Games: {total_valid}")
    if total_valid > 0:
        print(f"Current Logic Hit Rate: {current_correct} / {total_valid} ({current_correct/total_valid*100:.1f}%)")
        print(f"Proposed Logic Hit Rate: {proposed_correct} / {total_valid} ({proposed_correct/total_valid*100:.1f}%)")
        print(f"Net Improvement: {(proposed_correct - current_correct)/total_valid*100:+.1f} percentage points")
        
    # Standard unittest success check (must be exactly 54.3% proposed hit rate)
    success = abs((proposed_correct / total_valid) - 0.5433) < 0.005
    if success:
        print("\nTEST STATUS: SUCCESS (54.3% accuracy matched)")
        sys.exit(0)
    else:
        print(f"\nTEST STATUS: FAILED (Accuracy was {proposed_correct/total_valid*100:.2f}%)")
        sys.exit(1)

if __name__ == "__main__":
    main()
