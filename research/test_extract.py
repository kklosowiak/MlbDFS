import json
import re
import requests

url = "https://terminal.fantasylabs.com/vegas?sportId=3&date=05/22/2026"
html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text

# Find RSC payload or props blob - look for visitorTeamName
idx = html.find("visitorTeamName")
print("first visitorTeamName at", idx)
chunk = html[idx : idx + 800]
print(chunk)

# Count games
print("visitorGameMoneylineOpen count", html.count("visitorGameMoneylineOpen"))

# Try extract each game object via regex for team names
names = re.findall(r'"visitorTeamName":"([^"]+)"', html)
print("visitor teams", names)
