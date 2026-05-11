# Gpx reader

A small CLI tool to analyze GPX routes and produce summarized route features, weather forecasts, and surface/climb information.

Features
- Extracts route features from a GPX file: total distance, elevation gain, and estimated hiking time.
- Identifies and summarizes climbs (length, elevation gain, gradient, start distance/elevation).
- Samples weather forecasts along the route (one point per km) using the Open-Meteo API.
- Analyzes path surface types (asphalt, path, mountain_hiking, alpine_hiking) using local map data.
- Exports a compact XML report containing distance, elevation, hiking time, weather datapoints, surfaces, and climbs.

Usage
- Run the script with a GPX file as the last argument: `python main.py <route.gpx>`.
- Optional flag: `--no-weather` to skip weather lookups.

Implementation notes
- GPX parsing and feature extraction: `utils/gpx.py`.
- Weather fetching and processing: `utils/weather.py`.
- Map surface analysis: `utils/map.py` (uses a local GeoPackage defined in `utils/constants.py`).
- XML export: `utils/xml.py`.
- Data models: `utils/classes.py`.

Output
- The default XML report is written to `files/exported_xml.xml`.
