import json
import os
from engine.sharps_weighting import SharpsWeighting

def run_fatigue_simulation():
    path = 'reports/latest_results.json'
    if not os.path.exists(path):
        print("Latest results not found.")
        return

    with open(path) as f:
        data = json.load(f)

    sharps = SharpsWeighting()
    teams = data.get('teams', [])
    
    print(f"{'Team':20} | {'Fatigue':7} | {'Old Score':9} | {'New Score':9} | {'Diff':5} | {'Runs':4}")
    print("-" * 70)
    
    # We need to reach into the logic of calculate_stack_score to simulate the sliding scale
    # Since we can't easily change the class on the fly for the sim, we'll mimic the math
    
    for t in teams:
        fatigue = t.get('bullpen_fatigue', 0)
        
        # Original Logic:
        # if fatigue >= 80: boost = 5, beta = 1
        # if fatigue >= 100: boost = 10, beta = 1
        
        # New Sliding Scale Proposal:
        # threshold = 65
        # boost = max(0, (fatigue - 65) / 3.5)
        # beta = 1 if fatigue > 65 else 0
        
        # Let's see what the diff would be by recalculating
        # We'll use the archived stack_score as the baseline and adjust the delta
        
        old_boost = 0
        old_beta = 0
        if fatigue >= 80:
            old_boost = 5.0
            old_beta = 1
            if fatigue >= 100:
                old_boost = 10.0
        
        new_boost = max(0, (fatigue - 65) / 3.5)
        new_beta = 1 if fatigue > 65 else 0
        
        # Multiplier diff
        # multiplier = 1.0 + (alpha * 0.15) + (beta * 0.05)
        # We'll assume at least 1 beta was already there or not, the delta is 0.05 if it flips
        
        beta_delta = 0
        if new_beta == 1 and old_beta == 0:
            beta_delta = 0.05 # Add 5% multiplier
        elif new_beta == 0 and old_beta == 1:
            beta_delta = -0.05 # Remove 5% multiplier
            
        # Delta calculation (approximate)
        # new_score approx = (old_score / old_mult - old_boost) + new_boost) * (old_mult + beta_delta)
        # For simplicity in this scratch sim, we'll just show the direct impact on the points
        
        # If we just apply the point diff:
        point_diff = (new_boost - old_boost)
        # And the multiplier diff (5% of the score is roughly 4-5 points)
        mult_diff = (beta_delta * t['stack_score'])
        
        total_diff = point_diff + mult_diff
        new_score = t['stack_score'] + total_diff
        
        # Only show teams where fatigue is > 50%
        if fatigue > 50:
            actual_runs = 0 # In a real sim we'd fetch this, but for now we'll just show the delta
            print(f"{t['team']:20} | {fatigue:7.1f} | {t['stack_score']:9.1f} | {new_score:9.1f} | {total_diff:+.1f}")

if __name__ == "__main__":
    run_fatigue_simulation()
