import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    ODDS_API_KEY = os.getenv("ODDS_API_KEY")
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
    
    # Engine Settings
    SHARP_WEIGHT_THRESHOLD = 0.05  # 5% movement threshold
    DEFAULT_SLATE_SIZE = 10
    
    # OMEGA Shadow Market Settings (v6.15)
    # Including global sharp books to catch early prop movements
    BOOKMAKERS = "draftkings,fanduel,betmgm,caesars,pinnacle,betonlineag,bovada"
    REGIONS = "us,eu"
    
    # Path Settings
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    LOG_DIR = os.path.join(BASE_DIR, "logs")
    REPORTS_DIR = os.path.join(BASE_DIR, "reports")
    
    # OMEGA v5 Stadium Alpha (Park Factors: Runs/HR Multiplier)
    PARK_FACTORS = {
        'Arizona Diamondbacks': 0.98, 'Atlanta Braves': 1.02, 'Baltimore Orioles': 1.01,
        'Boston Red Sox': 1.05, 'Chicago Cubs': 1.02, 'Chicago White Sox': 0.99,
        'Cincinnati Reds': 1.10, 'Cleveland Guardians': 0.98, 'Colorado Rockies': 1.15,
        'Detroit Tigers': 0.97, 'Houston Astros': 0.98, 'Kansas City Royals': 1.02,
        'Los Angeles Angels': 0.99, 'Los Angeles Dodgers': 1.03, 'Miami Marlins': 0.95,
        'Milwaukee Brewers': 1.01, 'Minnesota Twins': 0.99, 'New York Mets': 0.96,
        'New York Yankees': 1.02, 'Oakland Athletics': 0.95, 'Philadelphia Phillies': 1.03,
        'Pittsburgh Pirates': 0.97, 'San Diego Padres': 0.94, 'San Francisco Giants': 0.95,
        'Seattle Mariners': 0.92, 'St. Louis Cardinals': 0.98, 'Tampa Bay Rays': 0.96,
        'Texas Rangers': 1.04, 'Toronto Blue Jays': 1.01, 'Washington Nationals': 1.00
    }
    
    @classmethod
    def get_slate_filter(cls):
        """OMEGA v6.9: Load Date-Aware Slate Filter."""
        import json
        from datetime import datetime
        filter_path = os.path.join(cls.DATA_DIR, "slate_filter.json")
        if os.path.exists(filter_path):
            try:
                with open(filter_path, 'r') as f:
                    data = json.load(f)
                
                today = datetime.now().strftime("%Y-%m-%d")
                if data.get('enabled') and data.get('active_date') == today:
                    return data.get('allowed_teams', [])
            except: pass
        return None

    @classmethod
    def validate(cls):
        """Ensure required keys are present. ODDS_API_KEY is mandatory for ingestion."""
        missing = []
        if not cls.ODDS_API_KEY:
            missing.append("ODDS_API_KEY")
        if missing:
            print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
            return False
        return True

config = Config()
