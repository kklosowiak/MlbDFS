import json
import re
import requests

url = "https://terminal.fantasylabs.com/vegas?sportId=3&date=05/22/2026"
html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text

# __NEXT_DATA__ or similar
for marker in ["__NEXT_DATA__", "__NUXT__", "window.__", "VegasRunsOpen", "sportevents"]:
    if marker in html:
        print("found marker:", marker)

idx = html.find("VegasRunsOpen")
if idx >= 0:
    print("context:", html[idx : idx + 500])

# try next.js data
m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.S)
if m:
    data = json.loads(m.group(1))
    print("NEXT keys", data.keys())
    print(json.dumps(data, indent=2)[:3000])

# search for sportevents in html
for m in re.finditer(r"sportevents", html, re.I):
    print(html[m.start() - 50 : m.start() + 100])
    break

# large json blobs
for m in re.finditer(r'\{["\']sportId["\']', html):
    start = m.start()
    snippet = html[start : start + 200]
    print("json blob start:", snippet[:200])
