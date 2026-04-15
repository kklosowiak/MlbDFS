import os
import requests
import json
from dotenv import load_dotenv

env_path = r'C:\Users\konra\.gemini\antigravity\scratch\sports_agent\sports_agent\.env'
load_dotenv(env_path)

API_KEY = os.getenv("ODDS_API_KEY")
URL = "https://api.the-odds-api.com/v4/sports/baseball_mlb/events"

def inspect_events():
    params = {'apiKey': API_KEY}
    r = requests.get(URL, params=params)
    if r.status_code == 200:
        data = r.json()
        if data:
            print(json.dumps(data[0], indent=2))
        else:
            print("No events found.")
    else:
        print(f"Error: {r.status_code}")

if __name__ == "__main__":
    inspect_events()
