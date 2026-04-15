import time
import json
import os
import subprocess
from data.market_fetcher import MarketFetcher
from utils.notifier import Notifier
from config import config

class PropSentry:
    def __init__(self, poll_interval_minutes=10):
        self.fetcher = MarketFetcher()
        self.notifier = Notifier()
        self.poll_interval = poll_interval_minutes * 60
        self.is_active = True
        
    def announce_start(self):
        msg = (
            "🛸 *OMEGA PROP SENTRY ONLINE*\n"
            "Monitoring for K-Props, Outs, and Total Bases for the 12:10 PM ET Slate.\n"
            "📍 Status: *POLLING ACTIVE* (10m Interval)"
        )
        print("[SENTRY]: OMEGA PROP SENTRY ONLINE (Polling 10m Interval)")
        self.notifier.send_message(msg)

    def run_cycle(self):
        print(f"\n[SENTRY]: Cycle started at {time.ctime()}")
        
        # 1. Trigger Ingestion
        snapshot_path = self.fetcher.run_bulk_ingestion()
        if not snapshot_path:
            print("  - [SENTRY]: Ingestion failed. Retrying next cycle.")
            return False

        # 2. Check Player Prop Count
        with open(snapshot_path, 'r') as f:
            snapshot = json.load(f)
            
        metadata = snapshot.get('metadata', {})
        player_count = metadata.get('processed_players', 0)
        
        print(f"  - [SENTRY]: Processed {player_count} players.")
        
        if player_count > 0:
            print("  - [SENTRY]: PROPS DETECTED! Triggering OMEGA Analysis...")
            self.notifier.send_message(f"🎯 *OMEGA PROP ALERT*: {player_count} players ingested. Triggering high-fidelity analysis...")
            
            # 3. Trigger Full Analysis
            try:
                subprocess.run(["python", "main.py"], check=True)
                self.notifier.send_message("✅ *ANALYSIS COMPLETE*: v4.5 Sentiment Dashboard updated with full Probable/Prop coverage.")
                return True # Stop after successful discovery if desired, or keep polling
            except Exception as e:
                self.notifier.send_message(f"❌ *ANALYSIS ERROR*: {e}")
                return False
        else:
            print(f"  - [SENTRY]: No props found. Waiting {self.poll_interval/60:.0f} minutes...")
            return False

    def start(self):
        self.announce_start()
        try:
            while self.is_active:
                found = self.run_cycle()
                if found:
                    print("[SENTRY]: Mission Success. Continuing to monitor for late-opening markets...")
                    # We continue monitoring in case more props open for later games
                
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[SENTRY]: Shutdown command received. Offline.")

if __name__ == "__main__":
    sentry = PropSentry(poll_interval_minutes=10)
    sentry.start()
