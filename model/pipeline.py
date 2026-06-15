import os
import xml.etree.ElementTree as ET
import re
from .api_client import get_gemini_response

def execute_analysis(xml_current_hike: str) -> dict[str, dict[str, str] | str]:
    """ 
    Executes the analysis by calling the Gemini API with the current hike data, and returns the response as a dictionary.
    It maps the item IDs in the response to their corresponding human-readable names from the input XML.
    
    Args:
        xml_current_hike: A string containing the XML data for the current hike.
        
    Returns:
        dict: A dictionary containing the Gemini API response with clothing layer recommendations and overall strategy, or an error message if the analysis fails.    
    """

    # Extract the <InputData> section from the XML
    start = xml_current_hike.find("<InputData>")
    end = xml_current_hike.rfind("</InputData>")

    if start == -1 or end == -1:
        print("Error: Input XML does not contain <InputData> tags.")
        return {"error": "Invalid input XML format. Missing <InputData> tags."}
    
    input_xml = xml_current_hike[start:end + len("</InputData>")]

    # Map item IDs to their corresponding names from the input XML
    wardrobe_map = {}
    try:
        root = ET.fromstring(input_xml)
        for item in root.findall(".//WardrobeItem"):
            item_name = item.get("name")
            item_id = item.find("Id")

            if item_id is not None and item_name:
                wardrobe_map[item_id.text] = item_name

    except ET.ParseError as pe:
        print(f"XML parsing error: {pe}")
        return {"error": "Failed to parse input XML. Please check the format of the XML data."}

    # Load system prompt from markdown file
    sprompt_path = os.path.join(os.path.dirname(__file__), "prompts/system_prompt.md")

    with open(sprompt_path, "r", encoding="utf-8") as f:
        sprompt = f.read()

    # ZERO-SHOT PROMPT
    uprompt = "Input data to be analyzed to provide clothing recommendations:\n\n"
    uprompt += f"{xml_current_hike}\n\n"

    try:
        response = get_gemini_response(system_prompt=sprompt, user_prompt=uprompt)

        response_dict = response.model_dump() # Convert Pydantic model to dictionary for easier manipulation

        # Map item IDs in the response to their corresponding names from the input XML
        layers = ["base", "middle", "insulation", "shell"]
        for layer in layers:
            for item in response_dict[layer]["items"]:
                item_id = item["id"]
                item_name = wardrobe_map.get(item_id, "Unknown Item")
                del item["id"] # Remove the id from the response as it's not needed in the final output
                item["name"] = item_name # Add the human-readable name to the response

        return response_dict
    
    except Exception as e:
        print(f"Error executing analysis: {e}")
        return {"error": "Failed to execute analysis. Please check logs for details."}
