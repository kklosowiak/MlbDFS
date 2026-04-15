import json

d = json.load(open('data/snapshot_20260411_094300.json'))
props = d.get('props', {})
odds = d.get('odds', [])

print(f"Total games: {len(odds)}")
print(f"Total prop game IDs: {len(props)}")
print()

for game in odds:
    gid = game['id']
    home = game['home_team']
    away = game['away_team']
    hp = game.get('home_pitcher', 'N/A')
    ap = game.get('away_pitcher', 'N/A')
    
    gid_props = props.get(gid, {})
    prop_markets = list(gid_props.keys()) if gid_props else []
    
    # Count pitchers discovered from props
    ks = gid_props.get('pitcher_strikeouts', [])
    outs = gid_props.get('pitcher_outs', [])
    unique_pitchers = set()
    for o in ks + outs:
        pn = o.get('player_name', '')
        if pn: unique_pitchers.add(pn)
    
    print(f"{away:25s} @ {home:25s}")
    print(f"  API Pitchers: {ap} vs {hp}")
    print(f"  Props: {prop_markets}")
    print(f"  Prop Pitchers: {unique_pitchers if unique_pitchers else 'NONE'}")
    print()
