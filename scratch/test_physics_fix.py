import os
import sys
import json
from data.pitcher_analyzer import PitcherAnalyzer

def test_physics():
    analyzer = PitcherAnalyzer()
    
    # Test 1: In Matrix
    print("Testing 'Tyler Glasnow' (In Matrix)...")
    res = analyzer.fetch_pitcher_physics("Tyler Glasnow")
    print(f"Result: {res}")
    
    # Test 2: In StatsAPI cache (Proxy should trigger)
    # Ryne Nelson was in the cache I saw earlier
    print("\nTesting 'Ryne Nelson' (Proxy Fallback)...")
    res = analyzer.fetch_pitcher_physics("Ryne Nelson")
    print(f"Result: {res}")
    
    # Test 3: Unknown pitcher (Default fallback)
    print("\nTesting 'Unknown Pitcher' (Default)...")
    res = analyzer.fetch_pitcher_physics("Unknown Pitcher")
    print(f"Result: {res}")

if __name__ == "__main__":
    test_physics()
