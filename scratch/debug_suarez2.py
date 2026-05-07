import sys, os
sys.path.append(os.getcwd())
from data.pitcher_analyzer import PitcherAnalyzer

a = PitcherAnalyzer()

# Test the proxy calculation directly
siera, csw, conf = a._calculate_proxy_physics(4.00, 19, 27.0)
print(f"Direct proxy test: SIERA={siera:.2f}, CSW={csw:.3f}, conf={conf}")

# Now test the full pipeline
result = a.fetch_pitcher_physics('Ranger Suarez')
print(f"\nFull pipeline: {result}")

# Test with exact name from probable_pitchers.json
import json
prob = json.load(open("data/probable_pitchers.json"))
for team, name in prob.items():
    if 'Suarez' in name or 'suarez' in name.lower():
        print(f"\nProbable pitchers has: '{name}' for {team}")
        result2 = a.fetch_pitcher_physics(name)
        print(f"Result: {result2}")
