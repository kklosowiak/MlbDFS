import json
import os

def check_k_stats():
    cache_path = os.path.join('data', 'statcast_cache.json')
    if not os.path.exists(cache_path):
        print("Cache not found.")
        return
    
    with open(cache_path, 'r') as f:
        cache = json.load(f)
        
    team_stats = {}
    for name, data in cache.items():
        if data.get('type') == 'hitter':
            team = data.get('team')
            if not team or team == "UNK": continue
            if team not in team_stats:
                team_stats[team] = {'k': 0, 'pa': 0}
            team_stats[team]['k'] += data.get('k', 0)
            team_stats[team]['pa'] += data.get('pa', 0)
            
    rates = {}
    for team, stats in team_stats.items():
        if stats['pa'] > 50:
            rates[team] = stats['k'] / stats['pa']
            
    if not rates:
        print("No rates calculated.")
        return
        
    sorted_rates = sorted(rates.items(), key=lambda x: x[1], reverse=True)
    avg_rate = sum(rates.values()) / len(rates)
    max_rate = sorted_rates[0][1]
    min_rate = sorted_rates[-1][1]
    
    print(f"League Average K%: {avg_rate:.3f}")
    print(f"Max K% ({sorted_rates[0][0]}): {max_rate:.3f}")
    print(f"Min K% ({sorted_rates[-1][0]}): {min_rate:.3f}")
    print("\nCurrent Logic (Boost = rate/max * 15):")
    for team, rate in [sorted_rates[0], sorted_rates[len(sorted_rates)//2], sorted_rates[-1]]:
        boost = (rate / max_rate) * 15.0
        print(f"  {team:20}: {boost:5.1f}%")

if __name__ == "__main__":
    check_k_stats()
