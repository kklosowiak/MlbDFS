import re
import requests

url = "https://terminal.fantasylabs.com/vegas?sportId=3&date=05/22/2026"
html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
print("len", len(html))
for pat in [r"/api/[a-zA-Z0-9_./?=-]+", r"vegas[A-Za-z]*", r"opening[A-Za-z]*", r"Open[A-Za-z]*", r"sportevent[A-Za-z0-9_/]*"]:
    hits = sorted(set(re.findall(pat, html, re.I)))
    if hits:
        print(f"\n{pat} ({len(hits)})")
        for h in hits[:30]:
            print(" ", h)
# js bundle urls
for m in re.findall(r'https?://[^"\']+\.js[^"\']*', html):
    if "terminal" in m or "chunk" in m:
        print("JS", m[:120])
