"""
Mock implementation for testing
"""

def run_model(xml_input: str) -> dict:

    # real logic to be integrated

    _ = xml_input  # unused in mock – will be used in real implementation

    return {
        "base": {
            "motivation": "[MOCK] Synthetic short-sleeve base layer for active breathability",
            "items": [
                {"position": "worn", "name": "Men's Hiking Synthetic SS T-Shirt MH500"},
            ],
        },
        "middle": {
            "motivation": "[MOCK] Light fleece worn at the cool start, shed once climbing begins",
            "items": [
                {"position": "worn", "name": "Men's MH120 Hiking Fleece Zip"},
            ],
        },
        "insulation": {
            "motivation": "[MOCK] Not needed for the expected temperature range",
            "items": [],
        },
        "shell": {
            "motivation": "[MOCK] Packed in case of the forecast precipitation",
            "items": [
                {"position": "backpack", "name": "Men's Ultra-Light Rain Jacket FH500"},
            ],
        },
        "pants": {
            "motivation": "[MOCK] Not yet validated",
            "items": [],
        },
        "shoes": {
            "motivation": "[MOCK] Not yet validated",
            "items": [],
        },
        "gear": {
            "motivation": "[MOCK] Not yet validated",
            "items": [],
        },
        "overall_strategy": "[MOCK] Calibrated to score perfectly on the validated categories of sample 00",
    }
