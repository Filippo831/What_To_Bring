"""
Mock implementation for testing
"""

from typing import TypedDict


class ModelOutput(TypedDict):
    suggested_items: list[str]
    # other fields may be added


def run_model(xml_input: str) -> ModelOutput:

    # real logic to be integrated

    _ = xml_input  # unused in mock – will be used in real implementation

    return ModelOutput(
        suggested_items=[
            "Men's Hiking Synthetic SS T-Shirt MH500",
            "Men's MH120 Hiking Fleece Zip",
            "Men's Ultra-Light Rain Jacket FH500",
        ]
    )