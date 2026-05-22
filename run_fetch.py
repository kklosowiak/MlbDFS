from data.market_fetcher import MarketFetcher
from data.consensus_fetcher import ConsensusFetcher
from data.statcast_bridge import StatcastBridge
from data.probable_pitcher_fetcher import ProbablePitcherFetcher
from data.propfinder_scraper import PropfinderScraper
import json
import os
import time
from datetime import datetime, timedelta, timezone
from config import config

def get_slate_date(dt_utc=None):
    """OMEGA v9.4: Timezone-aware DFS slate rollover (4:00 AM US/Eastern Time)"""
    if dt_utc is None:
        dt_utc = datetime.now(timezone.utc)
    try:
        from zoneinfo import ZoneInfo
        dt_et = dt_utc.astimezone(ZoneInfo("America/New_York"))
    except Exception:
        # Fallback to -4 offset (EDT) or -5 (EST). May 18 is EDT (UTC-4)
        dt_et = dt_utc - timedelta(hours=4)
        
    if dt_et.hour < 4:
        return (dt_et - timedelta(days=1)).date()
    else:
        return dt_et.date()

def perform_fetch(custom_date_from=None, capture_opening=False):
    print("[INGEST]: Initiating OMEGA v3.2.1 Data Sync...")
    
    # OMEGA v6.6.5: Live Weather Overlay Sync
    try:
        PropfinderScraper().refresh()
    except Exception as e:
        print(f"  - WARNING: Weather refresh failed: {e}")
    
    # OMEGA v6.5: Dynamic Probable Sync
    ProbablePitcherFetcher().refresh()
    
    fetcher = MarketFetcher()
    consensus = ConsensusFetcher()
    statcast = StatcastBridge()
    
    # 1. New V4 Bulk Ingestion (Odds + Props)
    # OMEGA v9.4: Dynamic Slate Isolation (Timezone-Aware)
    base_date = get_slate_date()
        
    date_from = custom_date_from or f"{base_date}T04:00:00Z"
    date_to = (base_date + timedelta(days=1)).strftime("%Y-%m-%dT04:00:00Z")
    
    print(f"[INGEST]: Targeting Active Slate (Window: {date_from} to {date_to})")
    snapshot_path = fetcher.run_bulk_ingestion(
        date_from=date_from, date_to=date_to, capture_opening=capture_opening
    )

    
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

        # Savant season xwOBA (once per slate day — safe with hourly MLB refresh)
        bridge.refresh_statcast_xwoba(season=2026)
        
        # v10.2: Refresh Pitcher Recent Form Cache
        bridge.refresh_pitcher_form_cache()
    except Exception as e:
        print(f"  - WARNING: Statcast refresh failed (non-critical): {e}")

    # 5. OMEGA v9.5: Platoon Splits Cache Refresh
    print("\n[STEP 5]: Refreshing Platoon Splits Cache...")
    try:
        from data.platoon_fetcher import PlatoonFetcher
        platoon = PlatoonFetcher(config.DATA_DIR)
        platoon.fetch_platoon_data()
    except Exception as e:
        print(f"  - WARNING: Platoon splits refresh failed (non-critical): {e}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", action="store_true", help="Run full ingestion audit")
    parser.add_argument("--main-slate", action="store_true", help="Filter for games starting 7:05 PM ET or later")
    args = parser.parse_args()
    
    if args.main_slate:
        # 7:05 PM ET is 23:05 UTC. OMEGA v6.1 Main Slate Isolation.
        base_date = get_slate_date()
        main_slate_start = f"{base_date}T23:05:00Z"
        print(f"[SLATE]: ISOLATING MAIN SLATE (Starting {main_slate_start})...")
        perform_fetch(custom_date_from=main_slate_start)
    elif args.audit:
        print("[AUDIT]: Initiating Full Ingestion Clean Sweep...")
        perform_fetch()
        print("[AUDIT]: Sweep complete. Verify latest snapshot for coverage.")
    else:
        perform_fetch()


