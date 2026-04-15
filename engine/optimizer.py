import pulp
import pandas as pd

class Optimizer:
    def __init__(self, salary_cap=50000):
        self.salary_cap = salary_cap
        
    def solve(self, player_df):
        """Standard DFS Lineup Optimization using PuLP."""
        # Check if we have enough players
        if len(player_df) < 9:
            print("ERROR: Not enough players to build a lineup.")
            return None
            
        # Define the problem
        prob = pulp.LpProblem("MLB_DFS_Optimization", pulp.LpMaximize)
        
        # Decision variables: 1 if player is chosen, 0 otherwise
        player_vars = {i: pulp.LpVariable(f"player_{i}", 0, 1, pulp.LpBinary) for i in player_df.index}
        
        # Objective function: Maximize total projection
        prob += pulp.lpSum(player_vars[i] * player_df.loc[i, 'Final_Projection'] for i in player_df.index)
        
        # Constraint 1: Salary cap
        prob += pulp.lpSum(player_vars[i] * player_df.loc[i, 'Salary'] for i in player_df.index) <= self.salary_cap
        
        # Constraint 2: Total number of players (example: 9 for DK)
        prob += pulp.lpSum(player_vars[i] for i in player_df.index) == 9
        
        # Solve
        status = prob.solve(pulp.PULP_CBC_CMD(msg=0))
        
        if status == pulp.LpStatusOptimal:
            selected_indices = [i for i in player_df.index if player_vars[i].varValue == 1]
            return player_df.loc[selected_indices]
        else:
            print("ERROR: Optimization failed.")
            return None

if __name__ == "__main__":
    # Test with dummy data
    data = {
        'Player': [f"P{i}" for i in range(20)],
        'Salary': [4000, 5000, 6000, 4500, 5500] * 4,
        'Final_Projection': [10, 12, 18, 11, 14] * 4
    }
    df = pd.DataFrame(data)
    opt = Optimizer()
    lineup = opt.solve(df)
    if lineup is not None:
        print(lineup)
