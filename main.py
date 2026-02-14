import math
import gpxpy
import pprint

from helpers import haversine_distance, extract_features
from classes import Gpx_features


def main():
    gpx_file = open("./test.gpx", "r")

    gpx = gpxpy.parse(gpx_file)

    gpx_features: Gpx_features = extract_features(gpx)

    # print("Total distance: " + str(gpx_features.distance))
    for climb in gpx_features.climbs:
        print("length {}, elevation {}", climb.length, climb.elevation_gain)



if __name__ == "__main__":
    main()
