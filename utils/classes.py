from utils.constants import ELEVATION_PER_HOUR, HIKING_SPEED
import datetime


class Point:
    latitude: float = 0
    longitude: float = 0
    cumulative_distance: float = 0
    elevation: float = 0
    time: datetime.datetime = datetime.datetime.now()

    def __init__(
        self,
        _lat,
        _lon,
        _cumulative_distance=0.0,
        _elev=0,
        _time=datetime.datetime.now(),
    ):
        self.latitude = _lat
        self.longitude = _lon
        self.cumulative_distance = _cumulative_distance
        self.elevation = _elev
        self.time = _time


class Climb:
    length: float = 0
    elevation_gain: float = 0
    gradient: float = 0
    starting_distance: float = 0
    starting_elevation: float = 0

    def __init__(self, first_point: Point, second_point: Point):
        self.length = second_point.cumulative_distance - first_point.cumulative_distance
        self.elevation_gain = second_point.elevation - first_point.elevation
        self.gradient = self.elevation_gain / self.length * 100
        self.starting_distance = first_point.cumulative_distance
        self.starting_elevation = first_point.elevation


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
        is_recorded: bool = whether the gpx route is recorded or planned

"""


class Gpx_features:
    distance: float = 0
    elevation_gain: float = 0
    points: list[Point] = []
    path_sac_scale = []
    weather_points: list[Point] = []
    weather_information = []
    climbs: list[Climb] = []
    hiking_time: int = 0
    is_recorded: bool = False

    def set_distance(self, _distance):
        self.distance = _distance

    def set_elevation_gain(self, _elevation_gain):
        self.elevation_gain = _elevation_gain

    def add_climbs(self, _climb: Climb):
        self.climbs.append(_climb)

    # calculate the hiking time using Naismith's rule if not recorded, otherwise use the time from the gpx file
    # def calculate_hiking_time(self):
    #     self.hiking_time = round(
    #         self.distance / HIKING_SPEED * 3600
    #         + self.elevation_gain / ELEVATION_PER_HOUR * 3600
    #     )
    def set_hiking_time(self, _hiking_time):
        self.hiking_time = _hiking_time

    def append_point(self, _point: Point):
        self.points.append(_point)

    def append_weather_point(self, _point: Point):
        self.weather_points.append(_point)
