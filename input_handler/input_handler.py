from input_handler.gpx_analyzer.gpx_analyzer import gpx_analyzer
import json

def input_handler(_sample: dict[str, str]):
    # read the json file sample["hike_information"] and get the value under "starting_time". If not present set starting_time to None
    with open(_sample["hike_information"], "r") as f:
        hike_information = json.load(f)
        starting_time = hike_information.get("starting_time", None)

    gpx_analyzer(_sample["course"], starting_time)
