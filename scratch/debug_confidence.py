import sys
import os
sys.path.append(os.getcwd())

from data.pitcher_analyzer import PitcherAnalyzer

analyzer = PitcherAnalyzer()
players = ["Dylan Cease", "Dustin May", "Matthew Boyd", "Steven Matz", "Luis Castillo"]

for p in players:
    res = analyzer.fetch_pitcher_physics(p)
    print(f"{p}: {res}")
