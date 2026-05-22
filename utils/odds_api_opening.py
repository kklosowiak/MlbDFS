"""
Opening lines via The Odds API Historical endpoint (paid plan).

Uses the closest snapshot at or before 4:30 AM US/Eastern on the slate date.
One request per slate day (~20 quota credits for us + h2h + totals + draftkings).
"""
from datetime import datetime, time, timezone

import requests

from config import config
from utils.market_utils import get_market_prices
from utils.opening_lines import _pair_key
from utils.slate_date import get_slate_date

HISTORICAL_URL = "https://api.the-odds-api.com/v4/historical/sports/baseball_mlb/odds"
OPEN_BOOK = "draftkings"
OPEN_REGIONS = "us"
OPEN_MARKETS = "h2h,totals"


def opening_capture_time_utc(slate_date_iso: str) -> datetime:
    """4:30 AM US/Eastern on slate date -> UTC aware datetime."""
    try:
        from zoneinfo import ZoneInfo
        et = ZoneInfo("America/New_York")
    except Exception:
        et = timezone.utc

    y, m, d = (int(x) for x in slate_date_iso.split("-"))
    local = datetime(y, m, d, 4, 30, 0, tzinfo=et)
    return local.astimezone(timezone.utc)


def fetch_historical_opens(slate_date_iso: str | None = None) -> dict[str, dict]:
    """
    Returns pair_key -> {away_opening_ml, home_opening_ml, opening_total, team_away, team_home, source}.
    """
    if not config.ODDS_API_KEY:
        raise RuntimeError("ODDS_API_KEY missing")

    slate = slate_date_iso or get_slate_date().isoformat()
    capture_utc = opening_capture_time_utc(slate)
    date_param = capture_utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    params = {
        "apiKey": config.ODDS_API_KEY,
        "regions": OPEN_REGIONS,
        "markets": OPEN_MARKETS,
        "oddsFormat": "american",
        "date": date_param,
        "bookmakers": OPEN_BOOK,
    }

    resp = requests.get(HISTORICAL_URL, params=params, timeout=45)
    resp.raise_for_status()

    payload = resp.json()
    snapshot_ts = payload.get("timestamp", date_param)
    games = payload.get("data") or []

    remaining = resp.headers.get("x-requests-remaining")
    last_cost = resp.headers.get("x-requests-last")
    print(
        f"  - [LINES]: Odds API historical snapshot {snapshot_ts} "
        f"({len(games)} games, cost {last_cost}, remaining {remaining})"
    )

    by_pair: dict[str, dict] = {}
    for game in games:
        away = game.get("away_team")
        home = game.get("home_team")
        if not away or not home:
            continue

        away_ml, _ = get_market_prices(game, away)
        home_ml, total = get_market_prices(game, home)
        if away_ml is None or home_ml is None:
            continue
        if total is None:
            total = 8.5

        pk = _pair_key(away, home)
        by_pair[pk] = {
            "team_away": away,
            "team_home": home,
            "pair_key": pk,
            "away_opening_ml": away_ml,
            "home_opening_ml": home_ml,
            "opening_total": total,
            "opening_source": f"odds_api_historical:{snapshot_ts}",
        }

    return by_pair
