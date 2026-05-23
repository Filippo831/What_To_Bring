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
MAP_PATH = "./assets/map/nord-est-latest.osm.pbf"
