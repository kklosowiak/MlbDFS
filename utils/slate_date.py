"""OMEGA slate date helpers (4:00 AM US/Eastern rollover)."""
from datetime import datetime, timedelta, timezone


def get_slate_date(dt_utc=None):
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        dt_et = dt_utc - timedelta(hours=4)

    if dt_et.hour < 4:
        return (dt_et - timedelta(days=1)).date()
    return dt_et.date()


def get_slate_date_iso(dt_utc=None):
    return get_slate_date(dt_utc).isoformat()
