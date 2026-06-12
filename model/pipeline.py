import os
from .api_client import get_gemini_response

def execute_analysis(xml_current_hike: str) -> dict[str, dict[str, str] | str]:
    """ 
    Executes the analysis by calling the Gemini API with the current and previous hike data, and returns the response as a dictionary.
    
    Args:
        xml_current_hike: A string containing the XML data for the current hike.
        
    Returns:
        dict: A dictionary containing the Gemini API response with clothing layer recommendations and overall strategy, or an error message if the analysis fails.    
    """

    sprompt_path = os.path.join(os.path.dirname(__file__), "prompts/system_prompt.md")

    with open(sprompt_path, "r", encoding="utf-8") as f:
        sprompt = f.read() # Load system prompt from markdown file

    # ZERO-SHOT PROMPT
    uprompt = "Input data to be analyzed to provide clothing recommendations:\n\n"
    uprompt += f"{xml_current_hike}\n\n"

    try:
        response = get_gemini_response(system_prompt=sprompt, user_prompt=uprompt)
        return response.model_dump() # Return the response as a dictionary
    
    except Exception as e:
        print(f"Error executing analysis: {e}")
        return {"error": "Failed to execute analysis. Please check logs for details."}
