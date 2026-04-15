import os
import sys
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import config

def run_health_check():
    print("\n" + "="*50)
    print("      OMEGA v6.2.2 HEALTH & HOOKUP AUDIT")
    print("="*50)

    # 1. Environment Check
    print("\n[CHECK 1]: Environment Variables...")
    if config.validate():
        print("[OK] Environment variables validated.")
    else:
        print("[ERROR] CRITICAL: Missing environment variables.")

    # 2. Connectivity Check (The Odds API)
    print("\n[CHECK 2]: API Connectivity (The Odds API)...")
    import requests
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={config.ODDS_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        print(f"[OK] The Odds API: Active (Status {resp.status_code})")
    except Exception as e:
        print(f"[ERROR] The Odds API: FAILED. {e}")

    # 3. Telegram Bot Check
    print("\n[CHECK 3]: Telegram Bot Relay...")
    from utils.notifier import Notifier
    notifier = Notifier()
    if notifier.token and notifier.chat_id:
        print(f"[OK] Telegram Config: Hooked (Bot Token: {notifier.token[:5]}...)")
    else:
        print("[ERROR] Telegram Config: MISSING or INVALID.")

    # 4. Data Directory Check
    print("\n[CHECK 4]: Local Persistence...")
    required_dirs = [config.DATA_DIR, config.LOG_DIR, config.REPORTS_DIR]
    for d in required_dirs:
        if os.path.exists(d):
            print(f"[OK] Directory Found: {os.path.basename(d)}")
        else:
            print(f"[WARNING] Missing Directory: {os.path.basename(d)} (Creating...)")
            os.makedirs(d, exist_ok=True)

    # 5. Opening Lines Check
    print("\n[CHECK 5]: Opening Lines Sync...")
    opening_path = os.path.join(config.DATA_DIR, "opening_lines.json")
    if os.path.exists(opening_path):
        try:
            with open(opening_path, 'r') as f:
                data = json.load(f)
            print(f"[OK] Opening Lines: Loaded ({len(data)} entries found).")
        except:
            print("[ERROR] Opening Lines: File corrupted.")
    else:
        print("[WARNING] Opening Lines: Missing. Engine will lack 'Laggard' detection.")

    print("\n" + "="*50)
    print("      AUDIT COMPLETE")
    print("="*50 + "\n")

if __name__ == "__main__":
    run_health_check()
