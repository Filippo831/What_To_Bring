import io
import gpxpy
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


def gpx_analyzer(
    gpx_content: str,
    _xml_root: ET.Element,
    _starting_time: str | None = None,
    use_weather: bool = True,
):
    gpx = gpxpy.parse(io.StringIO(gpx_content))

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

    gpx_features: Gpx_features = extract_features(
        gpx, _is_recorded=is_recorded, _starting_time=starting_time
    )

    if use_weather:
        analyze_weather_points(gpx_features)

    analyze_path(gpx_features)

    export_xml(gpx_features, _xml_root)
