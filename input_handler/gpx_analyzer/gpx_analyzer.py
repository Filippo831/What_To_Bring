import gpxpy
import sys
import xml.etree.ElementTree as ET

from datetime import datetime

from input_handler.gpx_analyzer.utils.gpx import (
    extract_features,
    calculate_starting_time,
)
from input_handler.gpx_analyzer.utils.classes import Gpx_features
from input_handler.gpx_analyzer.utils.weather import analyze_weather_points
from input_handler.gpx_analyzer.utils.map import analyze_path
from input_handler.gpx_analyzer.utils.xml import export_xml


def gpx_analyzer(_gpx_file_path: str, _xml_root: ET.Element, _starting_time: str | None = None):
    gpx_file = open(_gpx_file_path, "r")

    print(f"Analyzing {_gpx_file_path}...")
    gpx = gpxpy.parse(gpx_file)
    print("GPX file parsed successfully")

    # discriminate between planned gpx and recorded gpx
    is_recorded = gpx.time is not None or gpx.tracks[0].segments[0].points[0].time is not None
    starting_time: int = 0

    if is_recorded:
        starting_time = calculate_starting_time(gpx)
    else:
        if _starting_time is not None:
            date_format = "%Y-%m-%d %H:%M"

            dt_obj = datetime.strptime(_starting_time, date_format)

            starting_time = int(dt_obj.timestamp())

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

    export_xml(gpx_features, _xml_root)

