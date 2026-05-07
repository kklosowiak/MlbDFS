import sys, os, json, requests
sys.path.append(os.getcwd())
from utils.normalization import normalize_player_name

pitcher_name = "Ranger Suarez"
p_norm = normalize_player_name(pitcher_name)
print(f"Normalized name: '{p_norm}'")

# Check Tier 2 - cache
cache = json.load(open("data/statcast_cache.json"))
p_data = cache.get(p_norm)
print(f"Tier 2 cache lookup: {p_data}")

# Check Tier 3 - Live API (with full debug)
print("\nTier 3 - Live API search:")
resp = requests.get(
    "https://statsapi.mlb.com/api/v1/people/search",
    params={"names": pitcher_name, "sportId": 1},
    timeout=10
)
print(f"  Search URL: {resp.url}")
print(f"  Status: {resp.status_code}")
people = resp.json().get('people', [])
print(f"  People found: {len(people)}")
if people:
    player_id = people[0]['id']
    print(f"  First match: ID={player_id}, Name={people[0].get('fullName')}")
    
    stats_resp = requests.get(
        f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats",
        params={"stats": "season", "season": 2026, "group": "pitching"},
        timeout=10
    )
    print(f"  Stats URL: {stats_resp.url}")
    print(f"  Stats status: {stats_resp.status_code}")
    
    stats_data = stats_resp.json()
    splits = stats_data.get('stats', [{}])[0].get('splits', [])
    print(f"  Splits found: {len(splits)}")
    if splits:
        stat = splits[0].get('stat', {})
        print(f"  ERA={stat.get('era')}, K={stat.get('strikeOuts')}, IP={stat.get('inningsPitched')}")
    else:
        print(f"  Full response: {json.dumps(stats_data, indent=2)[:500]}")
