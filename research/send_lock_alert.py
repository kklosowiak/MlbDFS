import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(r"c:\Users\konra\.gemini\antigravity\scratch\mlb_dfs_sharps_engine"))

from utils.notifier import Notifier
from data.market_fetcher import MarketFetcher

def send_final_alert():
    notifier = Notifier()
    
    with open(r"c:\Users\konra\.gemini\antigravity\scratch\mlb_dfs_sharps_engine\reports\latest_results.json", 'r') as f:
        data = json.load(f)
        
    p_top = data['pitchers'][0]
    t_top = data['teams'][0]
    h_top = data['hitters'][0]
    
    msg = (
        "🚨 *PRE-LOCK OMEGA UPDATE (3-GAME SLATE)* 🚨\n\n"
        f"💎 *Top Pitcher*: {p_top['pitcher']} (`{p_top['alpha_score']}`)\n"
        f"🔥 *Top Stack*: {t_top['team']} (`{t_top['stack_score']}`)\n"
        f"🎯 *Top Hitter*: {h_top['name']} (`{h_top['player_score']}`)\n\n"
        "✅ Dashboard refreshed with most recent market signals.\n"
        "📍 [View Dashboard v4.5](file:///c:/Users/konra/.gemini/antigravity/scratch/mlb_dfs_sharps_engine/reports/dashboard.html)\n\n"
        "_[Lock in 7 mins - Final Sentiment Converged]_"
    )
    
    success = notifier.send_message(msg)
    if success:
        print("Telegram alert sent successfully.")
    else:
        print("Failed to send Telegram alert.")

if __name__ == "__main__":
    send_final_alert()
