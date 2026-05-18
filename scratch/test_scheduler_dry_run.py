import datetime
import time
import os
import sys

# Add root project path to import server.py
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from server import get_eastern_time

print("="*60)
print("OMEGA SCHEDULER DIAGNOSTIC DRY-RUN")
print("="*60)

# Test 1: Timezone conversions
print("[TEST 1]: Timezone conversions & DST validation")
utc_now = datetime.datetime.now(datetime.timezone.utc)
try:
    from zoneinfo import ZoneInfo
    et_now = utc_now.astimezone(ZoneInfo("America/New_York"))
    print(f"  - Using zoneinfo.ZoneInfo: {et_now} (Hour: {et_now.hour})")
except Exception as e:
    print(f"  - zoneinfo failed: {e}")
    et_now = utc_now - datetime.timedelta(hours=4)
    print(f"  - Using fallback (-4 offset): {et_now} (Hour: {et_now.hour})")

# Test 2: Helper get_eastern_time
naive_now = datetime.datetime.now()
et_helper = get_eastern_time(naive_now)
print(f"  - get_eastern_time helper output: {et_helper}")

# Test 3: Hour Key Calculation
current_hour_key = et_now.strftime("%Y-%m-%d %H")
print(f"[TEST 2]: Hour Key Calculation")
print(f"  - current_hour_key: '{current_hour_key}'")

# Test 4: Startup loading from latest_results.json
print("[TEST 3]: Checking results file mapping")
results_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "reports", "latest_results.json"))
if os.path.exists(results_path):
    print(f"  - latest_results.json exists at: {results_path}")
    import json
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            cached_data = json.load(f)
        cached_ts = cached_data.get("timestamp")
        print(f"  - Raw cached timestamp: {cached_ts}")
        if cached_ts and "T" in cached_ts:
            dt = datetime.datetime.fromisoformat(cached_ts)
            dt_et = get_eastern_time(dt)
            last_key = dt_et.strftime("%Y-%m-%d %H")
            print(f"  - Mapped last_scheduled_hour_key: '{last_key}'")
            if last_key == current_hour_key:
                print("  - MATCH! The server will wait for the next hour.")
            else:
                print("  - NO MATCH! A catch-up run will trigger on startup.")
    except Exception as err:
        print(f"  - Error parsing: {err}")
else:
    print("  - reports/latest_results.json not found.")

print("="*60)
print("DIAGNOSTIC COMPLETED SUCCESSFULLY")
print("="*60)
