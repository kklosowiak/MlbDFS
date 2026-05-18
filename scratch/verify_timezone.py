from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

now_utc = datetime.now(timezone.utc)
now_et = now_utc.astimezone(ZoneInfo("America/New_York"))

print(f"Current UTC: {now_utc}")
print(f"Current ET:  {now_et}")

# Slate Rollover Logic
if now_et.hour < 4:
    base_date = (now_et - timedelta(days=1)).date()
else:
    base_date = now_et.date()

print(f"Calculated base date: {base_date}")
