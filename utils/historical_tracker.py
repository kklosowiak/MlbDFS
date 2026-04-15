import pandas as pd
import os
from datetime import datetime
from config import config

class HistoricalTracker:
    def __init__(self):
        self.log_file = os.path.join(config.LOG_DIR, "elite_signals_history.csv")
        self._initialize_log()
        
    def _initialize_log(self):
        """Creates the log file with headers if it doesn't exist."""
        if not os.path.exists(self.log_file):
            columns = [
                'timestamp', 'team', 'signal_type', 
                'ml_move', 'tt_move', 'public_bets_pct', 
                'k_prop', 'final_score', 'is_elite'
            ]
            df = pd.DataFrame(columns=columns)
            df.to_csv(self.log_file, index=False)
            print(f"Initialized historical log at {self.log_file}")

    def log_signal(self, team, signal_type, ml_move, tt_move, public_bets, k_prop, final_score, is_elite):
        """Logs a single signal event."""
        new_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'team': team,
            'signal_type': signal_type,
            'ml_move': ml_move,
            'tt_move': tt_move,
            'public_bets_pct': public_bets,
            'k_prop': k_prop,
            'final_score': final_score,
            'is_elite': is_elite
        }
        
        df = pd.read_csv(self.log_file)
        df = pd.concat([df, pd.DataFrame([new_entry])], ignore_index=True)
        df.to_csv(self.log_file, index=False)
        print(f"Logged {signal_type} signal for {team}.")

if __name__ == "__main__":
    tracker = HistoricalTracker()
    tracker.log_signal("CHC", "Hitter", 18, 0.5, 10, None, 100, True)
