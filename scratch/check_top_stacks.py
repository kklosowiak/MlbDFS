import json

def main():
    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\latest_results.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        
    teams = data.get("teams", [])
    pitchers = data.get("pitchers", [])
    
    out_lines = []
    out_lines.append("=== TOP TEAM STACKS ===")
    sorted_teams = sorted(teams, key=lambda x: x.get("stack_score", 0), reverse=True)
    for i, t in enumerate(sorted_teams[:12], 1):
        signals = []
        if t.get("is_shark"): signals.append("🦈 SHARK")
        if t.get("is_whale"): signals.append("🐳 WHALE")
        if t.get("is_sharp"): signals.append("🎯 SHARP")
        if t.get("is_storm"): signals.append("⛈️ STORM")
        if t.get("is_steam"): signals.append("💨 STEAM")
        if t.get("is_burst"): signals.append("🔥 BURST")
        
        sig_str = ", ".join(signals) if signals else "None"
        out_lines.append(f"{i}. {t.get('team')} ({t.get('stack_score'):.1f}) | Opp Pitcher: {t.get('opp_pitcher')} | Div: {t.get('divergence')} | Signals: {sig_str}")
        
    out_lines.append("\n=== TOP PITCHERS ===")
    sorted_pitchers = sorted(pitchers, key=lambda x: x.get("alpha_score", 0), reverse=True)
    for i, p in enumerate(sorted_pitchers[:12], 1):
        signals = []
        if p.get("is_shark"): signals.append("🦈 SHARK")
        if p.get("is_whale"): signals.append("🐳 WHALE")
        if p.get("is_sharp"): signals.append("🎯 SHARP")
        if p.get("is_trap"): signals.append("🚨 TRAP")
        if p.get("is_paradox"): signals.append("⚠️ PARADOX")
        if p.get("is_hazard"): signals.append("⚡ HAZARD")
        
        sig_str = ", ".join(signals) if signals else "None"
        out_lines.append(f"{i}. {p.get('pitcher')} ({p.get('team')}) - Alpha: {p.get('alpha_score'):.1f} | Opp: {p.get('opponent')} | Signals: {sig_str}")

    with open(r"C:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\scratch\stacks_output.txt", "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(out_lines))
    print("Done! Wrote output to scratch/stacks_output.txt")

if __name__ == "__main__":
    main()
