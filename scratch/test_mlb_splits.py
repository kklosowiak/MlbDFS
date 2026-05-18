import requests
import json

def test_api():
    season = 2026
    
    # Test Team Splits
    params_team = {
        "stats": "statSplits",
        "group": "hitting",
        "season": season,
        "sitCodes": "vl,vr",
        "sportId": 1
    }
    # Wait, the above doesn't specify 'team'. Let's see what it returns if we use playerPool=all vs team level.
    # To get team stats, we might need to query the team endpoint or use `stats=season` with `teamId`
    # Let's try getting team splits by querying a specific team
    # e.g., Braves are 144
    url_team = "https://statsapi.mlb.com/api/v1/teams/144/stats"
    params = {"stats": "statSplits", "group": "hitting", "sitCodes": "vl,vr", "season": season}
    
    resp = requests.get(url_team, params=params)
    print("Team Response Code:", resp.status_code)
    try:
        data = resp.json()
        print(json.dumps(data.get('stats', [])[0].get('splits', []), indent=2)[:1000])
    except:
        pass
        
    print("\n\n---\n\n")
    # Test Pitcher Splits
    # e.g., Max Meyer is 676974
    url_pitcher = "https://statsapi.mlb.com/api/v1/people/676974/stats"
    params_pitcher = {"stats": "statSplits", "group": "pitching", "sitCodes": "vl,vr", "season": season}
    resp2 = requests.get(url_pitcher, params=params_pitcher)
    print("Pitcher Response Code:", resp2.status_code)
    try:
        data2 = resp2.json()
        print(json.dumps(data2.get('stats', [])[0].get('splits', []), indent=2)[:1000])
    except:
        pass

if __name__ == "__main__":
    test_api()
