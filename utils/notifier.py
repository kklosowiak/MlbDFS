import requests
import os
from config import config

class Notifier:
    def __init__(self):
        self.token = config.TELEGRAM_TOKEN
        self.chat_id = config.TELEGRAM_CHAT_ID
        self.base_url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        
    def send_message(self, text):
        """Sends a text message to the configured Telegram chat."""
        if not self.token or not self.chat_id:
            print(f"INFO: Telegram credentials missing. Skipping notification: {text}")
            return False
            
        payload = {
            'chat_id': self.chat_id,
            'text': text,
            'parse_mode': 'Markdown'
        }
        
        try:
            response = requests.post(self.base_url, data=payload)
            response.raise_for_status()
            return True
        except Exception as e:
            print(f"ERROR: Failed to send Telegram message: {e}")
            return False

    def send_document(self, file_path, caption=""):
        """Uploads a file (like dashboard.html) to the configured Telegram chat."""
        if not self.token or not self.chat_id:
            return False
            
        if not os.path.exists(file_path):
            print(f"ERROR: File not found for Telegram upload: {file_path}")
            return False
            
        url = f"https://api.telegram.org/bot{self.token}/sendDocument"
        try:
            with open(file_path, 'rb') as f:
                files = {'document': f}
                payload = {
                    'chat_id': self.chat_id, 
                    'caption': caption, 
                    'parse_mode': 'Markdown'
                }
                response = requests.post(url, data=payload, files=files)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"ERROR: Failed to send Telegram document: {e}")
            return False

    def push_god_tier_alert(self, team_data):
        """Sends a high-impact alert for Alpha scores > 80."""
        text = (
            f"\U0001f680 *GOD-TIER OMEGA ALERT* \U0001f680\n\n"
            f"\U0001f525 *Team*: {team_data['team']}\n"
            f"\U0001f4c8 *Alpha Score*: `{team_data['stack_score']}`\n"
            f"\U0001f464 *Opponent*: {team_data['opp_pitcher']}\n"
            f"\U0001f3af *ITT Move*: `{team_data['tt_move']}`\n"
            f"\U0001f4a8 *Weather*: {team_data['weather']}\n"
            f"\U0001f4ca *Public Ticket*: {team_data['public_bets']}%\n"
            f"\U0001f4b0 *Game Total*: {team_data['game_total']}\n\n"
            f"_[The OMEGA Engine - High Alpha Detection]_"
        )
        return self.send_message(text)

    def alert_scraper_failure(self, scraper_name: str, reason: str):
        """
        Fires a Telegram alert when a critical scraper fails silently
        (returns 0 results or raises an exception).
        Called automatically by run_fetch.py when zero-result detection fires.
        """
        from datetime import datetime, timezone
        ts = datetime.now(timezone.utc).strftime("%H:%M UTC")
        text = (
            f"\u26a0\ufe0f *OMEGA SCRAPER ALERT* \u26a0\ufe0f\n\n"
            f"*Scraper*: `{scraper_name}`\n"
            f"*Status*: FAILED / 0 results\n"
            f"*Reason*: {reason[:200]}\n"
            f"*Time*: {ts}\n\n"
            f"_Model is serving cached data. Check logs._"
        )
        return self.send_message(text)

if __name__ == "__main__":
    notifier = Notifier()
    notifier.send_message("*MLB DFS Sharps Engine*\nInfrastructure setup complete. Ready for real-time market signals.")
