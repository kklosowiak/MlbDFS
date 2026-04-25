import json
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

with open('reports/latest_results.json', 'r') as f:
    results = json.load(f)

targets = ['Trevor Story', 'Trent Grisham', 'Victor Scott', 'Masyn Winn', 'Byron Buxton', 'Andrew Benintendi']

print("============ PLAYER COMPARISON ============")
for h in results['hitters']:
    if h['name'] in targets:
        print(f"{h['name']} ({h['team']}) - Score: {h['player_score']} | xWOBA: {h.get('matchup_xwoba', 0)} | Sharp: {h['is_juiced_target']}")
