import os
import requests
import json
from dotenv import load_dotenv

# Path to the .env file
env_path = r'C:\Users\konra\.gemini\antigravity\scratch\sports_agent\sports_agent\.env'
load_dotenv(env_path)

API_KEY = os.getenv("ODDS_API_KEY")
BASE_URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/odds"

def test_api_pull():
    print(f"--- OMEGA API Connection Check ---")
    if not API_KEY:
        print("❌ ERROR: No API Key found in .env")
        return

    params = {
        'apiKey': API_KEY,
        'regions': 'us',
        'markets': 'h2h,totals',
        'oddsFormat': 'american'
    }

    try:
        response = requests.get(BASE_URL, params=params)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            game_count = len(data)
            print(f"✅ SUCCESS: Pulled {game_count} MLB games successfully.")
            
            if game_count > 0:
                first_game = data[0]
                home = first_game.get('home_team')
                away = first_game.get('away_team')
                print(f"Sample Game: {away} @ {home}")
                
                # Check for bookmakers
                books = [b['key'] for b in first_game.get('bookmakers', [])]
                print(f"Active Books: {', '.join(books[:5])}...")
            
            # Print remaining quota if available in headers
            remaining = response.headers.get('x-requests-remaining')
            if remaining:
                print(f"API Quota Remaining: {remaining}")
                
        else:
            print(f"❌ ERROR: API returned status {response.status_code}")
            print(response.text)

    except Exception as e:
        print(f"❌ CONNECTION ERROR: {e}")

if __name__ == "__main__":
    test_api_pull()
