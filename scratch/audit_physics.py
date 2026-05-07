"""Full transparency audit: what data did each pitcher actually get?"""
import sys, os, json
sys.path.append(os.getcwd())
from utils.normalization import normalize_player_name
from data.pitcher_analyzer import PitcherAnalyzer

analyzer = PitcherAnalyzer()

# Today's probable pitchers
prob = json.load(open("data/probable_pitchers.json"))

# Also load the results to see final scores
results = json.load(open("reports/latest_results.json"))
pitcher_results = {p['pitcher']: p for p in results.get('pitchers', [])}

print("=" * 100)
print("FULL PHYSICS AUDIT - WHAT DATA SOURCE DID EACH PITCHER HIT?")
print("=" * 100)

# Check master matrix names
master_names = list(analyzer.fetch_pitcher_physics.__code__.co_consts)  # won't work, do it manually

master_matrix = {
    "Luis Castillo": {"siera": 3.12, "csw": 0.29},
    "Max Fried": {"siera": 3.10, "csw": 0.27},
    "Ranger Suarez": {"siera": 3.35, "csw": 0.28},
    "Dylan Cease": {"siera": None},  # Check if in matrix
    "Jack Leiter": {"siera": 3.85, "csw": 0.27},
    "Randy Vasquez": {"siera": 4.05, "csw": 0.25},
    "Jack Kochanowicz": None,  # Probably NOT in matrix
}

# Load statcast cache
cache = json.load(open("data/statcast_cache.json"))
pitchers_in_cache = {k: v for k, v in cache.items() if v.get('type') == 'pitcher'}

print(f"\nData sources available:")
print(f"  Master Matrix: ~40 hardcoded elite pitchers (SIERA + CSW from FanGraphs historical)")  
print(f"  StatsAPI Cache: {len(pitchers_in_cache)} pitchers (ERA, K, IP from MLB.com - refreshed today)")
print(f"  Live API: Direct MLB StatsAPI person search (ERA, K, IP - real-time)")
print(f"  FanGraphs/pybaseball: BLOCKED (Cloudflare 403)")
print()

for team, pitcher in sorted(prob.items()):
    norm = normalize_player_name(pitcher)
    result = pitcher_results.get(pitcher, {})
    
    # Determine which tier hit
    physics = analyzer.fetch_pitcher_physics(pitcher)
    
    in_cache = norm in pitchers_in_cache
    cache_data = pitchers_in_cache.get(norm, {})
    
    # What tier actually resolved?
    if physics['confidence'] == 'high' and norm in [normalize_player_name(n) for n in [
        "Luis Castillo", "Max Fried", "Ranger Suarez", "Jack Leiter", 
        "Randy Vasquez", "Randy V\u00e1squez", "Jack Kochanowicz"
    ]]:
        # Check if it's truly in master matrix
        tier = "TIER 1: Master Matrix (hardcoded SIERA/CSW)"
        data_type = "STATIC - last updated manually"
    elif in_cache and cache_data.get('ip', 0) > 5.0:
        tier = "TIER 2: StatsAPI Cache"
        data_type = f"REAL MLB DATA - ERA={cache_data.get('era')}, K={cache_data.get('k')}, IP={cache_data.get('ip')}"
    else:
        tier = "TIER 3: Live MLB API Search"
        data_type = "REAL MLB DATA - fetched on-demand"
    
    print(f"{pitcher:25s} | conf={physics['confidence']:4s} | SIERA={physics['siera']:.2f} | CSW={physics['csw']:.3f} | {tier}")
    print(f"{'':25s} | {data_type}")
    if in_cache:
        cd = cache_data
        ip = float(cd.get('ip', 0))
        k = float(cd.get('k', 0))
        if ip > 0:
            print(f"{'':25s} | Actual K/IP ratio: {k/ip:.2f} (used to derive proxy SIERA/CSW)")
    print()

print("=" * 100)
print("IMPORTANT CAVEATS:")
print("=" * 100)
print("""
1. SIERA and CSW% are FanGraphs-proprietary metrics. They require FanGraphs data.
   Since FanGraphs is Cloudflare-blocked, we CANNOT get true SIERA/CSW right now.
   
2. For Tier 2 and Tier 3 pitchers, SIERA and CSW are PROXIED from K/IP ratio:
   - Proxy SIERA = 4.00 - (K/IP - 0.85) * 1.2
   - Proxy CSW   = 0.25 + (K/IP - 0.85) * 0.10
   These are reasonable approximations but NOT the real FanGraphs values.
   
3. The ERA, K, and IP values ARE real - they come directly from MLB.com's official API.

4. Master Matrix pitchers have REAL FanGraphs SIERA/CSW but they were set manually
   and may be from 2025 season data, not live 2026.
""")
