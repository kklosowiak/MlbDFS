import os
import sys
import json

# Standalone execution support
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data.pitcher_analyzer import PitcherAnalyzer

analyzer = PitcherAnalyzer()
boosts = analyzer.opponent_k_boosts

for t, b in sorted(boosts.items(), key=lambda x: x[1], reverse=True):
    print(f"{t}: {b}%")
