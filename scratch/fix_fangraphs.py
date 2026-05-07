import requests
import pandas as pd
import io

url = "https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=pit&lg=all&qual=0&season=2026&season1=2026&startdate=2026-01-01&enddate=2026-12-31&month=0&hand=&team=0&pageitems=3000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&sortdir=default&sortstat=SIERA"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
}

print("Attempting to fetch 2026 FanGraphs data via API...")
try:
    response = requests.get(url, headers=headers, timeout=15)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data.get('data', []))} pitchers.")
        # Save to CSV
        df = pd.DataFrame(data.get('data', []))
        df.to_csv("data/physics_leaderboard_2026.csv", index=False)
        print("Saved to data/physics_leaderboard_2026.csv")
    else:
        print(response.text[:200])
except Exception as e:
    print(f"Error: {e}")

# Repeat for 2025
url_2025 = "https://www.fangraphs.com/api/leaders/major-league/data?age=&pos=all&stats=pit&lg=all&qual=0&season=2025&season1=2025&startdate=2025-01-01&enddate=2025-12-31&month=0&hand=&team=0&pageitems=3000&pagenum=1&ind=0&rost=0&players=&type=8&postseason=&sortdir=default&sortstat=SIERA"
print("\nAttempting to fetch 2025 FanGraphs data via API...")
try:
    response = requests.get(url_2025, headers=headers, timeout=15)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data.get('data', []))} pitchers.")
        df = pd.DataFrame(data.get('data', []))
        df.to_csv("data/physics_leaderboard_2025.csv", index=False)
        print("Saved to data/physics_leaderboard_2025.csv")
except Exception as e:
    print(f"Error: {e}")
