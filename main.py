import gpxpy
import sys
import pprint

from utils.gpx import extract_features, calculate_starting_time
from utils.classes import Gpx_features
from utils.weather import analyze_weather_points
from utils.map import analyze_path


def main():
    # check if sys.argv[-1] contains a gpx file
    if not sys.argv[-1].endswith(".gpx"):
        print("Please provide a gpx file as the last argument")
        return

    gpx_file = open(sys.argv[-1], "r")

    gpx = gpxpy.parse(gpx_file)

    # discriminate between planned gpx and recorded gpx
    is_recorded = gpx.time is not None

    starting_time = calculate_starting_time(gpx, is_recorded)

    # reduce the amount of points in the gpx
    gpx.reduce_points(min_distance=5)

    gpx_features: Gpx_features = extract_features(
        gpx, _is_recorded=is_recorded, _starting_time=starting_time
    )

    if "--no-weather" not in sys.argv:
        analyze_weather_points(gpx_features)

    analyze_path(gpx_features)



if __name__ == "__main__":
    main()
