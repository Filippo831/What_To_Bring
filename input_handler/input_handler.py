# pyright: basic

import json
import xml.etree.ElementTree as ET
from pathlib import Path
from xml.dom import minidom
import pandas as pd

from input_handler.gpx_analyzer.gpx_analyzer import gpx_analyzer
from input_handler.utils.string_conversion import underscore_to_camel_case

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_WARDROBE_CATALOG = _PROJECT_ROOT / "assets" / "wardrobe" / "decathlon_hiking_clothes_catalog.csv"


def load_wardrobe_catalog() -> pd.DataFrame:
    return pd.read_csv(_WARDROBE_CATALOG)


def build_input_xml(
    course_gpx: str,
    personal_info: dict,
    hike_info: dict,
    *,
    use_weather: bool = True,
) -> str:
    """
    Build the <InputData> XML for a hike.

    Args:
        course_gpx: content of the GPX file
        personal_info: parsed personal_information.json (name, wardrobe, ...)
        hike_info: parsed hike_information.json (starting_time, type, ...)
        use_weather: whether to fetch the weather forecast (network call)

    Returns:
        str: pretty-printed XML
    """
    starting_time = hike_info.get("starting_time")

    # base xml file
    xml_root = ET.Element("InputData")

    personal_information_element = ET.SubElement(xml_root, "PersonalInformation")
    wardrobe_list_element = ET.SubElement(xml_root, "Wardrobe")

    wardrobe_df = load_wardrobe_catalog()
    for key, value in personal_info.items():
        if key == "wardrobe":
            for item in value:
                item_info = wardrobe_df[wardrobe_df["Product_Name"] == item]
                if not item_info.empty:
                    item_element = ET.SubElement(
                        wardrobe_list_element, "WardrobeItem", name=item
                    )
                    for col in wardrobe_df.columns:
                        if col != "Product_Name":
                            col_value = item_info.iloc[0][col]
                            if (col_value is not None) and (not pd.isna(col_value)):
                                col_element = ET.SubElement(item_element, underscore_to_camel_case(col))
                                col_element.text = str(col_value)
        else:
            child = ET.SubElement(personal_information_element, underscore_to_camel_case(key))
            # if the value indicates the heat tolerance, store the value as a score out of 10
            if key == "heat_tolerance":
                child.text = str(value) + "/10"
            else:
                child.text = str(value)

    gpx_analyzer(course_gpx, xml_root, starting_time, use_weather=use_weather)

    activity_type = hike_info.get("type")
    if activity_type is not None:
        child = ET.SubElement(xml_root, "ActivityType")
        child.text = str(activity_type)

    raw_xml = ET.tostring(xml_root, encoding="utf-8")  # pyright: ignore[reportAny]

    reparsed = minidom.parseString(raw_xml)  # pyright: ignore[reportAny]
    pretty_xml = reparsed.toprettyxml(indent="    ")

    return pretty_xml


def input_handler(_sample: dict[str, str]):
    # read the json file sample["hike_information"] and get the value under "starting_time". If not present set starting_time to None
    with open(_sample["hike_information"], "r") as f:
        hike_info = json.load(f)

    with open(_sample["personal_information"], "r") as f:
        personal_info = json.load(f)

    course_gpx = Path(_sample["course"]).read_text(encoding="utf-8")

    pretty_xml = build_input_xml(course_gpx, personal_info, hike_info)

    # write the xml_root content to output.xml
    xml_output_path = _sample["course"].replace("course.gpx", "output.xml")

    with open(xml_output_path, "w", encoding="utf-8") as f:
        _ = f.write(pretty_xml)
        f.flush()
