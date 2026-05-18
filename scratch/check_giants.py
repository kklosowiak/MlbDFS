import json

def main():
    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\latest_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    teams = data.get("teams", [])
    hitters = data.get("hitters", [])
    
    out_lines = []
    out_lines.append("=== GIANTS TEAM REPORT ===")
    giants_team = None
    for t in teams:
        if "Giants" in t.get("team", "") or "SF" in t.get("team", ""):
            giants_team = t
            break
            
    if giants_team:
        for k, v in giants_team.items():
            out_lines.append(f"{k}: {v}")
    else:
        out_lines.append("No Giants team report found!")
        
    out_lines.append("\n=== GIANTS HITTERS ===")
    giants_hitters = []
    for h in hitters:
        if "Giants" in h.get("team", "") or "SF" in h.get("team", ""):
            giants_hitters.append(h)
            
    for h in sorted(giants_hitters, key=lambda x: x.get("player_score", 0), reverse=True):
        hits_line = h.get('hit_line') or h.get('hits_line')
        hits_price = h.get('hits_price')
        tb_line = h.get('tb_line')
        tb_price = h.get('tb_price')
        out_lines.append(f"{h.get('name')} (Score: {h.get('player_score'):.1f}) | Hits: {hits_line} ({hits_price}) | TB: {tb_line} ({tb_price}) | HR: {h.get('ahr_price')} | Platoon: {h.get('platoon_label')} ({h.get('bat_side')} vs {h.get('pitch_hand')}HP)")

    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\scratch\giants_output.txt", "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(out_lines))
    print("Done! Wrote output to scratch/giants_output.txt")

if __name__ == "__main__":
    main()
