import statsapi
import json

# Testing if we can get handedness from the stats API without individual people calls
def test_handedness():
    params = {
        'stats': 'season',
        'group': 'hitting',
        'sportId': 1,
        'season': 2026,
        'limit': 1
    }
    # Using statsapi for ease of use
    data = statsapi.get('stats', params)
    if 'stats' in data and data['stats'][0].get('splits'):
        split = data['stats'][0]['splits'][0]
        player_id = split['player']['id']
        # Let's see what a person record looks like
        person = statsapi.get('person', {'personId': player_id})
        print(json.dumps(person, indent=4))

if __name__ == "__main__":
    test_handedness()
