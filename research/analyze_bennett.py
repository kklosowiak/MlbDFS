import json
from pathlib import Path

archive_dir = Path(r"c:\Users\konra\OneDrive\Desktop\Antigravity\Projects\MlbDFS\reports\archive")
actuals_files = list(archive_dir.glob("actuals_cache_*.json"))

bennett_starts = []

for f in actuals_files:
    try:
        with open(f, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for team, stats in data.items():
                sp_stats = stats.get("sp_stats", {})
                if sp_stats and sp_stats.get("name") == "Jake Bennett":
                    # Find opponent team in the same file
                    opp_team = None
                    opp_runs = 0
                    opp_hitters = {}
                    for t2, s2 in data.items():
                        if t2 != team:
                            # Verify if it's the same game.
                            # In actuals_cache, games are adjacent. But let's check if the SP opposing name matches or if they played each other.
                            # Usually actuals_cache only contains games played that day.
                            # Let's just find the opponent by looking at who scored runs or matched.
                            pass
                    
                    bennett_starts.append({
                        "date": f.name.replace("actuals_cache_", "").replace(".json", ""),
                        "team": team,
                        "ip": sp_stats.get("ip"),
                        "k": sp_stats.get("k"),
                        "er": sp_stats.get("er"),
                        "runs_allowed": sp_stats.get("er") # approximation
                    })
    except Exception as e:
        pass

print("--- Jake Bennett Starts Found ---")
for start in bennett_starts:
    print(f"Date: {start['date']} | Team: {start['team']} | IP: {start['ip']} | K: {start['k']} | ER: {start['er']}")

# Let's check June 4 game details specifically
jun4_file = archive_dir / "actuals_cache_2026-06-04.json"
if jun4_file.exists():
    with open(jun4_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print("\n--- June 4, 2026 Game Actuals ---")
        for team, stats in data.items():
            if "jake bennett" in str(stats).lower() or team == "Baltimore Orioles" or team == "Boston Red Sox":
                print(f"Team: {team} | Runs: {stats.get('runs')}")
                sp = stats.get("sp_stats", {})
                print(f"  SP: {sp.get('name')} | IP: {sp.get('ip')} | ER: {sp.get('er')} | K: {sp.get('k')}")
                # Print top hitters
                hitters = stats.get("hitters", {})
                good_hitters = {k: v for k, v in hitters.items() if v.get("hits", 0) > 0 or v.get("hr", 0) > 0}
                print("  Hitters:")
                for h_name, h_stats in good_hitters.items():
                    print(f"    - {h_name}: Hits={h_stats.get('hits')}, HR={h_stats.get('hr')}, RBI={h_stats.get('rbi')}")

# Let's check June 10 game details specifically
jun10_file = archive_dir / "actuals_cache_2026-06-10.json"
if jun10_file.exists():
    with open(jun10_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
        print("\n--- June 10, 2026 Game Actuals ---")
        for team, stats in data.items():
            # In actuals cache, let's look for Boston Red Sox or Tampa Bay Rays
            if team == "Boston Red Sox" or team == "Tampa Bay Rays":
                print(f"Team: {team} | Runs: {stats.get('runs')}")
                sp = stats.get("sp_stats", {})
                print(f"  SP: {sp.get('name')} | IP: {sp.get('ip')} | ER: {sp.get('er')} | K: {sp.get('k')}")
                hitters = stats.get("hitters", {})
                good_hitters = {k: v for k, v in hitters.items() if v.get("hits", 0) > 0 or v.get("hr", 0) > 0}
                print("  Hitters:")
                for h_name, h_stats in good_hitters.items():
                    print(f"    - {h_name}: Hits={h_stats.get('hits')}, HR={h_stats.get('hr')}, RBI={h_stats.get('rbi')}")
