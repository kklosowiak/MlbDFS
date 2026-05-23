import re
import requests

h = requests.get(
    "https://terminal.fantasylabs.com/vegas?sportId=3&date=05/22/2026",
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=30,
).text

# HTML embeds escaped JSON: \"field\"
pat = re.compile(
    r'\\"visitorTeam\\":\\"([^\\]+)\\",\\"homeTeam\\":\\"([^\\]+)\\".*?'
    r'\\"visitorTeamShort\\":\\"([^\\]+)\\".*?\\"homeTeamShort\\":\\"([^\\]+)\\".*?'
    r'\\"homeGameMoneylineOpen\\":(-?\d+).*?'
    r'\\"visitorGameMoneylineOpen\\":(-?\d+).*?'
    r'\\"homeGameOUOpen\\":([\d.]+).*?'
    r'\\"visitorGameOUOpen\\":([\d.]+)',
    re.DOTALL,
)

games = []
for m in pat.finditer(h):
    games.append(
        {
            "visitor": m.group(1),
            "home": m.group(2),
            "vshort": m.group(3),
            "hshort": m.group(4),
            "home_ml_open": int(m.group(5)),
            "away_ml_open": int(m.group(6)),
            "home_ou": float(m.group(7)),
            "away_ou": float(m.group(8)),
        }
    )

print("matched", len(games))
for g in games[:5]:
    print(g)

# PHI game
for g in games:
    if "Phillies" in g["home"] or "Phillies" in g["visitor"]:
        print("PHI", g)
