import json

def main():
    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\latest_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    hitters = data.get("hitters", [])
    
    sox_lineup = [
        {"name": "Sam Antonacci", "pos": "OF", "price": "$3.9K", "order": 1},
        {"name": "Munetaka Murakami", "pos": "1B", "price": "$5.7K", "order": 2},
        {"name": "Miguel Vargas", "pos": "3B", "price": "$4.9K", "order": 3},
        {"name": "Colson Montgomery", "pos": "SS", "price": "$4.3K", "order": 4},
        {"name": "Andrew Benintendi", "pos": "OF", "price": "$3.2K", "order": 5},
        {"name": "Jarred Kelenic", "pos": "OF", "price": "$2.2K", "order": 6},
        {"name": "Tristan Peters", "pos": "OF", "price": "$2.5K", "order": 7},
        {"name": "Drew Romo", "pos": "C", "price": "$3.7K", "order": 8},
        {"name": "Luisangel Acuna", "pos": "OF/SS", "price": "$2.1K", "order": 9}
    ]
    
    # Clean up name comparisons (handle accents like Acuña)
    def name_match(name1, name2):
        n1 = name1.replace("ñ", "n").replace("á", "a").replace("í", "i").replace("ó", "o").replace("ú", "u").lower()
        n2 = name2.replace("ñ", "n").replace("á", "a").replace("í", "i").replace("ó", "o").replace("ú", "u").lower()
        return n1 in n2 or n2 in n1

    out_lines = []
    out_lines.append("=== CHICAGO WHITE SOX DFS PLATOON ANALYSIS ===")
    
    found_hitters = []
    for player in sox_lineup:
        match = None
        for h in hitters:
            if name_match(player["name"], h.get("name", "")):
                match = h
                break
        
        if match:
            found_hitters.append((player, match))
        else:
            found_hitters.append((player, None))
            
    for player, h in found_hitters:
        if h:
            h_line = h.get("hits_line") or h.get("hit_line", "-")
            h_price = h.get("hits_price", "-")
            tb_line = h.get("tb_line", "-")
            tb_price = h.get("tb_price", "-")
            hr_price = h.get("ahr_price", "-")
            
            tags = []
            if h.get("is_hot"): tags.append("🔥 HOT")
            if h.get("is_juiced_target"): tags.append("🥤 JUICED")
            if h.get("is_speed_target"): tags.append("🏃 SPEED")
            
            tag_str = ", ".join(tags) if tags else "None"
            
            out_lines.append(
                f"{player['order']}. {h.get('name')} ({h.get('bat_side')}B) - {player['pos']} {player['price']}\n"
                f"   Score: {h.get('player_score'):.1f} | xwOBA: {h.get('matchup_xwoba', '-')} | Platoon: {h.get('platoon_label', 'Neutral')}\n"
                f"   Props -> Hits: {h_line} ({h_price}) | TB: {tb_line} ({tb_price}) | HR: {hr_price}\n"
                f"   Tags -> {tag_str}\n"
            )
        else:
            out_lines.append(f"{player['order']}. {player['name']} - {player['pos']} {player['price']} (NOT FOUND IN DATABASE)\n")

    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\scratch\sox_analysis_output.txt", "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(out_lines))
    print("Done! Wrote output to scratch/sox_analysis_output.txt")

if __name__ == "__main__":
    main()
