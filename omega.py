import subprocess
import sys
import os
import time
from utils.notifier import Notifier

def run_omega_pipeline():
    notifier = Notifier()
    
    print("\n" + "="*60)
    print("OMEGA v6.1: ACTIVE SLATE MASTER ACTIVATED")
    print("="*60)
    
    # Step 1: Market Intelligence Sync
    print("\n[SYNC]: Phase 1: Market Intelligence & Odds Ingestion...")
    try:
        subprocess.check_call([sys.executable, "run_fetch.py"])
    except subprocess.CalledProcessError:
        print("\nCRITICAL: Market Sync failed. Check API connectivity.")
        return

    # Step 2: Predictive Analysis & Dashboard Generation
    print("\n[ANALYSIS]: Phase 2: Applying Alpha Tiers & OMEGA Scoring...")
    try:
        subprocess.check_call([sys.executable, "main.py"])
    except subprocess.CalledProcessError:
        print("\nCRITICAL: Analysis Engine failed. Check data mappings.")
        return

    # Step 3: Remote Dashboard Relay
    print("\n[RELAY]: Phase 3: Pushing Dashboard to Telegram...")
    dashboard_path = os.path.join("reports", "dashboard.html")
    if notifier.send_document(dashboard_path, "📊 *OMEGA v6.1 Analysis Complete*"):
        print("SUCCESS: Dashboard sent to Telegram.")
    else:
        print("NOTICE: Telegram relay skipped or failed.")

    print("\n" + "="*60)
    print("OMEGA PIPELINE COMPLETE")
    print(f"VIEW DASHBOARD: {os.path.abspath('reports/dashboard.html')}")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_omega_pipeline()
