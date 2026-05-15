def get_market_prices(game_json, target_team):
    """
    Robustly extracts current ML and Total from the Odds API outcomes.
    - [x] Hard-code strict name matching in `market_utils.py`
    - [/] Fix `open_total` field mismatch in `main.py`
    """
    curr_ml = None
    curr_total = None
    
    home_team = game_json.get('home_team')
    away_team = game_json.get('away_team')
    
    # OMEGA v5.2: Forced Sharp Priority (DK > FD > MGM)
    preferred_books = ['draftkings', 'fanduel', 'betmgm', 'caesars']
    for target_book in preferred_books:
        for book in game_json.get('bookmakers', []):
            if book['key'] == target_book:
                for market in book.get('markets', []):
                    # 1. Extract Moneyline (Strict Name Match)
                    if market['key'] == 'h2h':
                        for outcome in market['outcomes']:
                            if outcome['name'] == target_team:
                                curr_ml = outcome['price']
                                
                    # 2. Extract Total (Primary Game Total)
                    if market['key'] == 'totals' and curr_total is None:
                        curr_total = market['outcomes'][0]['point']
                
                if curr_ml is not None and curr_total is not None:
                    return curr_ml, curr_total
    
    return curr_ml, curr_total

def calculate_ml_move(open_ml, curr_ml):
    """
    OMEGA v5.0.5: American Odds Linearizer.
    Converts odds to a "Cents" scale relative to 100 to get a real movement delta.
    
    POLARITY (Crucial):
    - Negative (-) Move: Price is moving IN FAVOR of the team (Green/Bullish).
    - Positive (+) Move: Price is moving AGAINST the team (Red/Bearish).
    
    Examples:
    -110 -> -122: Result is -12 (Good)
    -150 -> -138: Result is +12 (Bad)
    """
    if open_ml is None or curr_ml is None:
        return 0.0
        
    def get_cents(val):
        if val >= 100:
            return (val - 100)
        elif val <= -100:
            return -(-val - 100)
        return 0.0 # Pk or invalid
        
    delta = get_cents(curr_ml) - get_cents(open_ml)
    return float(delta)

