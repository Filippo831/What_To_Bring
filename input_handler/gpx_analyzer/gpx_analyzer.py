import gpxpy
import sys

from input_handler.gpx_analyzer.utils.gpx import extract_features, calculate_starting_time
from input_handler.gpx_analyzer.utils.classes import Gpx_features
from input_handler.gpx_analyzer.utils.weather import analyze_weather_points
from input_handler.gpx_analyzer.utils.map import analyze_path
from input_handler.gpx_analyzer.utils.xml import export_xml


def gpx_analyzer():
    # check if sys.argv[-1] contains a gpx file
    if not sys.argv[-1].endswith(".gpx"):
        print("Please provide a gpx file as the last argument")
        return

    gpx_file = open(sys.argv[-1], "r")

    print(f"Analyzing {sys.argv[-1]}...")
    gpx = gpxpy.parse(gpx_file)
    print("GPX file parsed successfully")

    # discriminate between planned gpx and recorded gpx
    is_recorded = gpx.time is not None

    starting_time = calculate_starting_time(gpx, is_recorded)

    # reduce the amount of points in the gpx
    gpx.reduce_points(min_distance=5)

    print("Extracting features from the GPX file...")
    gpx_features: Gpx_features = extract_features(
        gpx, _is_recorded=is_recorded, _starting_time=starting_time
    )
    print("Features extracted successfully")

    print("Analyzing weather points...")
    if "--no-weather" not in sys.argv:
        analyze_weather_points(gpx_features)
    print("Weather points analyzed successfully")

    print("Analyzing path information...")
    analyze_path(gpx_features)
    print("Path information analyzed successfully")

    export_xml(gpx_features, "./assets/export/exported_xml.xml") 
