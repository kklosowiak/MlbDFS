from data.statcast_bridge import StatcastBridge

def test_lineups():
    bridge = StatcastBridge()
    teams = ['Texas Rangers', 'Arizona Diamondbacks', 'Seattle Mariners']
    
    print("\n" + "="*50)
    print("      OMEGA v6.8.2: LINEUP DISCOVERY TEST")
    print("="*50)
    
    for team in teams:
        print(f"\n[TEAM]: {team}")
        roster = bridge.get_team_roster(team, player_type='hitter')
        
        # Display the "Full Lineup" (Top 9 hitters in the roster)
        for i, p in enumerate(roster[:9]):
            ops = p.get('ops', 0.0)
            xwoba_proxy = round(ops / 2.5, 3) if ops > 0 else 0.315
            print(f"  {i+1}. {p['name']:20} | OPS: {ops:.3f} | xWOBA (Proxy): {xwoba_proxy:.3f}")

if __name__ == "__main__":
    test_lineups()
