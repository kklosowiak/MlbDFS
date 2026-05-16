import requests
from datetime import datetime

def get_latest_scores():
    date = "2026-05-15"
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date}"
    response = requests.get(url)
    data = response.json()
    games = data.get('dates', [{}])[0].get('games', [])
    
    print(f"Latest Scores for {date}:")
    for game in games:
        away_team = game['teams']['away']['team']['name']
        away_score = game['teams']['away'].get('score', 0)
        home_team = game['teams']['home']['team']['name']
        home_score = game['teams']['home'].get('score', 0)
        status = game['status']['detailedState']
        print(f"{away_team} {away_score} @ {home_team} {home_score} ({status})")

if __name__ == "__main__":
    get_latest_scores()
