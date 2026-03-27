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

        gpx_features: Gpx_features = extract_features(gpx, _is_recorded=False, _starting_time=0)

        self.assertAlmostEqual(gpx_features.distance, 6790, places=-2)
        self.assertAlmostEqual(gpx_features.elevation_gain, 280, places=-2)
        self.assertAlmostEqual(gpx_features.hiking_time, 7860, places=-3)



