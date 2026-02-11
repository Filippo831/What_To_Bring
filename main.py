import math
import gpxpy

from helpers import haversine_distance, extract_features
from classes import Gpx_features


def main():
    gpx_file = open("./test.gpx", "r")

    gpx = gpxpy.parse(gpx_file)

    gpx_features: Gpx_features = extract_features(gpx)

    print("Total distance: " + str(gpx_features.distance))


if __name__ == "__main__":
    main()
