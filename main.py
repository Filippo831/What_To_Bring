import gpxpy
import datetime
import time
import sys
import pprint

from utils.gpx import extract_features
from utils.classes import Gpx_features
from utils.weather import analyze_weather_points
from utils.map import get_coords_information


def main():
    # check if sys.argv[-1] contains a gpx file
    if not sys.argv[-1].endswith(".gpx"):
        print("Please provide a gpx file as the last argument")
        return

    gpx_file = open(sys.argv[-1], "r")

    gpx = gpxpy.parse(gpx_file)

    # discriminate between planned gpx and recorded gpx
    is_recorded = gpx.time is not None

    if is_recorded and gpx.time is not None:
        starting_time = gpx.time
    else:
        # get tomorrows time at 9AM for the first weather point
        starting_time = datetime.datetime.now() + datetime.timedelta(days=1)
        starting_time = starting_time.replace(hour=9, minute=0, second=0, microsecond=0)

    gpx_features: Gpx_features = extract_features(gpx, _is_recorded=is_recorded)

    unix_time = time.mktime(starting_time.timetuple())

    if "--no-weather" not in sys.argv:
        analyze_weather_points(unix_time, gpx_features)

    get_coords_information(gpx_features)


if __name__ == "__main__":
    main()
