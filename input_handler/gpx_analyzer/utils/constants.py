# radius of the earth in meters
RADIUS = 6371200

# the minimum gradient to consider a climb
GRADIENT = 4

# the minimum length to consider a climb
CLIMB_LENGTH = 300

# m/h used for the Naismith's rule
HIKING_SPEED = 4000

# elevation gain for each hour used for the Naismith's rule
ELEVATION_PER_HOUR = 600

# features to request from the Open-Meteo API
WEATHER_FEATURES = [
    "temperature_2m",
    "relative_humidity_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
]

# path with map osm inforamtion
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
MAP_PATH = str(_PROJECT_ROOT / "assets" / "map" / "nord-est-custom.gpkg")

# amount of years in the past to check the weather
HISTORICAL_YEARS = 5
