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

    def _extract_json_array(self, text, key):
        start_idx = text.find(key)
        if start_idx == -1: return None
        array_start = text.find('[', start_idx)
        if array_start == -1: return None
        bracket_count = 0
        for i in range(array_start, len(text)):
            char = text[i]
            if char == '[': bracket_count += 1
            elif char == ']':
                bracket_count -= 1
                if bracket_count == 0:
                    try:
                        return json.loads(text[array_start:i+1])
                    except:
                        return None
        return None

    def refresh(self):
        print(f"[WEATHER]: Scraping Propfinder Expert Overlay (Roth Reports)...")
        results = []
        
        # 1. Primary: High-Fidelity Next.js Hydration Stream Parser (Instant, precise, extracts Roth's exact game-time metrics)
        try:
            import sys
            import os
            import requests
            from bs4 import BeautifulSoup
            from datetime import datetime
            
            # Add project root to sys.path
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)
                
            from engine.weather_engine import WeatherEngine
            
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            resp = requests.get(self.url, headers=headers, timeout=15)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # Scan script tags for the streaming hydration payload
                for script in soup.find_all('script'):
                    script_text = script.string or ""
                    if "initialNotes" in script_text:
                        chunks = re.findall(r'self\.__next_f\.push\(\[1,\s*"(.*?)"\]\)', script_text)
                        if chunks:
                            # Reconstruct and unescape Next.js stream payload
                            full_payload = "".join(chunks).replace('\\"', '"').replace('\\\\', '\\')
                            
                            games = self._extract_json_array(full_payload, '"initialGames"')
                            notes = self._extract_json_array(full_payload, '"initialNotes"')
                            
                            if games:
                                print(f"  - [HYDRATION]: Successfully extracted {len(games)} games from Next.js stream.")
                                engine = WeatherEngine()
                                
                                for g in games:
                                    try:
                                        home_raw = g['homeTeam']['fullName']
                                        away_raw = g['visitorTeam']['fullName']
                                        
                                        home_team = self.normalize_team(home_raw)
                                        away_team = self.normalize_team(away_raw)
                                        
                                        game_id = g['id']
                                        game_date_str = g['gameDate'] # e.g. "2026-05-20T01:40:00Z"
                                        
                                        # Match Kevin Roth's Forecaster Notes
                                        game_notes = [n for n in notes if n.get('gameId') == game_id]
                                        notes_text = game_notes[0]['content'].strip() if game_notes else ""
                                        
                                        # Status Indicator (Green/Yellow/Orange/Red/Roof/Neutral)
                                        status = g.get('weatherIndicator') or "Neutral"
                                        if status == "None" or not status:
                                            status = "Neutral"
                                            
                                        # Game start timestamp
                                        dt = datetime.fromisoformat(game_date_str.replace('Z', '+00:00'))
                                        game_ts = int(dt.timestamp())
                                        
                                        # Find closest hour in weatherData list
                                        weather_data = g.get('weatherData', [])
                                        closest_hour = None
                                        min_diff = float('inf')
                                        for hour in weather_data:
                                            epoch = hour.get('dateTimeEpoch', 0)
                                            diff = abs(epoch - game_ts)
                                            if diff < min_diff:
                                                min_diff = diff
                                                closest_hour = hour
                                                
                                        if closest_hour:
                                            temp = int(round(closest_hour.get('temp', 70)))
                                            wind_speed = int(round(closest_hour.get('windSpeed', 5)))
                                            wind_deg = int(round(closest_hour.get('windDir', 0)))
                                            humidity = int(round(closest_hour.get('humidity', 50)))
                                        else:
                                            temp, wind_speed, wind_deg, humidity = 70, 5, 0, 50
                                            
                                        # Resolve wind direction label
                                        wind_dir = "Neutral"
                                        
                                        stadium = engine.stadiums.get(home_team)
                                        is_dome = stadium.get('is_dome') if stadium else False
                                        
                                        if is_dome:
                                            wind_dir = "Indoor"
                                            status = "Roof"
                                        else:
                                            found_dir = False
                                            
                                            # A. Search notes for exact directions
                                            directions = ["Out to Right", "Out to Left", "Out to Center", 
                                                          "In from Right", "In from Left", "In from Center", 
                                                          "Cross", "Indicated", "Indoor"]
                                            if notes_text:
                                                for d in directions:
                                                    if d.lower() in notes_text.lower():
                                                        wind_dir = d
                                                        found_dir = True
                                                        break
                                                        
                                            # B. Check simple "blowing out" / "blowing in" phrasing
                                            if not found_dir and notes_text:
                                                cleaned_notes = notes_text.lower()
                                                if any(x in cleaned_notes for x in ["blowing out", "winds out", "wind out", "winds blowing out"]):
                                                    wind_dir = "Out to Center"
                                                    found_dir = True
                                                elif any(x in cleaned_notes for x in ["blowing in", "winds in", "wind in", "winds blowing in"]):
                                                    wind_dir = "In from Center"
                                                    found_dir = True
                                                    
                                            # C. Fallback to WeatherEngine bearing math
                                            if not found_dir:
                                                auto_label, _ = engine.calculate_wind_impact(home_team, wind_speed, wind_deg)
                                                if "Out" in auto_label:
                                                    wind_dir = "Out to Center"
                                                elif "In" in auto_label:
                                                    wind_dir = "In from Center"
                                                elif "Cross" in auto_label:
                                                    wind_dir = "Cross"
                                                elif "Indoor" in auto_label:
                                                    wind_dir = "Indoor"
                                                    status = "Roof"
                                                else:
                                                    wind_dir = "Neutral"
                                                    
                                        results.append({
                                            "home": home_team,
                                            "away": away_team,
                                            "temp": temp,
                                            "wind_speed": wind_speed,
                                            "wind_deg": wind_deg,
                                            "humidity": humidity,
                                            "wind_dir": wind_dir,
                                            "status": status,
                                            "notes": notes_text
                                        })
                                    except Exception as single_game_e:
                                        print(f"  - Hydration parse error for game: {single_game_e}")
                                        continue
                                break
        except Exception as hyd_e:
            print(f"  - [HYDRATION WARNING]: Next.js stream parser failed: {hyd_e}. Falling back...")
            
        # 2. Secondary: Fast BeautifulSoup Card Scraper (if hydration stream parsing failed/changed)
        if not results:
            print(f"  - [BS4]: Falling back to BeautifulSoup HTML card scraping...")
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
                                "wind_deg": 0,
                                "humidity": 50,
                                "wind_dir": wind_dir,
                                "status": status,
                                "notes": notes
                            })
                        except Exception as card_e:
                            print(f"  - BS4 Skip card: {card_e}")
                            continue
            except Exception as bs4_e:
                print(f"  - [BS4 WARNING]: BS4 Scraper failed: {bs4_e}. Falling back to Playwright...")
                
        # 3. Tertiary: Playwright Headless Browser fallback (if both requests scrapers failed)
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
                                "wind_deg": 0,
                                "humidity": 50,
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
            print("  [WARNING]: All Scrapers finished but results were empty. Verify connection or page structure.")

if __name__ == "__main__":
    PropfinderScraper().refresh()
