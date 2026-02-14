from os import CLD_CONTINUED


class Climb:
    length: float = 0
    elevation_gain: float = 0
    gradient: float = 0


"""
    @params
        distance: float = the total distance of the gpx route in meters
        weather_points: list[Points] = the points where we want to get the weather information
        climbs: list[Climb] = the climbs of the gpx route
    
"""


class Gpx_features:
    distance: float = 0
    weather_points = []
    climbs: list[Climb] = []

    def set_distance(self, _distance):
        self.distance = _distance

    def set_weather_points(self, _weather_points):
        self.weather_points = _weather_points

    def add_climbs(self, _length, _elevation):
        _climb = Climb()
        _climb.length = _length
        _climb.elevation_gain = _elevation
        _climb.gradient = _elevation / _length * 100

        self.climbs.append(_climb)


# class created for testing purposes
class Point:
    latitude: float = 0
    longitude: float = 0
    elevation: float = 0

    def __init__(self, lat, lon):
        self.latitude = lat
        self.longitude = lon
