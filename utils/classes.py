from typing import Any


class Point:
    latitude: float = 0
    longitude: float = 0
    cumulative_distance: float = 0
    elevation: float = 0
    time: int = 0
    way_type: str = ""

    def __init__(
        self,
        _lat: float,
        _lon: float,
        _cumulative_distance: float = 0.0,
        _elev: float = 0,
        _time: int = 0,
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
        points: list[Points] = the points of the gpx route (with latitude, longitude, cumulative distance, elevation, time and way type)
        weather_points: list[Points] = the points where we want to get the weather information
        weather_information: list[dict[str, float]] = the weather information (specified in the configuration file) for each point in the gpx route
        surface_percentage: dict[str, float] = the percentage of each path surface type (e.g. asphalt, gravel, etc.) in the gpx route
        climbs: list[Climb] = the climbs of the gpx route
        hiking_time: int = the estimated hiking time in seconds (using Naismith's rule)
        is_recorded: bool = whether the gpx route is recorded or planned

"""


class Gpx_features:
    distance: float = 0
    elevation_gain: float = 0
    points: list[Point] = []
    weather_points: list[Point] = []
    weather_information: list[dict[str, float]] = []
    surface_percentage: dict[str, float] = dict()
    climbs: list[Climb] = []
    hiking_time: int = 0
    is_recorded: bool = False

    def set_is_recorded(self, _is_recorded: bool):
        self.is_recorded = _is_recorded

    def set_distance(self, _distance: float):
        self.distance = _distance

    def set_elevation_gain(self, _elevation_gain: float):
        self.elevation_gain = _elevation_gain

    def add_climbs(self, _climb: Climb):
        self.climbs.append(_climb)

    def set_hiking_time(self, _hiking_time: int):
        self.hiking_time = _hiking_time

    def append_point(self, _point: Point):
        self.points.append(_point)

    def append_weather_point(self, _point: Point):
        self.weather_points.append(_point)

    def set_surface_percentage(self, _surface_percentage: dict[str, float]):
        self.surface_percentage = _surface_percentage

    def set_weather_information(self, _weather_information: list[dict[Any, float]]):  # pyright: ignore[reportExplicitAny]
        self.weather_information = _weather_information
