import gpxpy
import json
import datetime
import time

from helpers import extract_features
from classes import Gpx_features
from weather import analyze_weather_points, get_weather

def main():
    gpx_file = open("./test.gpx", "r")

    gpx = gpxpy.parse(gpx_file)

    gpx_features: Gpx_features = extract_features(gpx)

    # get tomorrows time at 9AM for the first weather point
    starting_time = datetime.datetime.now() + datetime.timedelta(days=1)
    starting_time = starting_time.replace(hour=9, minute=0, second=0, microsecond=0)

    unix_time = time.mktime(starting_time.timetuple())

    analyze_weather_points(unix_time, gpx_features)

    # for information in gpx_features.weather_information:
    #     print(information)



if __name__ == "__main__":
    main()
