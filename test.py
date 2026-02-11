import unittest
from classes import Point
from helpers import haversine_distance


# if the input is 9.960 the result should be around 0.0075356
class TestHaversine(unittest.TestCase):
    def test_haversine_distance(self):
        first = Point(38.898, -77.037)
        second = Point(48.858, 2.294)

        self.assertAlmostEqual(
            haversine_distance(first, second) / 1000, 6161.6, places=1
        )
