import json
import os
from data.bullpen_analyzer import BullpenAnalyzer
from config import config

# Let's find the snapshot from today
files = [f for f in os.listdir(config.DATA_DIR) if f.startswith("snapshot_") and f.endswith(".json")]
if files:
    files.sort(reverse=True)
    snapshot_path = os.path.join(config.DATA_DIR, files[0])
    print(f"Loading snapshot: {files[0]}")
    with open(snapshot_path, 'r') as f:
        snapshot = json.load(f)
    
    analyzer = BullpenAnalyzer()
    
    # Check Chicago Cubs and Chicago White Sox
    cubs_score = analyzer.get_fatigue_score("Chicago Cubs")
    sox_score = analyzer.get_fatigue_score("Chicago White Sox")
    
    print("\n--- Bullpen Fatigue Scores ---")
    print(f"Chicago Cubs: {json.dumps(cubs_score, indent=4)}")
    print(f"Chicago White Sox: {json.dumps(sox_score, indent=4)}")
else:
    print("No snapshots found.")
