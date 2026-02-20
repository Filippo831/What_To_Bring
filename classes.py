from constants import ELEVATION_PER_HOUR, HIKING_SPEED


class Climb:
    length: float = 0
    elevation_gain: float = 0
    gradient: float = 0
    starting_distance: float = 0
    starting_elevation: float = 0

    def __init__(self, first_point, second_point):
        self.length = second_point[0] - first_point[0]
        self.elevation_gain = second_point[1] - first_point[1]
        self.gradient = self.elevation_gain / self.length * 100
        self.starting_distance = first_point[0]
        self.starting_elevation = first_point[1]


"""
    @params
        distance: float = the total distance of the gpx route in meters
        elevation_gain: float = the total elevation gain of the gpx route in meters
        points: list[tuple] = the coordinates of the gpx route (latitude, longitude)
        path_sac_scale: list[int] = the sac scale (difficulty of the path) of each point in the gpx route
        weather_points: list[Points] = the points where we want to get the weather information
        weather_information: list[dict] = the weather information for each point in weather_points
        climbs: list[Climb] = the climbs of the gpx route
        hiking_time: int = the estimated hiking time in seconds (using Naismith's rule)
"""


class Gpx_features:
    distance: float = 0
    elevation_gain: float = 0
    points = []
    path_sac_scale = []
    weather_points = []
    weather_information = []
    climbs: list[Climb] = []
    hiking_time: int = 0

    def set_distance(self, _distance):
        self.distance = _distance

    def set_elevation_gain(self, _elevation_gain):
        self.elevation_gain = _elevation_gain

    def set_weather_points(self, _weather_points):
        self.weather_points = _weather_points

    def add_climbs(self, _climb):
        self.climbs.append(_climb)

    def calculate_hiking_time(self):
        self.hiking_time = round(
            self.distance / HIKING_SPEED * 3600
            + self.elevation_gain / ELEVATION_PER_HOUR * 3600
        )

    def append_coordinates(self, _point):
        self.points.append(_point)


# class created for testing purposes
class Point:
    latitude: float = 0
    longitude: float = 0
    elevation: float = 0

    def __init__(self, lat, lon):
        self.latitude = lat
        self.longitude = lon
