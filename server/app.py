import json
import xml.etree.ElementTree as ET
from math import isfinite
from typing import Callable, Optional

from flask import Flask, jsonify, request, send_from_directory

from input_handler.input_handler import build_input_xml

ModelFn = Callable[[str], dict]

_WEATHER_FIELDS = {
    "temperature_2m": "Temperature2m",
    "relative_humidity_2m": "RelativeHumidity2m",
    "apparent_temperature": "ApparentTemperature",
    "precipitation_probability": "PrecipitationProbability",
    "precipitation": "Precipitation",
}


def _float_or_none(el: Optional[ET.Element]) -> Optional[float]:
    if el is None or el.text is None:
        return None
    try:
        value = float(el.text)
    except ValueError:
        return None
    return value if isfinite(value) else None


def extract_hike_features(xml_input: str) -> dict:
    root = ET.fromstring(xml_input)
    gpx = root.find("GPXFeatures")
    if gpx is None:
        return {}

    features = {
        "distance_km": _float_or_none(gpx.find("Distance")),
        "elevation_gain_m": _float_or_none(gpx.find("ElevationGain")),
        "hiking_time_minutes": _float_or_none(gpx.find("HikingTime")),
    }

    weather = []
    for dp in gpx.findall("WeatherForecast/DataPoint"):
        kilometer = dp.get("kilometer")
        point = {"kilometer": int(kilometer) if kilometer else None}
        for key, tag in _WEATHER_FIELDS.items():
            point[key] = _float_or_none(dp.find(tag))
        weather.append(point)

    surfaces = {}
    for s in gpx.findall("Surfaces/Surface"):
        if s.get("type") is not None:
            surfaces[s.get("type")] = _float_or_none(s)

    climbs = []
    for c in gpx.findall("Climbs/Climb"):
        climbs.append(
            {
                "length": _float_or_none(c.find("Length")),
                "gain": _float_or_none(c.find("Gain")),
                "gradient": _float_or_none(c.find("Gradient")),
                "start_distance": _float_or_none(c.find("StartDistance")),
                "start_elevation": _float_or_none(c.find("StartElevation")),
            }
        )

    features["weather"] = weather
    features["surfaces"] = surfaces
    features["climbs"] = climbs
    return features


def create_app(model_fn: Optional[ModelFn] = None) -> Flask:
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

    if model_fn is None:

        def _default_model(xml_input: str) -> dict:
            from model.pipeline import execute_analysis

            return execute_analysis(xml_input)

        model_fn = _default_model

    def _read_json_input(field: str) -> dict:
        uploaded = request.files.get(field)
        if uploaded is not None:
            raw = uploaded.read().decode("utf-8")
        else:
            raw = request.form.get(field)
        if raw is None:
            raise ValueError(f"Missing '{field}' (file upload or JSON text)")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in '{field}': {e}")
        if not isinstance(data, dict):
            raise ValueError(f"'{field}' must be a JSON object")
        return data

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok"})

    @app.post("/api/estimate")
    def estimate():
        gpx_file = request.files.get("gpx")
        if gpx_file is None:
            return jsonify({"error": "Missing 'gpx' file upload"}), 400
        gpx_content = gpx_file.read().decode("utf-8")

        try:
            personal_info = _read_json_input("personal_information")
            hike_info = _read_json_input("hike_information")
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

        try:
            xml_input = build_input_xml(gpx_content, personal_info, hike_info)
        except Exception as e:
            return jsonify({"error": f"Failed to process the input: {e}"}), 422

        model_output = model_fn(xml_input)
        if not isinstance(model_output, dict) or "error" in model_output:
            error = (
                model_output["error"]
                if isinstance(model_output, dict)
                else f"Model returned {type(model_output).__name__}"
            )
            return jsonify({"error": f"Model execution failed: {error}"}), 500

        try:
            hike_features = extract_hike_features(xml_input)
        except ET.ParseError:
            hike_features = {}

        recommendations = {
            k: v for k, v in model_output.items() if k != "overall_strategy"
        }

        return jsonify(
            {
                "hike_features": hike_features,
                "recommendations": recommendations,
                "overall_strategy": model_output.get("overall_strategy"),
            }
        )

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "Request too large (max 16MB)"}), 413

    @app.errorhandler(Exception)
    def internal_error(e):
        return jsonify({"error": f"Internal server error: {e}"}), 500

    return app
