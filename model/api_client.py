import os
import random
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from google.genai import errors as genai_errors
from pydantic import BaseModel, Field, ValidationError
from enum import Enum

# Maximum retries to avoid problems with Gemini
MAX_RETRIES = 5
BACKOFF_BASE_SECONDS = 1.0

"""
This module defines the data models and API client for interacting with the Gemini API. It includes:
- Position: An enumeration for item positions (worn, backpack, null).
- Layer: A Pydantic model representing a clothing layer with motivation, item, and position.
- GeminiResponse: A Pydantic model representing the structured response from the Gemini API, including layers and overall strategy.
- get_gemini_response: A function that takes system and user prompts, calls the Gemini API, and returns a validated GeminiResponse object. It includes error handling for API call failures and schema validation issues.
"""

class Position(str, Enum):
    WORN = "worn"
    BACKPACK = "backpack"

class ClothingItem(BaseModel):
    id: str = Field(..., description="Id field of the clothing item copied and pasted from xml tag <WardrobeItem> in the input xml file")
    position: Position

class Layer(BaseModel):
    motivation: str
    items: list[ClothingItem]

class PantsEnum(str, Enum):
    SHORTS = "shorts"
    LONG_PANTS = "long pants"
    RAIN_PANTS = "rain pants"

class ShoesEnum(str, Enum):
    HIGH_SHOES = "high shoes"
    LOW_SHOES = "low shoes"
    MOUNTAINEERING_SHOES = "mountaineering shoes"
    TRAIL_RUNNING_SHOES = "trail running shoes"

class PantsItem(BaseModel):
    name: PantsEnum
    position: Position

class ShoesItem(BaseModel):
    name: ShoesEnum
    position: Position

class GearItem(BaseModel):
    name: str = Field(..., description="Name of recommended gear item. Backpack is not included in this list as it is always recommended.")

class Pants(BaseModel):
    motivation: str
    items: list[PantsItem]

class Shoes(BaseModel):
    motivation: str
    items: list[ShoesItem]

class GearRecommendation(BaseModel):
    motivation: str
    items: list[GearItem]

class GeminiResponse(BaseModel):
    base: Layer
    middle: Layer
    insulation: Layer
    shell: Layer
    pants: Pants
    shoes: Shoes
    gear: GearRecommendation
    overall_strategy: str

# Initialize Gemini API client
load_dotenv()

# Load Gemini API key from environment variable
API_KEY = os.environ.get("GEMINI_API_KEY")

client = genai.Client(api_key=API_KEY, http_options=types.HttpOptions(timeout=60000))


def _is_transient_error(exc: Exception) -> bool:
    """True for errors worth retrying (server overload, timeouts, dropped connections).

    False for errors that will fail identically on every retry (bad API key,
    invalid request, schema mismatch), which should be raised immediately.
    """
    if isinstance(exc, genai_errors.APIError):
        code = getattr(exc, "code", None)

        # Exausted resources on Gemini APIs
        if code == 429:
            return False
        
        return getattr(exc, "code", None) in (408, 500, 502, 503, 504)
    # Low-level network errors (e.g. "Server disconnected without sending a response")
    # don't always come wrapped as APIError, so fall back to matching on the message.
    message = str(exc).lower()
    transient_markers = (
        "503",
        "unavailable",
        "high demand",
        "overloaded",
        "server disconnected",
        "timeout",
        "timed out",
        "connection reset",
        "connection aborted",
    )
    return any(marker in message for marker in transient_markers)

def get_gemini_response(system_prompt: str, user_prompt: str) -> GeminiResponse:
    """ Calls the Gemini API with the provided system and user prompts, and returns a validated GeminiResponse object.

    Args:
        system_prompt: The system instruction for the Gemini model.
        user_prompt: The user query or input for the Gemini model.

    Returns:
        GeminiResponse: A validated response object containing clothing layer recommendations and overall strategy.

    Raises:
        ValueError: If the Gemini API call fails or if the response does not match the expected schema.
    """
    last_error: Exception | None = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = client.models.generate_content(
                model = 'gemini-3.5-flash-lite',
                contents = user_prompt,
                config = types.GenerateContentConfig(
                    system_instruction = system_prompt,
                    temperature = 0.2,
                    response_mime_type = "application/json",
                    response_schema = GeminiResponse.model_json_schema(),
                ),
            )

            response_text = response.text
            if response_text is None:
                raise ValueError("Received empty response from Gemini API.")

            validated_response = GeminiResponse.model_validate_json(response_text)
            return validated_response

        except ValidationError as ve:
            # A schema mismatch will not fix itself on retry: fail immediately.
            print(f"Pydantic validation error (JSON schema mismatch): {ve}")
            raise ValueError("Received response does not match expected schema.") from ve

        except Exception as e:
            last_error = e

            if isinstance(e, genai_errors.APIError) and getattr(e, "code", None) == 429:
                print(f"Gemini API rate limit exceeded (attempt {attempt}/{MAX_RETRIES}): {e}")
                raise ValueError("Gemini API rate limit exceeded.") from e
            
            if not _is_transient_error(e) or attempt == MAX_RETRIES:
                print(f"Error during Gemini API call (attempt {attempt}/{MAX_RETRIES}): {e}")
                raise ValueError("Error occurred while calling Gemini API.") from e

            delay = BACKOFF_BASE_SECONDS * (2 ** (attempt - 1)) + random.uniform(0, 1)
            print(
                f"Transient Gemini API error (attempt {attempt}/{MAX_RETRIES}): {e} "
                f"-> retrying in {delay:.1f}s"
            )
            time.sleep(delay)

    # Should be unreachable (the loop always returns or raises), but keeps type checkers happy.
    raise ValueError("Error occurred while calling Gemini API.") from last_error