import urllib.request
import json

def get_game_data(game_pk):
    url = f'https://statsapi.mlb.com/api/v1/game/{game_pk}/boxscore'
    try:
        resp = urllib.request.urlopen(url).read()
        return json.loads(resp)
    except Exception as e:
        return None

def get_today_games(date_str):
    url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}'
    try:
        resp = urllib.request.urlopen(url).read()
        data = json.loads(resp)
        games = []
        for d in data.get('dates', []):
            for g in d.get('games', []):
                games.append(g)
        return games
    except:
        return []

def main():
    date_str = "2026-04-11"
    games = get_today_games(date_str)
    
    print(f"--- Detailed Box Score Check ({date_str}) ---\n")
    
    # We are interested in specific games or players from OMEGA targets
    # Targets: Ranger Suarez, Kyle Harrison, Logan Webb, Chris Bassitt, Gunnar Henderson, etc.
    
    for g in games:
        away_name = g['teams']['away']['team']['name']
        home_name = g['teams']['home']['team']['name']
        game_pk = g['gamePk']
        status = g['status']['detailedState']
        
        if status in ["In Progress", "Final", "Completed Early"]:
            print(f"Game: {away_name} @ {home_name} ({status})")
            box = get_game_data(game_pk)
            if not box: continue
            
            # Check Pitchers
            for team_key in ['away', 'home']:
                team_data = box['teams'][team_key]
                pitcher_ids = team_data.get('pitchers', [])
                for pid in pitcher_ids:
                    p = team_data['players'][f'ID{pid}']
                    stats = p.get('stats', {}).get('pitching', {})
                    if stats.get('inningsPitched', '0.0') != '0.0':
                        print(f"  P: {p['person']['fullName']:20} | IP: {stats.get('inningsPitched'):4} | K: {stats.get('strikeOuts'):2} | ER: {stats.get('runs'):2}")
                
                # Check key hitters
                for pid in team_data.get('hitters', []):
                    p = team_data['players'][f'ID{pid}']
                    stats = p.get('stats', {}).get('batting', {})
                    if stats.get('atBats', 0) > 0:
                        if p['person']['fullName'] in ["Gunnar Henderson", "Rafael Devers", "Willy Adames", "Jarren Duran", "Shohei Ohtani"]:
                            print(f"  H: {p['person']['fullName']:20} | AB: {stats.get('atBats'):1} | H: {stats.get('hits'):1} | HR: {stats.get('homeRuns'):1} | RBI: {stats.get('rbi'):1}")

if __name__ == "__main__":
    main()
