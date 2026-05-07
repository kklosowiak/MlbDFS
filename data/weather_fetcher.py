import requests
import json
import os
from engine.weather_engine import WeatherEngine

class WeatherFetcher:
    def __init__(self, data_dir="data"):
        self.engine = WeatherEngine()
        self.base_url = "https://wttr.in/"
        self.cache = {} # Stadium-level cache
        self.expert_cache_path = os.path.join(data_dir, "expert_weather_cache.json")
        self.expert_data = self._load_expert_cache()

    def _load_expert_cache(self):
        """Loads the Propfinder expert weather overlay and normalizes team names."""
        if os.path.exists(self.expert_cache_path):
            try:
                with open(self.expert_cache_path, 'r') as f:
                    data = json.load(f)
                    indexed = {}
                    for item in data:
                        # OMEGA v6.6.5: Robust Multi-Index for Teams
                        full_home = item['home']
                        indexed[full_home] = item
                        
                        # Add nickname index (e.g. 'Cubs' from 'Chicago Cubs')
                        nickname = full_home.split()[-1]
                        indexed[nickname] = item
                        
                        # Add city/prefix index (e.g. 'Chicago' from 'Chicago Cubs')
                        prefix = full_home.split()[0]
                        indexed[prefix] = item
                        
                        # Special Case Aliases (v6.6.5 hardening)
                        if "D-backs" in full_home or "Diamondbacks" in full_home:
                            indexed["D-backs"] = item
                            indexed["ARI"] = item
                        
                        # Support for Abbreviations if available
                        code_map = {
                            "NYM": "Mets", "NYY": "Yankees", "LAD": "Dodgers", 
                            "CHC": "Cubs", "CHW": "White Sox", "ATL": "Braves"
                        }
                        for code, nick in code_map.items():
                            if nick in full_home:
                                indexed[code] = item
                    return indexed
            except:
                return {}
        return {}

    def fetch_game_weather(self, team_name):
        """
        Fetches hyperlocal weather for a specific stadium using Lat/Lon.
        Fallback to wttr.in if expert data is unavailable or missing.
        """
        # Primary: Expert Cache Overlay
        if team_name in self.expert_data:
            expert = self.expert_data[team_name]
            return {
                'temp': int(expert['temp']),
                'wind_speed': int(expert['wind_speed']),
                'wind_deg': 0, # expert provides direction as string
                'wind_dir_str': expert['wind_dir'],
                'humidity': 50, # Default for expert data
                'desc': expert['notes'],
                'status': expert['status']
            }

        # Secondary: Instant Cache
        if team_name in self.cache:
            return self.cache[team_name]

        lat, lon = self.engine.get_stadium_coords(team_name)
        if not lat:
            return None

        # wttr.in format: wttr.in/{lat},{lon}?format=j1
        try:
            url = f"{self.base_url}{lat},{lon}?format=j1"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                current = data['current_condition'][0]
                
                result = {
                    'temp': int(current['temp_F']),
                    'wind_speed': int(current['windspeedMiles']),
                    'wind_deg': int(current['winddirDegree']),
                    'humidity': int(current['humidity']),
                    'desc': current['weatherDesc'][0]['value'],
                    'status': 'Neutral'
                }
                self.cache[team_name] = result
                return result
        except Exception as e:
            print(f"Weather Fetch Error for {team_name}: {e}")
        
        return None

    def get_alpha_modifier(self, team_name):
        """
        Returns the combined weather label, alpha boost, and icon.
        Integrates Propfinder Expert Status and Directions.
        """
        weather = self.fetch_game_weather(team_name)
        if not weather:
            return {"label": "TBD", "boost": 0, "icon": "⚪", "status": "Neutral"}

        # Logic for Expert Direction vs Angle
        if 'wind_dir_str' in weather:
            # EXPERT OVERLAY LOGIC
            label = weather['wind_dir_str']
            wind_boost = 0
            if "Out" in label:
                wind_boost = (weather['wind_speed'] / 10.0) * 1.5
            elif "In" in label:
                wind_boost = -(weather['wind_speed'] / 10.0) * 1.5
        else:
            # AUTOMATED LOGIC
            label, wind_boost = self.engine.calculate_wind_impact(
                team_name, weather['wind_speed'], weather['wind_deg']
            )
            
        density_boost = self.engine.calculate_density_mod(
            weather['temp'], weather['humidity']
        )
        
        total_boost = wind_boost + density_boost
        
        # Determine Status Icon (Roth Overlay)
        status = weather.get('status', 'Neutral')
        status_icon = "🟢"
        if status == "Yellow" or status == "Chance For Delay": status_icon = "🟡"
        elif status == "Orange": status_icon = "🟠"
        elif status == "Red": status_icon = "🔴"

        # Determine Weather Icon
        icon = "☀️"
        if "In" in label: icon = "❄️"
        elif "Out" in label: icon = "💨"
        elif "Rain" in weather.get('desc', "") or "Showers" in weather.get('desc', ""): icon = "🌧️"
        elif weather['temp'] >= 85: icon = "🔥"

        return {
            "label": f"{status_icon} {weather['temp']}° / {label}",
            "boost": total_boost,
            "icon": icon,
            "status": status,
            "notes": weather.get('desc', "")
        }
