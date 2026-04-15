import urllib.request
import json
try:
    url = 'https://statsapi.mlb.com/api/v1/schedule?sportId=1&date=2026-04-10'
    resp = urllib.request.urlopen(url).read()
    data = json.loads(resp)
    for d in data.get('dates', []):
        for g in d.get('games', []):
            away = g['teams']['away']['team']['name']
            away_score = g['teams']['away'].get('score', '-')
            home = g['teams']['home']['team']['name']
            home_score = g['teams']['home'].get('score', '-')
            status = g['status']['detailedState']
            inning = g.get('linescore', {}).get('currentInningOrdinal', '')
            print(f"{away} {away_score} @ {home} {home_score} [{status} {inning}]")
except Exception as e:
    print(e)
