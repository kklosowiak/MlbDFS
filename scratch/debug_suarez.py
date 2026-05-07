import requests
r = requests.get('https://statsapi.mlb.com/api/v1/people/search?names=Ranger Suarez&sportId=1', timeout=10)
people = r.json().get('people', [])
print(f"Found {len(people)} results")
for p in people[:5]:
    print(f"  ID={p['id']} Name={p['fullName']} Pos={p.get('primaryPosition',{}).get('abbreviation','?')}")

# Now check the first result's stats
if people:
    pid = people[0]['id']
    s = requests.get(f'https://statsapi.mlb.com/api/v1/people/{pid}/stats?stats=season&season=2026&group=pitching', timeout=10)
    stats = s.json().get('stats', [{}])[0].get('splits', [])
    if stats:
        stat = stats[0].get('stat', {})
        print(f"\nStats for ID {pid}: ERA={stat.get('era')}, K={stat.get('strikeOuts')}, IP={stat.get('inningsPitched')}")
    else:
        print(f"\nNo 2026 pitching splits for ID {pid}")
