
import requests
import json
import os
from config import config

def debug_api_health():
    api_key = config.ODDS_API_KEY
    print(f"--- OMEGA API HEALTH AUDIT (12:38 PM) ---")
    
    # 1. Quota / Usage Check
    print(f"[ACTION]: Checking API Quota...")
    usage_url = f"https://api.the-odds-api.com/v4/sports?apiKey={api_key}"
    res = requests.get(usage_url)
    print(f"  - Status: {res.status_code}")
    if res.status_code == 200:
        quota_remaining = res.headers.get('x-requests-remaining', 'unknown')
        quota_used = res.headers.get('x-requests-used', 'unknown')
        print(f"  - Quota Remaining: {quota_remaining}")
        print(f"  - Quota Used: {quota_used}")

    # 2. Sports Availability
    if res.status_code == 200:
        sports = res.json()
        baseball = [s for s in sports if s['key'] == 'baseball_mlb']
        if baseball:
            print(f"  - MLB (baseball_mlb) is active and available.")
        else:
            print(f"  - WARNING: MLB not found in active sports list.")

    # 3. Direct Prop Check for a specific Game
    print(f"\n[ACTION]: Checking Live Prop Availability for Game 1...")
    odds_url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/odds/?apiKey={api_key}&regions=us&markets=h2h"
    o_res = requests.get(odds_url)
    if o_res.status_code == 200:
        games = o_res.json()
        if games:
            game_id = games[0]['id']
            game_name = f"{games[0]['away_team']} @ {games[0]['home_team']}"
            print(f"  - Testing Event: {game_name} ({game_id})")
            
            # Request all relevant markets
            markets = "batter_home_runs,batter_hits,batter_total_bases,batter_stolen_bases"
            prop_url = f"https://api.the-odds-api.com/v4/sports/baseball_mlb/events/{game_id}/odds?apiKey={api_key}&regions=us&markets={markets}&oddsFormat=american"
            p_res = requests.get(prop_url)
            print(f"  - Prop Search Status: {p_res.status_code}")
            if p_res.status_code == 200:
                p_data = p_res.json()
                active_markets = []
                for bm in p_data.get('bookmakers', []):
                    for m in bm.get('markets', []):
                        active_markets.append(m['key'])
                
                findings = set(active_markets)
                if findings:
                    print(f"  - SUCCESS: Found active props: {findings}")
                else:
                    print(f"  - WARNING: API returned 200 OK but NO player props are available yet for this game.")
            else:
                print(f"  - ERROR: Prop search failed with status {p_res.status_code}")
        else:
             print("  - ERROR: No upcoming games found in H2H odds.")

if __name__ == "__main__":
    debug_api_health()
