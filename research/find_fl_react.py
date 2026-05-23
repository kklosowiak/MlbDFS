import re
import requests

html = requests.get(
    "https://www.fantasylabs.com/mlb/vegas/",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30,
).text
for key in ["reactAppsUrl", "sportId", "currentDate", "vegas"]:
    for m in re.finditer(key, html):
        print(html[max(0, m.start() - 30) : m.start() + 120])
