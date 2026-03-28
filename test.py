import unittest
from utils.classes import Point, Gpx_features
from utils.gpx import haversine_distance, extract_features
import gpxpy


class TestHaversine(unittest.TestCase):
    def test_haversine_distance(self):
        first = Point(38.898, -77.037)
        second = Point(48.858, 2.294)

        self.assertAlmostEqual(
            haversine_distance(first, second) / 1000, 6161.6, places=1
        )


class TestFeaturesExtraction(unittest.TestCase):
    def test_features_extract(self):
        gpx_file = open("./files/planned_gpx.gpx", "r")

        gpx = gpxpy.parse(gpx_file)

        gpx_features: Gpx_features = extract_features(
            gpx, _is_recorded=False, _starting_time=0
        )

        self.assertAlmostEqual(gpx_features.distance, 6790, places=-2)
        self.assertAlmostEqual(gpx_features.elevation_gain, 280, places=-2)
        self.assertAlmostEqual(gpx_features.hiking_time, 7860, places=-3)


# by giving the file "exported_gpx.gpx" check if the weather response is the same as the one in "./files/exported_weather_info.csv" (the weather information for the exported gpx file)
# class TestWeather(unittest.TestCase):
#     def test_weather(self):
#         import pandas as pd
#         from utils.weather import analyze_weather_points
#         from utils.gpx import calculate_starting_time
#
#         gpx_file = open("./files/exported_gpx.gpx", "r")
#
#         gpx = gpxpy.parse(gpx_file)
#
#         gpx_file.close()
#
#         gpx.reduce_points(min_distance=5)
#
#         is_recorded = gpx.time is not None
#
#         starting_time = calculate_starting_time(gpx, is_recorded)
#
#         gpx_features: Gpx_features = extract_features(
#             gpx, is_recorded, _starting_time=starting_time
#         )

        # analyze_weather_points(gpx_features)
        #
        # exported_weather_info = gpx_features.weather_information
        #
        # expected_weather_info = pd.read_csv("./files/exported_weather_info.csv")
        #
        # pd.testing.assert_frame_equal(exported_weather_info, expected_weather_info)
