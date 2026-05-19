import os
import json
import time
import re
class PropfinderScraper:
    def __init__(self, data_dir="data"):
        self.url = "https://propfinder.app/weather"
        self.cache_path = os.path.join(data_dir, "expert_weather_cache.json")
        
        # Standard OMEGA Team Name Map for normalization
        self.team_name_map = {
            "D-backs": "Arizona Diamondbacks",
            "Diamondbacks": "Arizona Diamondbacks",
            "Braves": "Atlanta Braves",
            "Orioles": "Baltimore Orioles",
            "Red Sox": "Boston Red Sox",
            "Cubs": "Chicago Cubs",
            "White Sox": "Chicago White Sox",
            "Reds": "Cincinnati Reds",
            "Guardians": "Cleveland Guardians",
            "Rockies": "Colorado Rockies",
            "Tigers": "Detroit Tigers",
            "Astros": "Houston Astros",
            "Royals": "Kansas City Royals",
            "Angels": "Los Angeles Angels",
            "Dodgers": "Los Angeles Dodgers",
            "Marlins": "Miami Marlins",
            "Brewers": "Milwaukee Brewers",
            "Twins": "Minnesota Twins",
            "Mets": "New York Mets",
            "Yankees": "New York Yankees",
            "Athletics": "Oakland Athletics",
            "Phillies": "Philadelphia Phillies",
            "Pirates": "Pittsburgh Pirates",
            "Padres": "San Diego Padres",
            "Giants": "San Francisco Giants",
            "Mariners": "Seattle Mariners",
            "Cardinals": "St. Louis Cardinals",
            "Rays": "Tampa Bay Rays",
            "Rangers": "Texas Rangers",
            "Blue Jays": "Toronto Blue Jays",
            "Nationals": "Washington Nationals"
        }

    def normalize_team(self, raw_name):
        """Converts Propfinder nicknames to full OMEGA team names."""
        if not raw_name: return "Unknown"
        # Check direct mapping
        if raw_name in self.team_name_map:
            return self.team_name_map[raw_name]
        
        # Check if full name is already provided
        for short, full in self.team_name_map.items():
            if short in raw_name:
                return full
        
        return raw_name

    def refresh(self):
        print(f"[WEATHER]: Scraping Propfinder Expert Overlay (Roth Reports)...")
        results = []
        
        # Primary: Fast, Lightweight BeautifulSoup Scraper (Runs with 0 browser overhead, works on Render)
        try:
            import requests
            from bs4 import BeautifulSoup
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(self.url, headers=headers, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                cards = soup.find_all(class_=lambda x: x and 'MuiCard-root' in x)
                print(f"  - [BS4]: Found {len(cards)} active weather cards.")
                
                for card in cards:
                    try:
                        imgs = card.find_all('img')
                        if len(imgs) < 2: continue
                        
                        away_raw = imgs[0].get("alt")
                        home_raw = imgs[1].get("alt")
                        if not away_raw or not home_raw: continue
                        
                        home_team = self.normalize_team(home_raw)
                        away_team = self.normalize_team(away_raw)
                        
                        status_chip = card.find(class_=lambda x: x and 'MuiChip-label' in x)
                        status = status_chip.get_text().strip() if status_chip else "Neutral"
                        
                        content = card.get_text(separator=' ')
                        
                        temp_match = re.search(r'(\d+)°', content)
                        temp = int(temp_match.group(1)) if temp_match else 70
                        
                        wind_match = re.search(r'(\d+)\s*mph', content)
                        wind_speed = int(wind_match.group(1)) if wind_match else 5
                        
                        wind_dir = "Neutral"
                        directions = ["Out to Right", "Out to Left", "Out to Center", 
                                      "In from Right", "In from Left", "In from Center", 
                                      "Cross", "Indicated", "Indoor"]
                        for d in directions:
                            if d.lower() in content.lower():
                                wind_dir = d
                                break
                                
                        notes = ""
                        if "FORECASTER NOTES" in content:
                            notes_part = content.split("FORECASTER NOTES")[-1].strip()
                            notes_part = re.sub(r'^\s*\(\d+\)\s*', '', notes_part).strip()
                            notes_part = re.sub(r'^Kevin Roth\s*', '', notes_part).strip()
                            notes_part = re.sub(r'^Forecaster:\s*Kevin Roth\s*', '', notes_part).strip()
                            if notes_part:
                                notes = notes_part.split('\n')[0].strip()
                                
                        results.append({
                            "home": home_team,
                            "away": away_team,
                            "temp": temp,
                            "wind_speed": wind_speed,
                            "wind_dir": wind_dir,
                            "status": status,
                            "notes": notes
                        })
                    except Exception as card_e:
                        print(f"  - BS4 Skip card: {card_e}")
                        continue
        except Exception as bs4_e:
            print(f"  - [BS4 WARNING]: BS4 Scraper failed: {bs4_e}. Falling back to Playwright...")
            
        # Secondary: Playwright Headless Browser fallback (if BS4 didn't find cards or threw error)
        if not results:
            print(f"  - [PLAYWRIGHT]: Falling back to Playwright browser scrape...")
            try:
                from playwright.sync_api import sync_playwright
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    page = browser.new_page()
                    page.goto(self.url, wait_until="networkidle", timeout=60000)
                    page.wait_for_selector(".MuiCard-root", timeout=30000)
                    time.sleep(2)
                    cards = page.query_selector_all(".MuiCard-root")
                    print(f"  - Found {len(cards)} active weather cards via Playwright.")
                    
                    for card in cards:
                        try:
                            imgs = card.query_selector_all("img[alt]")
                            if len(imgs) < 2: continue
                            away_raw = imgs[0].get_attribute("alt")
                            home_raw = imgs[1].get_attribute("alt")
                            home_team = self.normalize_team(home_raw)
                            away_team = self.normalize_team(away_raw)
                            
                            status_chip = card.query_selector(".MuiChip-label")
                            status = status_chip.inner_text() if status_chip else "Neutral"
                            content = card.inner_text()
                            
                            temp_match = re.search(r'(\d+)°', content)
                            temp = int(temp_match.group(1)) if temp_match else 70
                            
                            wind_match = re.search(r'(\d+)\s*mph', content)
                            wind_speed = int(wind_match.group(1)) if wind_match else 5
                            
                            wind_dir = "Neutral"
                            directions = ["Out to Right", "Out to Left", "Out to Center", 
                                          "In from Right", "In from Left", "In from Center", 
                                          "Cross", "Indicated", "Indoor"]
                            for d in directions:
                                if d.lower() in content.lower():
                                    wind_dir = d
                                    break
                            
                            notes = ""
                            if "FORECASTER NOTES" in content:
                                notes_part = content.split("FORECASTER NOTES")[-1].strip()
                                notes_part = re.sub(r'^\s*\(\d+\)\s*', '', notes_part).strip()
                                notes_part = re.sub(r'^Kevin Roth\s*', '', notes_part).strip()
                                notes_part = re.sub(r'^Forecaster:\s*Kevin Roth\s*', '', notes_part).strip()
                                if notes_part:
                                    notes = notes_part.split('\n')[0].strip()
                            
                            results.append({
                                "home": home_team,
                                "away": away_team,
                                "temp": temp,
                                "wind_speed": wind_speed,
                                "wind_dir": wind_dir,
                                "status": status,
                                "notes": notes
                            })
                        except Exception as e:
                            print(f"  - Playwright Skip card: {e}")
                            continue
                    browser.close()
            except Exception as e:
                print(f"  - [PLAYWRIGHT ERROR]: Playwright Scraper failed: {e}")
                
        if results:
            with open(self.cache_path, 'w') as f:
                json.dump(results, f, indent=2)
            print(f"  [SUCCESS]: Expert weather cache refreshed for {len(results)} games.")
        else:
            print("  [WARNING]: Both Scrapers finished but results were empty. Verify connection or page structure.")

if __name__ == "__main__":
    PropfinderScraper().refresh()
