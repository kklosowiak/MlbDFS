import json
import requests

url = "https://www.fantasylabs.com/api/sportevents/3/2026_05_22"
r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30)
data = r.json()
print("games", len(data))
# all keys from first game with non-null values
g = data[0]
for k, v in sorted(g.items()):
    if v not in (None, "", 0, 0.0, False) and "0001" not in str(v):
        print(k, ":", v)
print("\n--- PHI game ---")
for g in data:
    if g.get("HomeTeamShort") == "PHI" or g.get("VisitorTeamShort") == "PHI":
        for k in sorted(g.keys()):
            if "ML" in k or "OU" in k or "Open" in k or "Spread" in k or "Money" in k:
                print(k, g[k])
