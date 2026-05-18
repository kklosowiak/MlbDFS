import json

def main():
    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\latest_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    pitchers = data.get("pitchers", [])
    
    woo = None
    for p in pitchers:
        if "woo" in p.get("pitcher", "").lower() or "bryan" in p.get("pitcher", "").lower():
            woo = p
            break
            
    out_lines = ["=== WOO DETAILS ==="]
    if woo:
        for k, v in woo.items():
            out_lines.append(f"{k}: {v}")
    else:
        out_lines.append("Bryan Woo not found in pitchers list!")

    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\scratch\woo_output.txt", "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(out_lines))
    print("Done! Wrote output to scratch/woo_output.txt")

if __name__ == "__main__":
    main()
