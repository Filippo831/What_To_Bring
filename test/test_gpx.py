import unittest
from pathlib import Path
from gpxpy.gpx import GPXTrackPoint
import pandas as pd
from input_handler.gpx_analyzer.utils.classes import Point, Gpx_features, Climb
from input_handler.gpx_analyzer.utils.gpx import haversine_distance, extract_features
from input_handler.gpx_analyzer.utils.map import extract_sac_scale, extract_mtb_scale, process_row
import gpxpy
import math

# paths anchored to the project root (two levels up from this file: test/ → root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_GPX_FILES_DIR = _PROJECT_ROOT / "input_handler" / "gpx_analyzer" / "files"


class TestHaversine(unittest.TestCase):
    def test_haversine_distance(self):
        # create 2 points of type GPXTrakckPoint with these coordinates: (38.898, -77.037) and (48.858, 2.294) and calculate the distance between them using the haversine_distance function. The expected distance is 6161.6 km.
        first = GPXTrackPoint(latitude=38.898, longitude=-77.037, elevation=0)
        second = GPXTrackPoint(latitude=48.858, longitude=2.294, elevation=0)


        self.assertAlmostEqual(
            haversine_distance(first, second) / 1000, 6161.6, places=1
        )


class TestFeaturesExtraction(unittest.TestCase):
    def test_features_extract(self):
        gpx_file = open(_GPX_FILES_DIR / "planned_gpx.gpx", "r")

        gpx = gpxpy.parse(gpx_file)

        gpx_features: Gpx_features = extract_features(
            gpx, _is_recorded=False, _starting_time=0
        )

        self.assertAlmostEqual(gpx_features.distance, 6790, places=-2)
        self.assertAlmostEqual(gpx_features.elevation_gain, 280, places=-2)
        self.assertAlmostEqual(gpx_features.hiking_time, 7860, places=-3)


class TestClasses(unittest.TestCase):
    def test_point_initialization(self):
        p = Point(45.0, 7.0, 1000, 500, 1600000000)
        self.assertEqual(p.latitude, 45.0)
        self.assertEqual(p.longitude, 7.0)
        self.assertEqual(p.cumulative_distance, 1000)
        self.assertEqual(p.elevation, 500)
        self.assertEqual(p.time, 1600000000)


class TestGpxFeaturesMethods(unittest.TestCase):
    def test_gpx_features_mutators(self):
        gf = Gpx_features()
        self.assertEqual(gf.distance, 0)

        gf.set_distance(1234.5)
        self.assertAlmostEqual(gf.distance, 1234.5)

        gf.set_elevation_gain(250)
        self.assertEqual(gf.elevation_gain, 250)

        gf.set_hiking_time(3600)
        self.assertEqual(gf.hiking_time, 3600)

        p = Point(1, 2, 3, 4, 5)
        gf.append_point(p)
        self.assertIs(gf.points[-1], p)

        wp = Point(3, 4, 5, 6, 7)
        gf.append_weather_point(wp)
        self.assertIs(gf.weather_points[-1], wp)

        c = Climb(Point(0, 0, 0, 10, 0), Point(0, 0, 100, 20, 0))
        gf.add_climbs(c)
        self.assertIs(gf.climbs[-1], c)

        sp = {"asphalt": 80.0, "mountain_hiking": 20.0}
        gf.set_surface_percentage(sp)
        self.assertEqual(gf.surface_percentage, sp)


class TestExtractPercentages(unittest.TestCase):
    def test_extract_percentages(self):
        gpx_file = open("./input_handler/gpx_analyzer/files/planned_gpx.gpx", "r")

        gpx = gpxpy.parse(gpx_file)

        gpx_features: Gpx_features = extract_features(
            gpx, _is_recorded=False, _starting_time=0
        )

        expected_percentages = {"asphalt": 60, "path": 33, "mountain_hiking": 7}

        for k in gpx_features.surface_percentage.keys():
            assert math.isclose(
                gpx_features.surface_percentage[k],
                expected_percentages[k],
                rel_tol=0.05,
            )


class TestMapHelpers(unittest.TestCase):
    def test_extract_scales_and_process_row(self):
        tags = '"sac_scale"=>"mountain_hiking" "mtb:scale"=>"3" "surface"=>"gravel"'

        self.assertEqual(extract_sac_scale(tags), "mountain_hiking")
        self.assertEqual(extract_mtb_scale(tags), "3")

        row = pd.Series({"other_tags": tags, "highway": "track"})
        res = process_row(row)
        self.assertEqual(res["surface"], "gravel")

        # test fallback when tags are missing
        row_missing = pd.Series({"other_tags": pd.NA, "highway": "track"})
        res_missing = process_row(row_missing)
        self.assertEqual(res_missing["surface"], "ground")


if __name__ == "__main__":
    unittest.main()
