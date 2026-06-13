# pyright: basic

from input_handler.gpx_analyzer.gpx_analyzer import gpx_analyzer
from input_handler.utils.string_conversion import underscore_to_camel_case
import xml.etree.ElementTree as ET
from xml.dom import minidom
import json
import pandas as pd


def input_handler(_sample: dict[str, str]):
    # read the json file sample["hike_information"] and get the value under "starting_time". If not present set starting_time to None
    with open(_sample["hike_information"], "r") as f:
        hike_information = json.load(f)
        starting_time = hike_information.get("starting_time", None)

    # base xml file
    xml_root = ET.Element("InputData")

    """
    read the value inside _sample["personal_information"] json file and add 
    to the xml_root as a child all the values inside the json file
    """
    with open(_sample["personal_information"], "r") as f:
        personal_information = json.load(f)
        personal_information_element = ET.SubElement(
            xml_root, "PersonalInformation"
        )
        wardrobe_list_element = ET.SubElement(
            xml_root, "Wardrobe"
        )
        for key, value in personal_information.items():
            if key != "wardrobe":
                # if the value indicates the heat tolerance, store the value as a score out of 10
                if key == "heat_tolerance":
                    child = ET.SubElement(personal_information_element, underscore_to_camel_case(key))
                    child.text = str(value) + "/10"
                else:
                    child = ET.SubElement(personal_information_element, underscore_to_camel_case(key))
                    child.text = str(value)

            if key == "wardrobe":
                """
                take the value, look inside ./assets/wardrobe/decathlon_hiking_clothes_catalog.csv.
                Load the values with pandas
                Look for the item in the column "Product Name" and then get all the values in 
                the other columns encoding them as column title: value
                """
                wardrobe_df = pd.read_csv(
                    "./assets/wardrobe/decathlon_hiking_clothes_catalog.csv"
                )
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

    gpx_analyzer(_sample["course"], xml_root, starting_time)

    """
    read the value inside _sample["hike_information"] json file and add 
    to the xml_root as a child the value under "type" key
    """
    with open(_sample["hike_information"], "r") as f:
        hike_information = json.load(f)
        activity_type = hike_information.get("type", None)
        if activity_type is not None:
            child = ET.SubElement(xml_root, "ActivityType")
            child.text = str(activity_type)

    # write the xml_root content to output.xml
    xml_output_path = _sample["course"].replace("course.gpx", "output.xml")

    raw_xml = ET.tostring(xml_root, encoding="utf-8")  # pyright: ignore[reportAny]

    reparsed = minidom.parseString(raw_xml)  # pyright: ignore[reportAny]
    pretty_xml = reparsed.toprettyxml(indent="    ")

    with open(xml_output_path, "w", encoding="utf-8") as f:
        _ = f.write(pretty_xml)
        f.flush()
