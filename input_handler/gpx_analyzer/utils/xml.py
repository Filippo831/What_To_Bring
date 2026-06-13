import xml.etree.ElementTree as ET

from input_handler.gpx_analyzer.utils.classes import Gpx_features
from input_handler.utils.string_conversion import underscore_to_camel_case


def export_xml(_gpx_features: Gpx_features, _xml_root: ET.Element):
    root = ET.SubElement(_xml_root, "GPXFeatures")

    ET.SubElement(root, "Distance", units="km").text = str(
        _gpx_features.distance / 1000
    )
    ET.SubElement(root, "ElevationGain", units="m").text = str(
        _gpx_features.elevation_gain
    )
    ET.SubElement(root, "HikingTime", units="minutes").text = str(
        round(_gpx_features.hiking_time / 60)
    )

    weather_root = ET.SubElement(root, "WeatherForecast")
    for i, info in enumerate(_gpx_features.weather_information, start=0):
        # Create a point for each kilometer
        dp = ET.SubElement(weather_root, "DataPoint", kilometer=str(i))
        for key, value in info.items():
            child = ET.SubElement(dp, underscore_to_camel_case(key))
            child.text = str(value)

    surfaces_root = ET.SubElement(root, "Surfaces")
    for surface_type, percentage in _gpx_features.surface_percentage.items():
        s_elem = ET.SubElement(surfaces_root, "Surface", type=surface_type)
        s_elem.text = str(percentage)

    climbs_root = ET.SubElement(root, "Climbs")
    for climb in _gpx_features.climbs:
        c_elem = ET.SubElement(climbs_root, "Climb")
        ET.SubElement(c_elem, "Length").text = str(climb.length)
        ET.SubElement(c_elem, "Gain").text = str(climb.elevation_gain)
        ET.SubElement(c_elem, "Gradient").text = str(climb.gradient)
        ET.SubElement(c_elem, "StartDistance").text = str(climb.starting_distance)
        ET.SubElement(c_elem, "StartElevation").text = str(climb.starting_elevation)

    # raw_xml = ET.tostring(root, encoding="utf-8")  # pyright: ignore[reportAny]
    #
    # reparsed = minidom.parseString(raw_xml)  # pyright: ignore[reportAny]
    # pretty_xml = reparsed.toprettyxml(indent="    ")
    #
    # with open(_output_file, "w", encoding="utf-8") as f:
    #     _ = f.write(pretty_xml)
