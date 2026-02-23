import gpxpy
import json
import datetime
import time
import sys

from helpers import extract_features
from classes import Gpx_features
from weather import analyze_weather_points, get_weather
from map import get_coords_information

def main():
    gpx_file = open("./test.gpx", "r")

    gpx = gpxpy.parse(gpx_file)

    gpx_features: Gpx_features = extract_features(gpx)

    # get tomorrows time at 9AM for the first weather point
    starting_time = datetime.datetime.now() + datetime.timedelta(days=1)
    starting_time = starting_time.replace(hour=9, minute=0, second=0, microsecond=0)

    unix_time = time.mktime(starting_time.timetuple())

    if not "--no-weather" in sys.argv:
        analyze_weather_points(unix_time, gpx_features)
        for information in gpx_features.weather_information:
            print(information)

    get_coords_information(gpx_features)




if __name__ == "__main__":
    main()
