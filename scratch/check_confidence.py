import requests
import json

def check_pitcher(name):
    print(f"\nChecking {name}...")
    try:
        resp = requests.get(
            "https://statsapi.mlb.com/api/v1/people/search",
            params={"names": name, "sportId": 1},
            timeout=10
        )
        if resp.status_code == 200:
            people = resp.json().get('people', [])
            if people:
                player_id = people[0]['id']
                print(f"  Found Player ID: {player_id}")
                stats_resp = requests.get(
                    f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats",
                    params={"stats": "season", "season": 2026, "group": "pitching"},
                    timeout=10
                )
                if stats_resp.status_code == 200:
                    stats_list = stats_resp.json().get('stats', [])
                    if stats_list:
                        splits = stats_list[0].get('splits', [])
                        if splits:
                            stat = splits[0].get('stat', {})
                            era = stat.get('era')
                            k = stat.get('strikeOuts')
                            ip = stat.get('inningsPitched')
                            print(f"  2026 Stats: ERA={era}, K={k}, IP={ip}")
                            return {"era": era, "k": k, "ip": ip}
                    
                    print("  No 2026 stats. Checking 2025...")
                    stats_resp = requests.get(
                        f"https://statsapi.mlb.com/api/v1/people/{player_id}/stats",
                        params={"stats": "season", "season": 2025, "group": "pitching"},
                        timeout=10
                    )
                    if stats_resp.status_code == 200:
                        stats_list = stats_resp.json().get('stats', [])
                        if stats_list:
                            splits = stats_list[0].get('splits', [])
                            if splits:
                                stat = splits[0].get('stat', {})
                                era = stat.get('era')
                                k = stat.get('strikeOuts')
                                ip = stat.get('inningsPitched')
                                print(f"  2025 Stats: ERA={era}, K={k}, IP={ip}")
                                return {"era": era, "k": k, "ip": ip}
                    print("  No 2025 stats found.")
            else:
                print("  Player not found in search.")
    except Exception as e:
        print(f"  Error: {e}")
    return None

if __name__ == "__main__":
    check_pitcher("Trevor McDonald")
    check_pitcher("Chase Petty")
