import math

class WeatherEngine:
    def __init__(self):
        # Stadium Data: {Team: (Lat, Long, CF_Bearing)}
        # Bearings are Home Plate -> Center Field
        self.stadiums = {
            'Arizona Diamondbacks': {'lat': 33.4455, 'lon': -112.0667, 'bearing': 0, 'is_dome': True}, # Chase Field
            'Atlanta Braves': {'lat': 33.8911, 'lon': -84.4683, 'bearing': 45}, # Truist Park
            'Baltimore Orioles': {'lat': 39.2840, 'lon': -76.6215, 'bearing': 45}, # Camden Yards
            'Boston Red Sox': {'lat': 42.3467, 'lon': -71.0972, 'bearing': 45}, # Fenway Park
            'Chicago Cubs': {'lat': 41.9484, 'lon': -87.6553, 'bearing': 45}, # Wrigley Field
            'Chicago White Sox': {'lat': 41.8299, 'lon': -87.6339, 'bearing': 157}, # Guaranteed Rate
            'Cincinnati Reds': {'lat': 39.0971, 'lon': -84.5073, 'bearing': 135}, # Great American
            'Cleveland Guardians': {'lat': 41.4958, 'lon': -81.6852, 'bearing': 45}, # Progressive Field
            'Colorado Rockies': {'lat': 39.7558, 'lon': -104.9942, 'bearing': 0}, # Coors Field
            'Detroit Tigers': {'lat': 42.3392, 'lon': -83.0485, 'bearing': 135}, # Comerica Park
            'Houston Astros': {'lat': 29.7573, 'lon': -95.3555, 'bearing': 0, 'is_dome': True}, # Minute Maid
            'Kansas City Royals': {'lat': 39.0517, 'lon': -94.4803, 'bearing': 100}, # Kauffman
            'Los Angeles Angels': {'lat': 33.8003, 'lon': -117.8827, 'bearing': 45}, # Angel Stadium
            'Los Angeles Dodgers': {'lat': 34.0739, 'lon': -118.2400, 'bearing': 22}, # Dodger Stadium
            'Miami Marlins': {'lat': 25.7783, 'lon': -80.2197, 'bearing': 0, 'is_dome': True}, # LoanDepot
            'Milwaukee Brewers': {'lat': 43.0284, 'lon': -87.9712, 'bearing': 0, 'is_dome': True}, # AmFam
            'Minnesota Twins': {'lat': 44.9817, 'lon': -93.2778, 'bearing': 45}, # Target Field
            'New York Mets': {'lat': 40.7571, 'lon': -73.8458, 'bearing': 45}, # Citi Field
            'New York Yankees': {'lat': 40.8296, 'lon': -73.9262, 'bearing': 45}, # Yankee Stadium
            'Oakland Athletics': {'lat': 37.7516, 'lon': -122.2005, 'bearing': 45}, # Coliseum
            'Philadelphia Phillies': {'lat': 39.9061, 'lon': -75.1665, 'bearing': 45}, # Citizens Bank
            'Pittsburgh Pirates': {'lat': 40.4469, 'lon': -80.0057, 'bearing': 45}, # PNC Park
            'San Diego Padres': {'lat': 32.7073, 'lon': -117.1566, 'bearing': 110}, # Petco Park
            'San Francisco Giants': {'lat': 37.7786, 'lon': -122.3893, 'bearing': 45}, # Oracle Park
            'Seattle Mariners': {'lat': 47.5914, 'lon': -122.3323, 'bearing': 45, 'is_dome': True}, # T-Mobile
            'St. Louis Cardinals': {'lat': 38.6226, 'lon': -90.1928, 'bearing': 135}, # Busch Stadium
            'Tampa Bay Rays': {'lat': 27.7682, 'lon': -82.6534, 'bearing': 0, 'is_dome': True}, # Tropicana
            'Texas Rangers': {'lat': 32.7511, 'lon': -97.0825, 'bearing': 0, 'is_dome': True}, # Globe Life
            'Toronto Blue Jays': {'lat': 43.6414, 'lon': -79.3894, 'bearing': 0, 'is_dome': True}, # Rogers Centre
            'Washington Nationals': {'lat': 38.8730, 'lon': -77.0074, 'bearing': 45} # Nationals Park
        }

    def calculate_wind_impact(self, team_name, wind_speed, wind_deg):
        """
        Determines if wind is blowing In, Out, or Cross.
        Returns: direction_label, multiplier
        """
        stadium = self.stadiums.get(team_name)
        if not stadium:
            return "Neutral", 0
        
        if stadium.get('is_dome'):
            return "Indoor", 0

        # CF bearing is the 'Out' direction
        cf_bearing = stadium['bearing']
        
        # Difference between wind and CF
        # 0 = Straight Out, 180 = Straight In
        diff = abs(wind_deg - cf_bearing) % 360
        if diff > 180:
            diff = 360 - diff
            
        # Decision Logic: Source of wind vs CF Bearing
        if diff <= 45:
            # Reverted to Original: Wind source in CF is labeled "Out"
            return f"Out {wind_speed}mph", (wind_speed / 10.0) * 1.5
        elif diff >= 135:
            # Reverted to Original: Wind source behind home is labeled "In"
            return f"In {wind_speed}mph", -(wind_speed / 10.0) * 1.5
        else:
            return f"Cross {wind_speed}mph", 0



    def calculate_density_mod(self, temp, humidity):
        """
        Simple air density effect: Hot/Dry air carries more.
        Returns score modifier (0-10)
        """
        mod = 0
        if temp >= 85: mod += 7
        elif temp >= 75: mod += 4
        
        if humidity <= 40: mod += 3
        return mod

    def get_stadium_coords(self, team_name):
        s = self.stadiums.get(team_name)
        return (s['lat'], s['lon']) if s else (None, None)
