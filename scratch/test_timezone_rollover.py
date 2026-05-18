import sys
import os
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

# Add parent directory to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from run_fetch import get_slate_date

def run_tests():
    print("="*80)
    print("RUNNING TIMEZONE-AWARE SLATE ROLLOVER MOCK TESTS")
    print("="*80)

    # Test cases: tuples of (mocked_utc_datetime_string, expected_slate_date_string)
    test_cases = [
        # 1. Monday at 11:05 AM ET (15:05 UTC Monday) -> should resolve to Monday May 18
        ("2026-05-18T15:05:00+00:00", "2026-05-18"),
        
        # 2. Monday at 7:59 PM ET (23:59 UTC Monday) -> should resolve to Monday May 18
        ("2026-05-18T23:59:00+00:00", "2026-05-18"),
        
        # 3. Monday at 8:01 PM ET (00:01 UTC Tuesday) -> should resolve to Monday May 18 (BUG FIX: Previously rolled to Tuesday!)
        ("2026-05-19T00:01:00+00:00", "2026-05-18"),
        
        # 4. Monday at 11:05 PM ET (03:05 UTC Tuesday) -> should resolve to Monday May 18 (BUG FIX: Previously rolled to Tuesday!)
        ("2026-05-19T03:05:00+00:00", "2026-05-18"),
        
        # 5. Tuesday at 2:00 AM ET (06:00 UTC Tuesday) -> should resolve to Monday May 18 (Late games might be finishing)
        ("2026-05-19T06:00:00+00:00", "2026-05-18"),
        
        # 6. Tuesday at 3:59 AM ET (07:59 UTC Tuesday) -> should resolve to Monday May 18 (Very late / early morning)
        ("2026-05-19T07:59:00+00:00", "2026-05-18"),
        
        # 7. Tuesday at 4:01 AM ET (08:01 UTC Tuesday) -> should resolve to Tuesday May 19 (Rollover triggered!)
        ("2026-05-19T08:01:00+00:00", "2026-05-19"),
        
        # 8. Tuesday at 11:05 AM ET (15:05 UTC Tuesday) -> should resolve to Tuesday May 19
        ("2026-05-19T15:05:00+00:00", "2026-05-19"),
    ]

    failed = False
    for idx, (utc_str, expected_str) in enumerate(test_cases, 1):
        dt_utc = datetime.fromisoformat(utc_str)
        # Convert to ET to print local time context
        dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
        
        actual_date = get_slate_date(dt_utc)
        actual_str = actual_date.strftime("%Y-%m-%d")
        
        status = "PASS" if actual_str == expected_str else "FAIL"
        if status == "FAIL":
            failed = True
            
        print(f"Test {idx}:")
        print(f"  Mocked UTC time: {dt_utc} | Local ET time: {dt_et}")
        print(f"  Expected slate: {expected_str} | Actual slate: {actual_str} -> {status}")
        print("-"*80)

    if failed:
        print("RESULT: MOCK TESTS FAILED!")
        sys.exit(1)
    else:
        print("RESULT: ALL MOCK TESTS PASSED SUCCESSFULLY!")
        print("="*80)

if __name__ == "__main__":
    run_tests()
