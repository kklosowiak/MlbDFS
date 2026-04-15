import json

d = json.load(open('data/snapshot_20260411_094300.json'))
# Look at one game's prop structure
gid = list(d['props'].keys())[0]
ks = d['props'][gid].get('pitcher_strikeouts', [])
print(f"Game ID: {gid}")
print(f"K props count: {len(ks)}")
if ks:
    print(f"Sample outcome keys: {list(ks[0].keys())}")
    for o in ks[:4]:
        print(f"  {o}")
