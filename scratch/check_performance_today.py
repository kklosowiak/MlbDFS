import urllib.request
import json
from datetime import datetime

def get_scores(date_str):
    url = f'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date={date_str}'
    try:
        resp = urllib.request.urlopen(url).read()
        data = json.loads(resp)
        games = []
        for d in data.get('dates', []):
            for g in d.get('games', []):
                away = g['teams']['away']['team']['name']
                away_score = g['teams']['away'].get('score', 0)
                home = g['teams']['home']['team']['name']
                home_score = g['teams']['home'].get('score', 0)
                status = g['status']['detailedState']
                games.append({
                    'away': away,
                    'away_score': away_score,
                    'home': home,
                    'home_score': home_score,
                    'status': status
                })
        return games
    except Exception as e:
        print(f"Error fetching scores: {e}")
        return []

def main():
    date_str = "2026-04-11"
    scores = get_scores(date_str)
    
    try:
        with open('reports/latest_results.json', 'r') as f:
            omega_data = json.load(f)
    except Exception as e:
        print(f"Error loading OMEGA results: {e}")
        return

    print(f"--- OMEGA Performance Analysis ({date_str}) ---\n")
    
    # Check Pitchers
    print("TOP PITCHER TARGETS:")
    for p in omega_data.get('pitchers', [])[:10]:
        pitcher = p['pitcher']
        team = p['team']
        score = p['alpha_score']
        target = p.get('is_juiced_target', False)
        
        # Find game
        game_status = "Not Found"
        for g in scores:
            if team in [g['away'], g['home']]:
                game_status = f"{g['away']} {g['away_score']} @ {g['home']} {g['home_score']} [{g['status']}]"
                break
        
        tag = "[TARGET]" if target else ""
        print(f"  {pitcher:20} ({team:15}) | OMEGA: {score:5.1f} {tag:8} | Game: {game_status}")

    # Check Teams (Stacks)
    print("\nTOP TEAM STACKS:")
    for t in omega_data.get('teams', [])[:5]:
        team = t['team']
        score = t['stack_score']
        
        game_status = "Not Found"
        for g in scores:
            if team == g['away']:
                game_status = f"{g['away']} {g['away_score']} @ {g['home']} {g['home_score']} [{g['status']}]"
                break
            if team == g['home']:
                game_status = f"{g['home']} {g['home_score']} vs {g['away']} {g['away_score']} [{g['status']}]"
                break
        
        print(f"  {team:25} | OMEGA: {score:5.1f} | Game: {game_status}")

    # Check Hitters
    print("\nTOP HITTER TARGETS:")
    for h in omega_data.get('hitters', [])[:10]:
        name = h['name']
        team = h['team']
        score = h['player_score']
        target = h.get('is_juiced_target', False)
        
        game_status = "Not Found"
        for g in scores:
            if team in [g['away'], g['home']]:
                game_status = f"{g['away']} {g['away_score']} - {g['home']} {g['home_score']} [{g['status']}]"
                break
        
        tag = "[TARGET]" if target else ""
        print(f"  {name:20} ({team:15}) | OMEGA: {score:5.1f} {tag:8} | Game: {game_status}")

if __name__ == "__main__":
    main()
