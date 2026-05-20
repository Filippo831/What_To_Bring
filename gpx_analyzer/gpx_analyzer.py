import gpxpy
import sys

from gpx_analyzer.utils.gpx import extract_features, calculate_starting_time
from gpx_analyzer.utils.classes import Gpx_features
from gpx_analyzer.utils.weather import analyze_weather_points
from gpx_analyzer.utils.map import analyze_path
from gpx_analyzer.utils.xml import export_xml


def gpx_analyzer():
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

    export_xml(gpx_features, "files/exported_xml.xml") 
