import time
import json
import os
import subprocess
import requests
from config import config
from utils.notifier import Notifier

class OMEGABot:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}"
        self.notifier = Notifier()
        self.offset = 0
        self.results_file = os.path.join(config.REPORTS_DIR, "latest_results.json")

    def get_updates(self):
        url = f"{self.base_url}/getUpdates?offset={self.offset}&timeout=30"
        try:
            resp = requests.get(url, timeout=35)
            data = resp.json()
            if data.get("ok"):
                return data.get("result", [])
        except Exception as e:
            print(f"Polling Error: {e}")
        return []

    def handle_command(self, cmd, chat_id):
        if str(chat_id) != str(self.chat_id):
            return "Unauthorized access. This bot is locked to the OMEGA admin."

        if cmd == "/start":
            return "🛸 *OMEGA Bot Active*\nCommands:\n/status - System Health\n/stacks - Top Team Stacks\n/pitchers - Top SP Alpha\n/dashboard - Send HTML Report\n/refresh - Trigger Live Sync & Analysis"

        if cmd == "/status":
            last_sync = "Unknown"
            if os.path.exists(self.results_file):
                last_sync = time.ctime(os.path.getmtime(self.results_file))
            return f"✅ *OMEGA STATUS*\nPipeline: Clean\nLast Analysis: {last_sync}\nMode: Production"

        if cmd == "/stacks":
            if not os.path.exists(self.results_file):
                return "❌ No results found. Run /refresh first."
            with open(self.results_file, 'r') as f:
                data = json.load(f)
            teams = data.get("teams", [])[:5]
            msg = "🔥 *TOP OMEGA STACKS*\n"
            for t in teams:
                weather = t.get('weather_label', 'Neutral')
                msg += f"• *{t['team']}* ({t['stack_score']})\n  └ {weather} | vs {t['opp_pitcher']}\n"
            return msg

        if cmd == "/pitchers":
            if not os.path.exists(self.results_file):
                return "❌ No results found. Run /refresh first."
            with open(self.results_file, 'r') as f:
                data = json.load(f)
            pitchers = data.get("pitchers", [])[:5]
            msg = "👤 *TOP SP ALPHA*\n"
            for p in pitchers:
                weather = p.get('weather_label', 'Neutral')
                ump = p.get('umpire_name', 'Unknown')
                msg += f"• *{p['pitcher']}* ({p['alpha_score']})\n  └ {weather} | Ump: {ump}\n"
            return msg

        if cmd == "/refresh" or cmd == "/run":
            self.notifier.send_message("🔄 *Step 1/2: Syncing Market Data...* (Fetching latest sharp splits & props)")
            try:
                # OMEGA v6.1: Full Pipeline Remote Control
                subprocess.run(["python", "run_fetch.py"], check=True)
                
                self.notifier.send_message("🧠 *Step 2/2: Analyzing Slate Intelligence...* (Applying OMEGA v6.1 Alpha Tiers)")
                subprocess.run(["python", "main.py"], check=True)
                
                # Fetch summary for the closure
                with open(self.results_file, 'r') as f:
                    data = json.load(f)
                
                top_teams = data.get("teams", [])[:5]
                top_pitchers = data.get("pitchers", [])[:5]
                top_hitters = data.get("hitters", [])[:5]
                
                msg = "✅ *OMEGA v6.1 ANALYSIS COMPLETE*\n\n"
                
                msg += "👤 *TOP 5 PITCHER ALPHA:*\n"
                for p in top_pitchers:
                    msg += f"• {p['pitcher']} ({p['alpha_score']})\n"
                
                msg += "\n🔥 *TOP 5 TEAM STACKS:*\n"
                for t in top_teams:
                    msg += f"• {t['team']} ({t['stack_score']}) {'🌪️' if t.get('is_storm') else ''}\n"
                    
                msg += "\n🎯 *TOP 5 HITTER ALPHA:*\n"
                for h in top_hitters:
                    msg += f"• {h['name']} ({h['score']}) {'♨️' if h.get('is_hot') else ''}\n"
                
                bottom = "\nDetailed Dashboard mirrored to production."
                return msg + bottom
            except Exception as e:
                return f"❌ Pipeline failed: {e}"

        if cmd == "/dashboard" or cmd == "/send":
            dashboard_path = os.path.join("reports", "dashboard.html")
            self.notifier.send_document(dashboard_path, "📊 *OMEGA v6.1 Interactive Dashboard*")
            return "📤 Dashboard dispatched."

        return "Unknown command. Try /start"

    def run(self):
        print("🤖 OMEGA Bot Polling Started...")
        while True:
            updates = self.get_updates()
            for update in updates:
                self.offset = update["update_id"] + 1
                if "message" in update and "text" in update["message"]:
                    text = update["message"]["text"]
                    chat_id = update["message"]["chat"]["id"]
                    response = self.handle_command(text, chat_id)
                    self.notifier.send_message(response)
            time.sleep(1)

if __name__ == "__main__":
    bot = OMEGABot()
    bot.run()
