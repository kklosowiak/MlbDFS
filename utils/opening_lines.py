"""
OMEGA opening-line storage: freeze daily opens at 4:30 AM capture;
backfill from earliest same-day snapshot when games appear later.
"""
import json
import os
from datetime import datetime, UTC

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


def _game_entry(g_id, game, away_ml, home_ml, total, source, away_tt_open=None, away_tt_live=None, home_tt_open=None, home_tt_live=None):
    away = game["away_team"]
    home = game["home_team"]
    
    from utils.market_utils import get_bookmaker_total
    pin_tot = get_bookmaker_total(game, "pinnacle")
    dk_tot = get_bookmaker_total(game, "draftkings")
    fd_tot = get_bookmaker_total(game, "fanduel")
    circa_tot = get_bookmaker_total(game, "circa")
    
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
        "pinnacle_total": pin_tot if pin_tot is not None else total,
        "draftkings_total": dk_tot if dk_tot is not None else total,
        "fanduel_total": fd_tot if fd_tot is not None else total,
        "circa_total": circa_tot if circa_tot is not None else total,
        "commence_time": game.get("commence_time"),
        "opening_source": source,
        "opening_captured_at": datetime.now(UTC).replace(tzinfo=None).isoformat() + "Z",
        "away_tt_open": away_tt_open,
        "away_tt_live": away_tt_live,
        "home_tt_open": home_tt_open,
        "home_tt_live": home_tt_live
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


def sync_fantasylabs_vegas_opens(slate_date_iso=None):
    """Pull true FL opening ML/totals into vegas_opens_manual.json (no paste)."""
    try:
        from data.fantasylabs_vegas_fetcher import write_manual_opens
        return write_manual_opens(slate_date_iso)
    except Exception as e:
        print(f"  - [LINES WARNING]: FantasyLabs Vegas sync failed: {e}")
        return None


def _has_odds_api_open(row):
    src = str(row.get("opening_source", ""))
    return (
        "odds_api_historical" in src
        or "snapshot_backfill" in src
        or "4:30_capture" in src
    )


def apply_manual_vegas_opens(open_lookup, structured_odds, slate_date_iso=None):
    """FantasyLabs backup only — fills games missing Odds API / snapshot opens, and enriches all with team totals."""
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

        row = open_lookup.get(g_id)
        
        # Enrichment: always copy team totals if available in manual opens
        if row:
            if manual.get("away_tt_open") is not None:
                row["away_tt_open"] = manual["away_tt_open"]
            if manual.get("away_tt_live") is not None:
                row["away_tt_live"] = manual["away_tt_live"]
            if manual.get("home_tt_open") is not None:
                row["home_tt_open"] = manual["home_tt_open"]
            if manual.get("home_tt_live") is not None:
                row["home_tt_live"] = manual["home_tt_live"]

        if row and _has_odds_api_open(row):
            continue

        away_ml, _ = get_market_prices(game, away)
        home_ml, total = get_market_prices(game, home)

        if g_id not in open_lookup:
            open_lookup[g_id] = _game_entry(
                g_id,
                game,
                manual.get("away_opening_ml") or away_ml or -110,
                manual.get("home_opening_ml") or home_ml or -110,
                manual.get("opening_total") or total or 8.5,
                "fantasylabs_vegas_fallback",
                away_tt_open=manual.get("away_tt_open"),
                away_tt_live=manual.get("away_tt_live"),
                home_tt_open=manual.get("home_tt_open"),
                home_tt_live=manual.get("home_tt_live")
            )
        else:
            row = open_lookup[g_id]
            if manual.get("away_opening_ml") is not None:
                row["away_opening_ml"] = manual["away_opening_ml"]
            if manual.get("home_opening_ml") is not None:
                row["home_opening_ml"] = manual["home_opening_ml"]
            if manual.get("opening_total") is not None:
                row["opening_total"] = manual["opening_total"]
            row["opening_source"] = "fantasylabs_vegas_fallback"

        row = open_lookup[g_id]
        row["away_current_ml"] = away_ml if away_ml is not None else row.get("away_current_ml")
        row["home_current_ml"] = home_ml if home_ml is not None else row.get("home_current_ml")
        row["current_total"] = total if total is not None else row.get("current_total")
        applied += 1

    if applied:
        print(f"  - [LINES]: FantasyLabs fallback opens/enrichment applied for {applied} game(s).")
    return applied


def persist_opening_db(open_lookup, slate_ids, slate_date_iso=None):
    dated = dated_opening_path(slate_date_iso)
    final_rows = [open_lookup[gid] for gid in slate_ids if gid in open_lookup]
    with open(dated, "w", encoding="utf-8") as f:
        json.dump(final_rows, f, indent=4)
    with open(legacy_opening_path(), "w", encoding="utf-8") as f:
        json.dump(final_rows, f, indent=4)
    return dated, len(final_rows)
