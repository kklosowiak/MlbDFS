"""Script to analyze the 5-game slate from DraftKings Salaries and OMEGA export."""
import json
import csv
import sys
from pathlib import Path
from utils.normalization import normalize_player_name

# Mappings from OMEGA team name to DK abbreviation
TEAM_MAP_OMEGA_TO_DK = {
    "Philadelphia Phillies": "PHI",
    "Miami Marlins": "MIA",
    "New York Mets": "NYM",
    "Cincinnati Reds": "CIN",
    "Detroit Tigers": "DET",
    "Houston Astros": "HOU",
    "San Diego Padres": "SD",
    "St. Louis Cardinals": "STL",
    "Kansas City Royals": "KC",
    "Washington Nationals": "WSH",
}

TEAM_MAP_DK_TO_OMEGA = {v: k for k, v in TEAM_MAP_OMEGA_TO_DK.items()}

def load_salaries(path):
    salaries = []
    with open(path, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            salaries.append({
                "Position": row["Position"],
                "Name": row["Name"],
                "Salary": int(row["Salary"]),
                "GameInfo": row["Game Info"],
                "Team": row["TeamAbbrev"],
                "AvgPts": float(row["AvgPointsPerGame"]) if row["AvgPointsPerGame"] else 0.0,
            })
    return salaries

def stack_sigs(t):
    out = []
    if t.get("is_whale"): out.append("WHALE")
    if t.get("is_shark"): out.append("SHARK")
    if t.get("is_sharp"): out.append("HEAVY$")
    if t.get("is_burst"): out.append("BURST")
    if t.get("is_blind_spot"): out.append("BLIND")
    if t.get("is_trap"): out.append("CHALK")
    bf = t.get("bullpen_fatigue", 0) or 0
    if bf >= 90: out.append("EXHAUSTED")
    elif bf >= 75: out.append("GASSED")
    elif bf >= 65: out.append("WEARY")
    if t.get("trend") == "SURGING": out.append("SURGE")
    return out

def pitcher_sigs(p):
    out = []
    if p.get("is_trap"): out.append("TRAP")
    if p.get("is_hazard"): out.append("HAZARD")
    if p.get("is_shark"): out.append("SHARK")
    if p.get("is_whale"): out.append("WHALE")
    if p.get("is_sharp"): out.append("HEAVY$")
    if p.get("form_status") == "SURGING": out.append("SURGING")
    if p.get("form_status") == "COLD": out.append("COLD")
    if p.get("is_low_ceiling"): out.append("LOW_CEIL")
    if p.get("is_paradox"): out.append("PARADOX")
    return out

def main():
    # Auto-detect newest omega-results*.json in Downloads unless specified as arg
    if len(sys.argv) > 1:
        omega_path = Path(sys.argv[1])
    else:
        downloads_dir = Path(r"C:\Users\konra\Downloads")
        files = list(downloads_dir.glob("omega-results*.json"))
        if files:
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            omega_path = files[0]
            print(f"[AUTO-DETECT]: Using newest export in Downloads: {omega_path.name}")
        else:
            omega_path = Path(r"C:\Users\konra\Downloads\omega-results(150).json")
            
    dk_path = Path(r"C:\Users\konra\Downloads\DKSalaries(19).csv")
    
    if not omega_path.exists() or not dk_path.exists():
        print(f"Error: Missing files. Omega: {omega_path.exists()}, DK: {dk_path.exists()}")
        sys.exit(1)
        
    with open(omega_path, "r", encoding="utf-8") as f:
        omega_data = json.load(f)
        
    dk_players = load_salaries(dk_path)
    
    # Identify target teams on our 5-game slate
    target_dk_teams = set(TEAM_MAP_DK_TO_OMEGA.keys())
    
    # Filter DK players to only target teams
    dk_players = [p for p in dk_players if p["Team"] in target_dk_teams]
    
    # Group DK players by normalized name
    dk_by_name = {}
    for p in dk_players:
        norm_name = normalize_player_name(p["Name"])
        dk_by_name[norm_name] = p
        
    print(f"Loaded {len(dk_players)} players from DK Salaries.")
    
    # 1. Stacks / Teams Analysis
    teams = [t for t in omega_data.get("teams", []) if t["team"] in TEAM_MAP_OMEGA_TO_DK]
    for t in teams:
        t["dk_abbr"] = TEAM_MAP_OMEGA_TO_DK[t["team"]]
    
    # 2. Pitchers Analysis
    pitchers = [p for p in omega_data.get("pitchers", []) if p["team"] in TEAM_MAP_OMEGA_TO_DK]
    matched_pitchers = []
    
    for p in pitchers:
        p_team_dk = TEAM_MAP_OMEGA_TO_DK[p["team"]]
        norm_p_name = normalize_player_name(p["pitcher"])
        
        # Match by name first
        if p["pitcher"].lower() == "tbd":
            dk_p = None
        else:
            dk_p = dk_by_name.get(norm_p_name)
            if not dk_p:
                # Try to match by team and position SP or RP
                team_sps = [x for x in dk_players if x["Team"] == p_team_dk and "P" in x["Position"]]
                if team_sps:
                    # Fallback to matching by last name or just team's main starter
                    dk_p = team_sps[0]
                    print(f"[MATCH FALLBACK]: Matched pitcher {p['pitcher']} to {dk_p['Name']} by team {p_team_dk}")
                else:
                    print(f"[WARNING]: Could not match pitcher {p['pitcher']} ({p['team']}) to DraftKings salaries.")
                
        salary = dk_p["Salary"] if dk_p else 0
        p["salary"] = salary
        p["dk_abbr"] = p_team_dk
        p["value_score"] = (p.get("alpha_score", 0) / (salary / 1000)) if salary > 0 else 0
        p["dk_name"] = dk_p["Name"] if dk_p else f"TBD ({p['team']})"
        matched_pitchers.append(p)
        
    # 3. Hitters Analysis
    hitters = [h for h in omega_data.get("hitters", []) if h["team"] in TEAM_MAP_OMEGA_TO_DK]
    matched_hitters = []
    for h in hitters:
        norm_h_name = normalize_player_name(h["name"])
        dk_h = dk_by_name.get(norm_h_name)
        
        # Sometimes there's minor differences (e.g. Junior Caminero vs Jr. Caminero)
        if not dk_h:
            # Let's search for partial match
            for name_key, dk_p in dk_by_name.items():
                if norm_h_name in name_key or name_key in norm_h_name:
                    dk_h = dk_p
                    break
                    
        if dk_h:
            h["salary"] = dk_h["Salary"]
            h["position"] = dk_h["Position"]
            h["dk_abbr"] = TEAM_MAP_OMEGA_TO_DK[h["team"]]
            h["value_score"] = (h.get("player_score", 0) / (dk_h["Salary"] / 1000)) if dk_h["Salary"] > 0 else 0
            matched_hitters.append(h)
        else:
            # print(f"[WARNING]: Could not match hitter {h['name']} ({h['team']}) to DraftKings salaries.")
            pass
            
    print(f"Matched {len(matched_pitchers)} pitchers and {len(matched_hitters)} hitters.")
    
    # Sort and print results to markdown
    report = []
    report.append(f"# 🎂 OMEGA DFS Birthday Analysis: 5-Game Slate")
    report.append(f"**DraftKings Salaries & OMEGA Model Export Matching** (Snapshot: {omega_data.get('timestamp')})\n")
    
    report.append("> [!NOTE]")
    report.append("> Happy Birthday! This 5-game slate features: SD@STL, DET@HOU, KC@WSH, MIA@PHI, and NYM@CIN. Here is the OMEGA system breakdown to help you win today.\n")
    
    # --- Top Stacks ---
    report.append("## ⚾ Stack Rankings (Team Offense)")
    report.append("Sorted by OMEGA Stack Score.\n")
    report.append("| Rank | Team | Opponent | Stack Score | CONF | Implied Runs | Bullpen Fatigue | Signals | Opp Pitcher |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    teams_sorted = sorted(teams, key=lambda x: -x.get("stack_score", 0))
    for i, t in enumerate(teams_sorted, 1):
        sigs = stack_sigs(t)
        total_sig = t.get("total_signal") or "-"
        opp_abbr = TEAM_MAP_OMEGA_TO_DK.get(t.get("opponent"), t.get("opponent")[:3].upper())
        report.append(
            f"| {i} | **{t['team']}** ({t['dk_abbr']}) | {opp_abbr} | {t.get('stack_score', 0):.1f} | {t.get('attack_conf', 0)}% | {t.get('implied_total', '-'):.1f} | {t.get('bullpen_fatigue', 0)}% | {','.join(sigs) or '-'} {total_sig} | {t.get('opp_pitcher', 'TBD')} |"
        )
    report.append("\n" + "---" + "\n")
    
    # --- Pitchers ---
    report.append("##  pitcher rankings")
    report.append("Sorted by Value Score (OMEGA Score / $1k Salary). Traps are highlighted separately.\n")
    report.append("| Rank | Pitcher | Team | Salary | OMEGA Score | CONF | Value Score | Form | Notes |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    pitchers_clean = [p for p in matched_pitchers if not p.get("is_trap")]
    pitchers_traps = [p for p in matched_pitchers if p.get("is_trap")]
    
    pitchers_clean_sorted = sorted(pitchers_clean, key=lambda x: -x["value_score"])
    for i, p in enumerate(pitchers_clean_sorted, 1):
        sigs = pitcher_sigs(p)
        report.append(
            f"| {i} | **{p['dk_name']}** | {p['dk_abbr']} | ${p['salary']:,} | {p.get('alpha_score', 0):.1f} | {p.get('attack_conf', 0)}% | **{p['value_score']:.2f}** | {p.get('form_status', 'Neutral')} | {','.join(sigs) or '-'} |"
        )
        
    if pitchers_traps:
        report.append("\n### 🚨 SP Trap Warnings")
        report.append("Vegas Traps / Short Leash arms to fade or stack against:\n")
        report.append("| Pitcher | Team | Salary | OMEGA Score | CONF | Value Score | Trap Type | Notes |")
        report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
        for p in sorted(pitchers_traps, key=lambda x: -x["value_score"]):
            sigs = pitcher_sigs(p)
            report.append(
                f"| **{p['dk_name']}** | {p['dk_abbr']} | ${p['salary']:,} | {p.get('alpha_score', 0):.1f} | {p.get('attack_conf', 0)}% | {p['value_score']:.2f} | **{p.get('trap_type', 'Trap')}** | {','.join(sigs) or '-'} |"
            )
            
    report.append("\n" + "---" + "\n")
    
    # --- Top Value Hitters ---
    report.append("## 🎯 Hitter Value Rankings")
    report.append("Top salary-saving values on the slate (OMEGA Score >= 65, sorted by Value Score = Score/$1k).\n")
    report.append("| Rank | Player | Pos | Team | Salary | OMEGA Score | Value Score | Platoon Label | Target | Opp Pitcher |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    hitters_value = [h for h in matched_hitters if h.get("player_score", 0) >= 65]
    hitters_value_sorted = sorted(hitters_value, key=lambda x: -x["value_score"])[:30]
    
    for i, h in enumerate(hitters_value_sorted, 1):
        target_str = "🎯 Yes" if h.get("is_juiced_target") else "No"
        report.append(
            f"| {i} | **{h['name']}** | {h['position']} | {h['dk_abbr']} | ${h['salary']:,} | {h.get('player_score', 0):.1f} | **{h['value_score']:.2f}** | {h.get('platoon_label', 'NEUTRAL')} | {target_str} | {h.get('opp_pitcher', 'TBD')} |"
        )
        
    report.append("\n" + "---" + "\n")
    
    # --- Slate Breakers ---
    report.append("## 👑 Slate-Breakers (Top Raw Projections)")
    report.append("The highest projected hitters on the 5-game slate, regardless of price:\n")
    report.append("| Rank | Player | Pos | Team | Salary | OMEGA Score | Value Score | Platoon Label | Target | Opp Pitcher |")
    report.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
    
    hitters_raw_sorted = sorted(matched_hitters, key=lambda x: -x.get("player_score", 0))[:20]
    for i, h in enumerate(hitters_raw_sorted, 1):
        target_str = "🎯 Yes" if h.get("is_juiced_target") else "No"
        report.append(
            f"| {i} | **{h['name']}** | {h['position']} | {h['dk_abbr']} | ${h['salary']:,} | {h.get('player_score', 0):.1f} | {h['value_score']:.2f} | {h.get('platoon_label', 'NEUTRAL')} | {target_str} | {h.get('opp_pitcher', 'TBD')} |"
        )
        
    # Write report to files
    report_text = "\n".join(report)
    out_md = Path(r"c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\birthday_slate_analysis.md")
    out_md.write_text(report_text, encoding="utf-8")
    print(f"Report written to {out_md}")
    
    # Also output to stdout so we can view it in the console
    # print(report_text)

if __name__ == "__main__":
    main()
