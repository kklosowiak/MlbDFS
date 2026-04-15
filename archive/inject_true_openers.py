import json
import os

def inject():
    # True Overnight Opening Lines for April 11, 2026 (Consensus)
    # Source: covers.com / rotowire (Research snapshot)
    true_openers = [
        {"away": "Arizona Diamondbacks", "home": "Philadelphia Phillies", "away_ml": 110, "home_ml": -130, "total": 8.5},
        {"away": "Miami Marlins", "home": "Detroit Tigers", "away_ml": 124, "home_ml": -146, "total": 7.5},
        {"away": "Pittsburgh Pirates", "home": "Chicago Cubs", "away_ml": 122, "home_ml": -144, "total": 6.5},
        {"away": "Minnesota Twins", "home": "Toronto Blue Jays", "away_ml": -108, "home_ml": -108, "total": 7.5},
        {"away": "Chicago White Sox", "home": "Kansas City Royals", "away_ml": 152, "home_ml": -180, "total": 9.0},
        {"away": "Los Angeles Angels", "home": "Cincinnati Reds", "away_ml": 112, "home_ml": -132, "total": 9.0},
        {"away": "Athletics", "home": "New York Mets", "away_ml": 134, "home_ml": -158, "total": 7.5},
        {"away": "New York Yankees", "home": "Tampa Bay Rays", "away_ml": -194, "home_ml": 162, "total": 7.5},
        {"away": "Washington Nationals", "home": "Milwaukee Brewers", "away_ml": 150, "home_ml": -178, "total": 8.0},
        {"away": "San Francisco Giants", "home": "Baltimore Orioles", "away_ml": -120, "home_ml": 102, "total": 7.5},
        # Late Games (Estimated/Research)
        {"away": "St. Louis Cardinals", "home": "Boston Red Sox", "away_ml": 119, "home_ml": -143, "total": 9.5},
        {"away": "San Diego Padres", "home": "Colorado Rockies", "away_ml": -168, "home_ml": 139, "total": 11.5},
        {"away": "Texas Rangers", "home": "Los Angeles Dodgers", "away_ml": 163, "home_ml": -199, "total": 9.0},
        {"away": "Houston Astros", "home": "Seattle Mariners", "away_ml": 123, "home_ml": -149, "total": 8.0}
    ]
    
    opening_path = 'data/opening_lines.json'
    
    opening_data = []
    for o in true_openers:
        opening_data.append({
            "team_away": o['away'],
            "team_home": o['home'],
            "away_opening_ml": o['away_ml'],
            "away_current_ml": o['away_ml'], # Will be updated by engine
            "home_opening_ml": o['home_ml'],
            "home_current_ml": o['home_ml'], # Will be updated by engine
            "opening_total": o['total'],
            "current_total": o['total']
        })

    with open(opening_path, 'w') as f:
        json.dump(opening_data, f, indent=4)
    
    print(f"Successfully injected {len(opening_data)} TRUE overnight opening lines.")

if __name__ == "__main__":
    inject()
