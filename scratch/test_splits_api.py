import requests

def test_handedness_bulk():
    url = "https://statsapi.mlb.com/api/v1/sports/1/players"
    params = {
        "season": 2026
    }
    
    try:
        print("Querying bulk sports/1/players endpoint...")
        resp = requests.get(url, params=params, timeout=15)
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            people = data.get("people", [])
            print(f"Total players found: {len(people)}")
            if people:
                print("Sample player:")
                p = people[0]
                print(f"Name: {p.get('fullName')}")
                print(f"Bat side: {p.get('batSide', {}).get('code')}")
                print(f"Pitch hand: {p.get('pitchHand', {}).get('code')}")
                print(f"Primary Position: {p.get('primaryPosition', {}).get('abbreviation')}")
        else:
            print(f"Error: {resp.status_code}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_handedness_bulk()
