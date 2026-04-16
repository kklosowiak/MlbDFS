from data.market_fetcher import MarketFetcher
from data.consensus_fetcher import ConsensusFetcher
from data.statcast_bridge import StatcastBridge
from data.probable_pitcher_fetcher import ProbablePitcherFetcher
import json
import os
import time
from datetime import datetime, timedelta, timezone
from config import config

def perform_fetch(custom_date_from=None):
    print("[INGEST]: Initiating OMEGA v3.2.1 Data Sync...")
    
    # OMEGA v6.5: Dynamic Probable Sync
    ProbablePitcherFetcher().refresh()
    
    fetcher = MarketFetcher()
    consensus = ConsensusFetcher()
    statcast = StatcastBridge()
    
    # 1. New V4 Bulk Ingestion (Odds + Props)
    # OMEGA v6.1: Dynamic Slate Isolation
    # Slates typically run from 04:00 UTC (Midnight ET) to the next day.
    now_utc = datetime.now(timezone.utc)
    if now_utc.hour < 4:
        # If running in the early morning before 4am UTC, we might still be looking at "today"
        # But usually, we want the current day's slate.
        base_date = now_utc.date()
    else:
        # If running after 4am UTC, we are targeting the next game window.
        base_date = now_utc.date()
        
    date_from = custom_date_from or f"{base_date}T04:00:00Z"
    date_to = (base_date + timedelta(days=1)).strftime("%Y-%m-%dT04:00:00Z")
    
    print(f"[INGEST]: Targeting Active Slate (Window: {date_from} to {date_to})")
    snapshot_path = fetcher.run_bulk_ingestion(date_from=date_from, date_to=date_to)

    
    if not snapshot_path or not os.path.exists(snapshot_path):
        print("  - CRITICAL: Market ingestion failed. Aborting.")
        return

    # 2. Fetch Betting Splits (Consensus)
    print("\n[STEP 2]: Fetching Betting Splits (Consensus Overlay)...")
    splits_data = consensus.fetch_splits()
    
    # 3. Merge splits into the snapshot
    print("[STEP 3]: Hard-linking Splits to Snapshot...")
    try:
        with open(snapshot_path, 'r') as f:
            full_data = json.load(f)
        
        full_data['splits'] = splits_data
        
        with open(snapshot_path, 'w') as f:
            json.dump(full_data, f, indent=4)
            
        print(f"\n[SUCCESS]: OMEGA v3.2.1 Ingestion Complete.")
        print(f"  - Final Snapshot: {os.path.basename(snapshot_path)}")
        
        # OMEGA v6.6 Cleanup: Auto-purge snapshots older than 48 hours
        print("\n[CLEANUP]: Pruning stale snapshots...")
        try:
            for f in os.listdir(config.DATA_DIR):
                if f.startswith("snapshot_") and f.endswith(".json"):
                    f_path = os.path.join(config.DATA_DIR, f)
                    f_time = os.path.getmtime(f_path)
                    if (time.time() - f_time) > (48 * 3600):
                        os.remove(f_path)
                        print(f"  - Removed: {f}")
        except: pass

    except Exception as e:
        print(f"  - ERROR: Failed to finalize snapshot. {e}")

    # 4. OMEGA v5.2: Auto-Refresh Statcast Momentum Cache (14-day rolling)
    print("\n[STEP 4]: Refreshing Statcast Momentum Cache...")
    try:
        bridge = StatcastBridge(config.DATA_DIR)
        bridge.refresh_momentum_data()
    except Exception as e:
        print(f"  - WARNING: Statcast refresh failed (non-critical): {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true", help="Run full ingestion audit")
    parser.add_argument("--main-slate", action="store_true", help="Filter for games starting 7:05 PM ET or later")
    args = parser.parse_args()
    
    if args.main_slate:
        # 7:05 PM ET is 23:05 UTC. OMEGA v6.1 Main Slate Isolation.
        now_utc = datetime.now(timezone.utc)
        main_slate_start = f"{now_utc.date()}T23:05:00Z"
        print(f"[SLATE]: ISOLATING MAIN SLATE (Starting {main_slate_start})...")
        perform_fetch(custom_date_from=main_slate_start)
    elif args.audit:
        print("[AUDIT]: Initiating Full Ingestion Clean Sweep...")
        perform_fetch()
        print("[AUDIT]: Sweep complete. Verify latest snapshot for coverage.")
    else:
        perform_fetch()


