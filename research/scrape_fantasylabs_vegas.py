"""Probe FantasyLabs Vegas page for API endpoints and scrape opens."""
import json
import re
import sys
from datetime import datetime

import requests

URL = "https://www.fantasylabs.com/mlb/vegas/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/json",
}

# MLB abbrev -> OMEGA full names (Odds API style)
ABBREV_TO_FULL = {
    "ARI": "Arizona Diamondbacks",
    "ATL": "Atlanta Braves",
    "BAL": "Baltimore Orioles",
    "BOS": "Boston Red Sox",
    "CHC": "Chicago Cubs",
    "CHW": "Chicago White Sox",
    "CIN": "Cincinnati Reds",
    "CLE": "Cleveland Guardians",
    "COL": "Colorado Rockies",
    "DET": "Detroit Tigers",
    "HOU": "Houston Astros",
    "KC": "Kansas City Royals",
    "LAA": "Los Angeles Angels",
    "LAD": "Los Angeles Dodgers",
    "MIA": "Miami Marlins",
    "MIL": "Milwaukee Brewers",
    "MIN": "Minnesota Twins",
    "NYM": "New York Mets",
    "NYY": "New York Yankees",
    "OAK": "Athletics",
    "ATH": "Athletics",
    "PHI": "Philadelphia Phillies",
    "PIT": "Pittsburgh Pirates",
    "SD": "San Diego Padres",
    "SEA": "Seattle Mariners",
    "SF": "San Francisco Giants",
    "STL": "St. Louis Cardinals",
    "TB": "Tampa Bay Rays",
    "TEX": "Texas Rangers",
    "TOR": "Toronto Blue Jays",
    "WSH": "Washington Nationals",
}


def probe_page():
    r = requests.get(URL, headers=HEADERS, timeout=30)
    r.raise_for_status()
    text = r.text
    print(f"HTML length: {len(text)}")
    for m in re.findall(r'src="([^"]+)"', text):
        if any(k in m.lower() for k in ("vegas", "mlb", "angular", "app/")):
            print("script:", m)
    if "VegasController" in text:
        idx = text.index("VegasController")
        print("VegasController context:", text[max(0, idx - 200) : idx + 400])
    for pat in [
        r"/api/[a-zA-Z0-9_/\-]+",
        r"fantasylabs\.com/[a-zA-Z0-9_/\-]+",
        r"Vegas[A-Za-z]*",
        r"vegas[A-Za-z]*",
    ]:
        hits = sorted(set(re.findall(pat, text, re.I)))
        if hits:
            print(f"\n--- {pat} ({len(hits)}) ---")
            for h in hits[:40]:
                print(h)


def try_api_candidates(slate_date: str):
    bases = [
        "https://www.fantasylabs.com/api/mlb/vegas",
        "https://www.fantasylabs.com/api/vegas/mlb",
        "https://api.fantasylabs.com/mlb/vegas",
        "https://www.fantasylabs.com/mlb/api/vegas",
    ]
    params_variants = [
        {},
        {"date": slate_date},
        {"slateDate": slate_date},
    ]
    for base in bases:
        for params in params_variants:
            try:
                resp = requests.get(base, headers=HEADERS, params=params, timeout=15)
                if resp.status_code == 200 and resp.text and resp.text[0] in "[{":
                    print(f"OK {base} {params} -> {len(resp.text)} bytes")
                    print(resp.text[:500])
            except Exception as e:
                pass


if __name__ == "__main__":
    probe_page()
    slate = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime("%Y-%m-%d")
    try_api_candidates(slate)
