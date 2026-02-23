import unittest
from classes import Point, Gpx_features
from helpers import haversine_distance, extract_features
import gpxpy



# if the input is 9.960 the result should be around 0.0075356
class TestHaversine(unittest.TestCase):
    def test_haversine_distance(self):
        first = Point(38.898, -77.037)
        second = Point(48.858, 2.294)

        self.assertAlmostEqual(
            haversine_distance(first, second) / 1000, 6161.6, places=1
        )

class TestFeaturesExtraction(unittest.TestCase):
    def test_features_extract(self):
        gpx_file = open("./test.gpx", "r")

        gpx = gpxpy.parse(gpx_file)

        gpx_features: Gpx_features = extract_features(gpx)

        self.assertAlmostEqual(gpx_features.distance, 6790, places=-2)
        self.assertAlmostEqual(gpx_features.elevation_gain, 280, places=-2)
        self.assertAlmostEqual(gpx_features.hiking_time, 7860, places=-3)


class TestMapFeaturesExtraction(unittest.TestCase):
    def test_map_features_exctract(self):
        gpx_file = open("./test.gpx", "r")

        gpx = gpxpy.parse(gpx_file)

        gpx_features: Gpx_features = extract_features(gpx)

