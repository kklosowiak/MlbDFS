import json

def main():
    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\latest_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    teams = data.get("teams", [])
    hitters = data.get("hitters", [])
    
    out_lines = []
    out_lines.append("=== ARIZONA TEAM REPORT ===")
    ari_team = None
    for t in teams:
        if "Arizona" in t.get("team", "") or "ARI" in t.get("team", ""):
            ari_team = t
            break
            
    if ari_team:
        for k, v in ari_team.items():
            out_lines.append(f"{k}: {v}")
    else:
        out_lines.append("No Arizona team report found!")
        
    out_lines.append("\n=== ARIZONA HITTERS ===")
    ari_hitters = []
    for h in hitters:
        if "Arizona" in h.get("team", "") or "ARI" in h.get("team", ""):
            ari_hitters.append(h)
            
    for h in sorted(ari_hitters, key=lambda x: x.get("player_score", 0), reverse=True):
        hits_line = h.get('hit_line') or h.get('hits_line')
        hits_price = h.get('hits_price')
        tb_line = h.get('tb_line')
        tb_price = h.get('tb_price')
        out_lines.append(f"{h.get('name')} (Score: {h.get('player_score'):.1f}) | Hits: {hits_line} ({hits_price}) | TB: {tb_line} ({tb_price}) | HR: {h.get('ahr_price')} | Platoon: {h.get('platoon_label')} ({h.get('bat_side')} vs {h.get('pitch_hand')}HP)")

    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\scratch\ari_output.txt", "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(out_lines))
    print("Done! Wrote output to scratch/ari_output.txt")

if __name__ == "__main__":
    main()
