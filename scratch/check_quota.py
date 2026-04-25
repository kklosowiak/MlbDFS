import requests
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("ODDS_API_KEY")

if not api_key:
    print("Error: ODDS_API_KEY not found in .env")
else:
    url = f"https://api.the-odds-api.com/v4/sports/?apiKey={api_key}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        remaining = response.headers.get("x-requests-remaining")
        used = response.headers.get("x-requests-used")
        print(f"Requests remaining: {remaining}")
        print(f"Requests used: {used}")
    except Exception as e:
        print(f"Error checking status: {e}")
