import json
from data.bullpen_analyzer import BullpenAnalyzer

analyzer = BullpenAnalyzer()

# Check Chicago Cubs and Chicago White Sox
cubs_score = analyzer.get_fatigue_score("Chicago Cubs")
sox_score = analyzer.get_fatigue_score("Chicago White Sox")

print("\n--- Bullpen Fatigue Scores (Real-Time) ---")
print(f"Chicago Cubs: {json.dumps(cubs_score, indent=4)}")
print(f"Chicago White Sox: {json.dumps(sox_score, indent=4)}")
