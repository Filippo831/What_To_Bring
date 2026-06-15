import json
from model.pipeline import execute_analysis

if __name__ == "__main__":

    xml_path = r"samples/00/output.xml"

    with open(xml_path, "r", encoding="utf-8") as f:
        xml_current_hike = f.read()
    
    result = execute_analysis(xml_current_hike=xml_current_hike)

    print("Test Result:")

    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print("Gemini API Response:")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        json_output_path = r"analysis_output.json"
        with open(json_output_path, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=4, ensure_ascii=False)
        print(f"Response saved to {json_output_path}")