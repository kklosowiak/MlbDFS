"""
Fetch FantasyLabs Vegas OPEN lines (no login required).

Source: public SSR payload on terminal.fantasylabs.com/vegas
Fields: homeGameMoneylineOpen, visitorGameMoneylineOpen, homeGameOUOpen
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

import requests

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from config import config
from utils.slate_date import get_slate_date_iso

SPORT_ID_MLB = 3
TERMINAL_BASE = "https://terminal.fantasylabs.com/vegas"
MANUAL_PATH = os.path.join(config.DATA_DIR, "vegas_opens_manual.json")


def _slate_to_fl_date(slate_date_iso: str) -> str:
    """2026-05-22 -> 05/22/2026"""
    y, m, d = slate_date_iso.split("-")
    return f"{m}/{d}/{y}"


def _extract_int(blob: str, key: str):
    m = re.search(rf'\\"{re.escape(key)}\\":(-?\d+)', blob)
    return int(m.group(1)) if m else None


def _extract_float(blob: str, key: str):
    m = re.search(rf'\\"{re.escape(key)}\\":([\d.]+)', blob)
    return float(m.group(1)) if m else None


def _extract_str(blob: str, key: str):
    m = re.search(rf'\\"{re.escape(key)}\\":\\"([^\\"]*)\\"', blob)
    return m.group(1) if m else None


def fetch_vegas_opens(slate_date_iso: str | None = None) -> list[dict]:
    slate = slate_date_iso or get_slate_date_iso()
    fl_date = _slate_to_fl_date(slate)
    url = f"{TERMINAL_BASE}?sportId={SPORT_ID_MLB}&date={fl_date}"
    resp = requests.get(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        timeout=45,
    )
    resp.raise_for_status()
    html = resp.text

    # Each vegasProperties row contains eventId + open/current ML/OU
    chunks = re.split(r'\\"eventId\\":\d+', html)
    games = []
    seen = set()

    for chunk in chunks:
        away = _extract_str(chunk, "visitorTeam")
        home = _extract_str(chunk, "homeTeam")
        if not away or not home:
            continue

        away_ml = _extract_int(chunk, "visitorGameMoneylineOpen")
        home_ml = _extract_int(chunk, "homeGameMoneylineOpen")
        ou = _extract_float(chunk, "homeGameOUOpen") or _extract_float(
            chunk, "visitorGameOUOpen"
        )
        if away_ml is None or home_ml is None:
            continue

        pair = (away, home)
        if pair in seen:
            continue
        seen.add(pair)

        games.append(
            {
                "away": away,
                "home": home,
                "away_opening_ml": away_ml,
                "home_opening_ml": home_ml,
                "opening_total": ou if ou is not None else 8.5,
            }
        )

    return games


def write_manual_opens(slate_date_iso: str | None = None) -> str:
    slate = slate_date_iso or get_slate_date_iso()
    games = fetch_vegas_opens(slate)
    if not games:
        raise RuntimeError(f"FantasyLabs Vegas scrape returned 0 games for {slate}")

    payload = {
        "slate_date": slate,
        "source": "FantasyLabs terminal.fantasylabs.com/vegas (auto)",
        "fetched_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "games": games,
    }
    with open(MANUAL_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return MANUAL_PATH


if __name__ == "__main__":
    path = write_manual_opens()
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    print(f"Wrote {len(data['games'])} games to {path}")
    for g in data["games"]:
        print(
            f"  {g['away']} @ {g['home']}: "
            f"{g['away_opening_ml']}/{g['home_opening_ml']} O/U {g['opening_total']}"
        )
