import json

def main():
    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\latest_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    hitters = data.get("hitters", [])
    
    duran = None
    for h in hitters:
        if "duran" in h.get("name", "").lower() or "ezequiel" in h.get("name", "").lower():
            duran = h
            break
            
    print("=== DURAN DETAILS ===")
    if duran:
        for k, v in duran.items():
            print(f"{k}: {v}")
    else:
        print("Ezequiel Duran not found in database!")

if __name__ == "__main__":
    main()
