'''
    @params
        distance: float = the total distance of the gpx route
        weather_points: list[Points] = the points where we want to get the weather information
        climbs: list[Climb] = the climbs of the gpx route
    
'''
class Gpx_features:
    distance = 0
    weather_points = []
    climbs = []

    def set_distance(self, _distance):
        self.distance = _distance

    def set_weather_points(self, _weather_points):
        self.weather_points = _weather_points

    def set_climbs(self, _climbs):
        self.climbs = _climbs


# class created for testing purposes
class Point:
    latitude = 0
    longitude = 0
    elevation = 0

    def __init__(self, lat, lon):
        self.latitude = lat
        self.longitude = lon
