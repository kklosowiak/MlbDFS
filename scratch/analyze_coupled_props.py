import json
import os

def main():
    results_path = r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\latest_results.json"
    if not os.path.exists(results_path):
        print(f"Error: {results_path} does not exist.")
        return
        
    with open(results_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    hitters = data.get("hitters", [])
    
    # Active teams on tonight's slate
    active_teams = {
        "NYY", "TOR", "BOS", "KC", "MIL", "CHC", "HOU", "MIN", "TEX", "COL",
        "OAK", "LAA", "SF", "ARI", "CWS", "SEA", "LAD", "SD",
        "New York Yankees", "Toronto Blue Jays", "Boston Red Sox", "Kansas City Royals",
        "Milwaukee Brewers", "Chicago Cubs", "Houston Astros", "Minnesota Twins",
        "Texas Rangers", "Colorado Rockies", "Athletics", "Los Angeles Angels",
        "San Francisco Giants", "Arizona Diamondbacks", "Chicago White Sox",
        "Seattle Mariners", "Los Angeles Dodgers", "San Diego Padres", "Oakland Athletics"
    }
    
    # Map teams to common abbreviations for grouping
    team_map = {
        "New York Yankees": "NYY", "Yankees": "NYY",
        "Toronto Blue Jays": "TOR", "Blue Jays": "TOR",
        "Boston Red Sox": "BOS", "Red Sox": "BOS",
        "Kansas City Royals": "KC", "Royals": "KC",
        "Milwaukee Brewers": "MIL", "Brewers": "MIL",
        "Chicago Cubs": "CHC", "Cubs": "CHC",
        "Houston Astros": "HOU", "Astros": "HOU",
        "Minnesota Twins": "MIN", "Twins": "MIN",
        "Texas Rangers": "TEX", "Rangers": "TEX",
        "Colorado Rockies": "COL", "Rockies": "COL",
        "Athletics": "OAK", "Oakland Athletics": "OAK",
        "Los Angeles Angels": "LAA", "Angels": "LAA",
        "San Francisco Giants": "SF", "Giants": "SF",
        "Arizona Diamondbacks": "ARI", "Diamondbacks": "ARI",
        "Chicago White Sox": "CWS", "White Sox": "CWS",
        "Seattle Mariners": "SEA", "Mariners": "SEA",
        "Los Angeles Dodgers": "LAD", "Dodgers": "LAD",
        "San Diego Padres": "SD", "Padres": "SD"
    }
    
    print("ALL UNIQUE KEYS IN HITTERS LIST IN JSON:")
    unique_keys = set()
    for h in hitters:
        unique_keys.update(h.keys())
    print(unique_keys)
    print()

    filtered_hitters = []
    for h in hitters:
        team_name = h.get("team", "")
        # Map to abbreviation
        abbr = team_map.get(team_name, team_name)
        if abbr in active_teams:
            # Map keys dynamically to handle both singular/plural (e.g. hits_line vs hit_line)
            hits_line = h.get("hits_line") or h.get("hit_line") or h.get("hit")
            hits_price = h.get("hits_price") or h.get("hit_price")
            tb_line = h.get("tb_line") or h.get("tb") or h.get("bases_line")
            tb_price = h.get("tb_price") or h.get("bases_price")
            
            filtered_hitters.append({
                "name": h.get("name"),
                "abbr": abbr,
                "team": team_name,
                "opponent": h.get("opponent"),
                "opp_pitcher": h.get("opp_pitcher"),
                "player_score": h.get("player_score"),
                "hits_line": hits_line,
                "hits_price": hits_price,
                "tb_line": tb_line,
                "tb_price": tb_price,
                "ahr_price": h.get("ahr_price"),
                "platoon_multiplier": h.get("platoon_multiplier"),
                "platoon_label": h.get("platoon_label"),
                "bat_side": h.get("bat_side"),
                "pitch_hand": h.get("pitch_hand")
            })
            
    # Group by team
    by_team = {}
    for h in filtered_hitters:
        abbr = h["abbr"]
        if abbr not in by_team:
            by_team[abbr] = []
        by_team[abbr].append(h)
        
    print(f"Total active hitters: {len(filtered_hitters)}")
    print(f"Total teams represented: {len(by_team)}\n")
    
    if filtered_hitters:
        print("SAMPLE HITTER KEYS:", list(filtered_hitters[0].keys()))
        print("SAMPLE HITTER DATA:", filtered_hitters[0])
        print()
    
    # Sort teams by their top hitter's player_score
    sorted_teams = sorted(by_team.keys(), key=lambda t: max(x["player_score"] for x in by_team[t]), reverse=True)
    
    for team in sorted_teams[:6]: # Only print top 6 teams to avoid truncation
        print(f"=== TEAM: {team} ===")
        team_hitters = sorted(by_team[team], key=lambda x: x["player_score"], reverse=True)
        for h in team_hitters[:4]: # Top 4 hitters per team
            h_price = h.get('hits_price')
            h_price_str = f"({'+' if isinstance(h_price, (int, float)) and h_price > 0 else ''}{h_price})" if h_price is not None and h_price != 0 else ""
            hits_str = f"Hits: {h['hits_line']} {h_price_str}"
            
            t_price = h.get('tb_price')
            t_price_str = f"({'+' if isinstance(t_price, (int, float)) and t_price > 0 else ''}{t_price})" if t_price is not None and t_price != 0 else ""
            tb_str = f"TB: {h['tb_line']} {t_price_str}"
            
            hr_str = f"HR: {h['ahr_price']}"
            platoon = f"Platoon: {h['platoon_label']} ({h['bat_side']} vs {h['pitch_hand']}HP)"
            print(f"  {h['name']} (Score: {h['player_score']:.1f}) | {hits_str} | {tb_str} | {hr_str} | {platoon}")
        print()

if __name__ == "__main__":
    main()
