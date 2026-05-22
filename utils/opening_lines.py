"""
OMEGA opening-line storage: freeze daily opens at 4:30 AM capture;
backfill from earliest same-day snapshot when games appear later.
"""
import json
import os
from datetime import datetime

from config import config
from utils.market_utils import get_market_prices
from utils.slate_date import get_slate_date_iso

SNAPSHOT_SCAN_CAP = 30


def dated_opening_path(slate_date_iso=None):
    slate = slate_date_iso or get_slate_date_iso()
    return os.path.join(config.DATA_DIR, f"opening_lines_{slate}.json")


def legacy_opening_path():
    return os.path.join(config.DATA_DIR, "opening_lines.json")


def load_opening_lines_for_slate(slate_date_iso=None):
    """Prefer date-stamped opens; fall back to legacy file."""
    dated = dated_opening_path(slate_date_iso)
    if os.path.exists(dated):
        with open(dated, "r", encoding="utf-8") as f:
            return json.load(f)
    legacy = legacy_opening_path()
    if os.path.exists(legacy):
        with open(legacy, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def _pair_key(away_team, home_team):
    return f"{away_team}|{home_team}"


def _game_entry(g_id, game, away_ml, home_ml, total, source):
    away = game["away_team"]
    home = game["home_team"]
    return {
        "game_id": g_id,
        "pair_key": _pair_key(away, home),
        "team_away": away,
        "team_home": home,
        "away_opening_ml": away_ml,
        "away_current_ml": away_ml,
        "home_opening_ml": home_ml,
        "home_current_ml": home_ml,
        "opening_total": total,
        "current_total": total,
        "commence_time": game.get("commence_time"),
        "opening_source": source,
        "opening_captured_at": datetime.utcnow().isoformat() + "Z",
    }


def find_earliest_lines_from_snapshots(away_team, home_team, slate_date_iso=None):
    """
    Scan today's snapshot_*.json files (oldest first) for matching matchup lines.
    """
    slate = slate_date_iso or get_slate_date_iso()
    slate_compact = slate.replace("-", "")
    data_dir = config.DATA_DIR
    if not os.path.isdir(data_dir):
        return None

    files = [
        f
        for f in os.listdir(data_dir)
        if f.startswith(f"snapshot_{slate_compact}") and f.endswith(".json")
    ]
    files.sort()
    files = files[:SNAPSHOT_SCAN_CAP]

    for fname in files:
        path = os.path.join(data_dir, fname)
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            continue

        for game in data.get("odds", []):
            if game.get("away_team") != away_team or game.get("home_team") != home_team:
                continue

            away_ml, _ = get_market_prices(game, away_team)
            home_ml, total = get_market_prices(game, home_team)
            if away_ml is None or home_ml is None:
                continue

            return {
                "away_opening_ml": away_ml,
                "home_opening_ml": home_ml,
                "opening_total": total if total is not None else 8.5,
                "snapshot_file": fname,
            }

    return None


def load_manual_vegas_opens(slate_date_iso=None):
    """Optional override: data/vegas_opens_manual.json when automatic capture missed."""
    path = os.path.join(config.DATA_DIR, "vegas_opens_manual.json")
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return []
    slate = slate_date_iso or get_slate_date_iso()
    if data.get("slate_date") and data.get("slate_date") != slate:
        return []
    return data.get("games", [])


def apply_manual_vegas_opens(open_lookup, structured_odds, slate_date_iso=None):
    manuals = load_manual_vegas_opens(slate_date_iso)
    if not manuals:
        return 0

    manual_by_pair = {
        _pair_key(g["away"], g["home"]): g for g in manuals if g.get("away") and g.get("home")
    }
    applied = 0

    for g_id, game in structured_odds.items():
        away = game["away_team"]
        home = game["home_team"]
        manual = manual_by_pair.get(_pair_key(away, home))
        if not manual:
            continue

        if g_id not in open_lookup:
            away_ml, _ = get_market_prices(game, away)
            home_ml, total = get_market_prices(game, home)
            open_lookup[g_id] = _game_entry(
                g_id, game, away_ml or -110, home_ml or -110, total or 8.5, "vegas_manual"
            )
        else:
            row = open_lookup[g_id]
            # Only override when opens were not set by Odds API historical / snapshot
            src = str(row.get("opening_source", ""))
            if "odds_api_historical" in src or "snapshot_backfill" in src or "4:30_capture" in src:
                continue

        row = open_lookup[g_id]
        if manual.get("away_opening_ml") is not None:
            row["away_opening_ml"] = manual["away_opening_ml"]
        if manual.get("home_opening_ml") is not None:
            row["home_opening_ml"] = manual["home_opening_ml"]
        if manual.get("opening_total") is not None:
            row["opening_total"] = manual["opening_total"]
        row["opening_source"] = "vegas_manual"
        applied += 1

    if applied:
        print(f"  - [LINES]: Applied manual Vegas opens for {applied} game(s).")
    return applied


def persist_opening_db(open_lookup, slate_ids, slate_date_iso=None):
    dated = dated_opening_path(slate_date_iso)
    final_rows = [open_lookup[gid] for gid in slate_ids if gid in open_lookup]
    with open(dated, "w", encoding="utf-8") as f:
        json.dump(final_rows, f, indent=4)
    with open(legacy_opening_path(), "w", encoding="utf-8") as f:
        json.dump(final_rows, f, indent=4)
    return dated, len(final_rows)
