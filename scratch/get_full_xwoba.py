from data.lineup_fetcher import LineupFetcher
from data.statcast_bridge import StatcastBridge
import json

def get_full_xwoba():
    lf = LineupFetcher()
    sb = StatcastBridge()
    lineups = lf.fetch_confirmed_lineups()
    cache = sb.get_cache_data()
    
    # We use a fallback xwOBA for players with zero data in 2026 (rookies/debuts)
    FALLBACK_OPS = 0.750 # .300 xwOBA
    
    for team in ['Pittsburgh Pirates', 'Chicago White Sox']:
        print(f"\n--- {team} ---")
        players = lineups.get(team, [])
        if not players:
            print("  (No confirmed lineup found yet in StatsAPI)")
            continue
            
        for i, p in enumerate(players, 1):
            # Normalize for cache lookup
            from utils.normalization import normalize_player_name
            norm = normalize_player_name(p)
            data = cache.get(norm, {})
            
            # Use rolling_ops first, then seasonal ops, then fallback
            ops = data.get('rolling_ops')
            if not ops or ops == 0:
                ops = data.get('ops')
            
            if not ops or ops == 0:
                ops = FALLBACK_OPS
                tag = "(PROJECTED)"
            else:
                tag = ""
                
            xwoba = ops / 2.5
            print(f"{i}. {p.title():<20} | Matchup xwOBA: {xwoba:.3f} {tag}")

if __name__ == "__main__":
    get_full_xwoba()
