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

def get_pinnacle_and_dk_ml(game_json, target_team):
    """
    Extracts Moneyline prices specifically for Pinnacle and DraftKings from game JSON.
    """
    pin_ml = None
    dk_ml = None
    for book in game_json.get('bookmakers', []):
        book_key = book['key'].lower()
        if book_key in ['pinnacle', 'draftkings']:
            for market in book.get('markets', []):
                if market['key'] == 'h2h':
                    for outcome in market['outcomes']:
                        if outcome['name'] == target_team:
                            if book_key == 'pinnacle':
                                pin_ml = outcome['price']
                            elif book_key == 'draftkings':
                                dk_ml = outcome['price']
    return pin_ml, dk_ml

def ml_to_implied_prob(ml):
    """
    Converts American Moneyline odds to implied probability (range 0.0 to 1.0).
    """
    if ml is None:
        return 0.0
    val = float(ml)
    if val > 0:
        return 100.0 / (val + 100.0)
    elif val < 0:
        return -val / (-val + 100.0)
    return 0.5


def calibrate_vegas_itt(itt):
    """
    OMEGA v17.3: Non-Linear Vegas Calibration.
    Corrects historical Vegas bias:
    - Underpriced low totals (<3.5 by +0.93 runs)
    - Overpriced high totals (>5.5 by -0.66 runs)
    """
    if itt is None:
        return 4.5
    val = float(itt)
    if val < 3.5:
        # Interpolate upward: add up to +0.75 runs as ITT goes lower
        val += (3.5 - val) * 0.75
    elif val > 5.5:
        # Interpolate downward: subtract up to 50% of the excess above 5.5
        val -= (val - 5.5) * 0.50
    return round(val, 3)


def get_bookmaker_total(game_json, bookmaker_key):
    """
    Extracts the current game total for a specific bookmaker (e.g. pinnacle, draftkings, fanduel, circa).
    """
    bookmaker_key = bookmaker_key.lower()
    for book in game_json.get('bookmakers', []):
        if book['key'].lower() == bookmaker_key:
            for market in book.get('markets', []):
                if market['key'] == 'totals':
                    outcomes = market.get('outcomes', [])
                    if outcomes:
                        return outcomes[0].get('point')
    return None


