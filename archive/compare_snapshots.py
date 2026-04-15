import json

def get_ml_from_odds(odds_list):
    res = {}
    for g in odds_list:
        gid = g['id']
        home = g['home_team']
        away = g['away_team']
        # Try to find ML in bookmakers
        home_ml = None
        away_ml = None
        for b in g.get('bookmakers', []):
            if b['key'] == 'draftkings':
                for m in b.get('markets', []):
                    if m['key'] == 'h2h':
                        for o in m['outcomes']:
                            if o['name'] == home: home_ml = o['price']
                            if o['name'] == away: away_ml = o['price']
        res[gid] = {'home': home, 'away': away, 'home_ml': home_ml, 'away_ml': away_ml}
    return res

d1 = json.load(open('data/snapshot_20260411_093359.json'))
d2 = json.load(open('data/snapshot_20260411_094300.json'))

o1 = get_ml_from_odds(d1['odds'])
o2 = get_ml_from_odds(d2['odds'])

print(f"{'Team':25s} | 9:33 ML | 9:43 ML | Delta")
print("-" * 60)
for gid, data in o2.items():
    if gid in o1:
        prev = o1[gid]
        if data['home_ml'] and prev['home_ml']:
            delta = data['home_ml'] - prev['home_ml']
            print(f"{data['home']:25s} | {prev['home_ml']:7} | {data['home_ml']:7} | {delta:+d}")
        if data['away_ml'] and prev['away_ml']:
            delta = data['away_ml'] - prev['away_ml']
            print(f"{data['away']:25s} | {prev['away_ml']:7} | {data['away_ml']:7} | {delta:+d}")
