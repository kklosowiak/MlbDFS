import re
import requests

url = "https://www.fantasylabs.com/vegas/js/vegas-dash.js?version=0.7.0138"
t = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
print("len", len(t))
for pat in ["open", "Open", "sportevent", "api/", "MLMoney", "OU"]:
    if pat.lower() in t.lower():
        pass
# lines containing open + money or opening
for line in t.split(";"):
    low = line.lower()
    if "open" in low and ("ml" in low or "ou" in low or "money" in low or "sport" in low):
        if len(line) < 200:
            print(line.strip()[:200])
# all api urls
apis = sorted(set(re.findall(r"['\"](/api/[^'\"]+)['\"]", t)))
for a in apis:
    print("API", a)
# sportevents patterns
for m in re.findall(r"sportevents[^'\"]{0,60}", t):
    print("SE", m)
