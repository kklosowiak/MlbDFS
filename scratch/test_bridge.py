import sys
import os
sys.path.append(os.getcwd())

from data.statcast_bridge import StatcastBridge

bridge = StatcastBridge()
print("Fetching 2026 Pitching stats...")
p_stats = bridge._fetch_api_stats(group='pitching', stats='season', season=2026)
print(f"Found {len(p_stats)} pitchers in 2026.")

print("Fetching 2025 Pitching stats...")
p_stats_2025 = bridge._fetch_api_stats(group='pitching', stats='season', season=2025)
print(f"Found {len(p_stats_2025)} pitchers in 2025.")
