import json
from model.pipeline import execute_analysis

if __name__ == "__main__":
    
    result = execute_analysis(xml_current_hike="output.xml")

    print("Test Result:")

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("Gemini API Response:")
        print(json.dumps(result, indent=4, ensure_ascii=False))