import io
import json
import unittest
from pathlib import Path
from unittest import mock

from server.app import create_app, extract_hike_features

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

FAKE_XML = """<?xml version="1.0" ?>
<InputData>
  <GPXFeatures>
    <Distance units="km">10.1</Distance>
    <ElevationGain units="m">752.7</ElevationGain>
    <HikingTime units="minutes">227</HikingTime>
    <WeatherForecast>
      <DataPoint kilometer="0">
        <Temperature2m>9.8</Temperature2m>
        <RelativeHumidity2m>56.0</RelativeHumidity2m>
        <ApparentTemperature>nan</ApparentTemperature>
        <PrecipitationProbability>3.0</PrecipitationProbability>
        <Precipitation>0.0</Precipitation>
      </DataPoint>
    </WeatherForecast>
    <Surfaces>
      <Surface type="asphalt">6.99</Surface>
      <Surface type="hiking">15.57</Surface>
    </Surfaces>
    <Climbs>
      <Climb>
        <Length>1861.4</Length>
        <Gain>365.01</Gain>
        <Gradient>19.6</Gradient>
        <StartDistance>1147.5</StartDistance>
        <StartElevation>1563.3</StartElevation>
      </Climb>
    </Climbs>
  </GPXFeatures>
  <ActivityType>hike</ActivityType>
</InputData>
"""


def _fake_model(xml_input: str) -> dict:
    return {
        "base": {
            "motivation": "m",
            "items": [{"position": "worn", "name": "BaseA"}],
        },
        "middle": {"motivation": "m", "items": []},
        "insulation": {"motivation": "m", "items": []},
        "shell": {"motivation": "m", "items": []},
        "pants": {"motivation": "m", "items": []},
        "shoes": {"motivation": "m", "items": []},
        "gear": {"motivation": "m", "items": []},
        "overall_strategy": "strategy",
    }


class TestExtractHikeFeatures(unittest.TestCase):
    def test_extracts_all_sections(self):
        features = extract_hike_features(FAKE_XML)

        self.assertEqual(features["distance_km"], 10.1)
        self.assertEqual(features["elevation_gain_m"], 752.7)
        self.assertEqual(features["hiking_time_minutes"], 227)
        self.assertEqual(features["surfaces"], {"asphalt": 6.99, "hiking": 15.57})
        self.assertEqual(features["climbs"][0]["gradient"], 19.6)
        self.assertEqual(features["weather"][0]["kilometer"], 0)
        self.assertEqual(features["weather"][0]["temperature_2m"], 9.8)

    def test_nan_values_become_none(self):
        features = extract_hike_features(FAKE_XML)

        self.assertIsNone(features["weather"][0]["apparent_temperature"])

    def test_missing_gpx_features_returns_empty(self):
        self.assertEqual(extract_hike_features("<InputData/>"), {})


class TestServer(unittest.TestCase):
    def setUp(self):
        self.app = create_app(model_fn=_fake_model)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()
        patcher = mock.patch("server.app.build_input_xml", return_value=FAKE_XML)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _post(self, data=None):
        default = {
            "gpx": (io.BytesIO(b"<gpx/>"), "course.gpx"),
            "personal_information": (
                io.BytesIO(b'{"name": "x"}'),
                "personal_information.json",
            ),
            "hike_information": (
                io.BytesIO(b'{"type": "hike"}'),
                "hike_information.json",
            ),
        }
        if data:
            default.update(data)
        return self.client.post(
            "/api/estimate", data=default, content_type="multipart/form-data"
        )

    def test_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.get_json(), {"status": "ok"})

    def test_index_serves_demo_page(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        self.assertIn(b"What To Bring", res.data)

    def test_catalog_lists_products(self):
        res = self.client.get("/api/catalog")
        self.assertEqual(res.status_code, 200)

        items = res.get_json()
        self.assertGreaterEqual(len(items), 30)
        for item in items:
            self.assertIn("name", item)
            self.assertIn("layer", item)
        names = {item["name"] for item in items}
        self.assertIn("Men's Hiking Synthetic SS T-Shirt MH500", names)

    def test_happy_path(self):
        res = self._post()
        self.assertEqual(res.status_code, 200)

        body = res.get_json()
        self.assertEqual(body["overall_strategy"], "strategy")
        self.assertEqual(body["recommendations"]["base"]["items"][0]["name"], "BaseA")
        self.assertEqual(body["hike_features"]["distance_km"], 10.1)
        self.assertNotIn("overall_strategy", body["recommendations"])

    def test_jsons_also_accepted_as_text_fields(self):
        res = self._post(
            {
                "personal_information": '{"name": "x"}',
                "hike_information": '{"type": "hike"}',
            }
        )
        self.assertEqual(res.status_code, 200)

    def test_missing_gpx_returns_400(self):
        res = self._post({"gpx": None})
        self.assertEqual(res.status_code, 400)
        self.assertIn("gpx", res.get_json()["error"])

    def test_invalid_personal_json_returns_400(self):
        res = self._post(
            {
                "personal_information": (
                    io.BytesIO(b"not json"),
                    "personal_information.json",
                )
            }
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("Invalid JSON", res.get_json()["error"])

    def test_model_error_returns_500(self):
        def failing_model(xml_input: str) -> dict:
            return {"error": "boom"}

        app = create_app(model_fn=failing_model)
        app.config["TESTING"] = True
        client = app.test_client()
        with mock.patch("server.app.build_input_xml", return_value=FAKE_XML):
            res = client.post(
                "/api/estimate",
                data={
                    "gpx": (io.BytesIO(b"<gpx/>"), "course.gpx"),
                    "personal_information": (
                        io.BytesIO(b'{"name": "x"}'),
                        "personal_information.json",
                    ),
                    "hike_information": (
                        io.BytesIO(b'{"type": "hike"}'),
                        "hike_information.json",
                    ),
                },
                content_type="multipart/form-data",
            )

        self.assertEqual(res.status_code, 500)
        self.assertIn("boom", res.get_json()["error"])

    def test_build_xml_failure_returns_422(self):
        with mock.patch(
            "server.app.build_input_xml", side_effect=ValueError("bad gpx")
        ):
            res = self._post()
        self.assertEqual(res.status_code, 422)
        self.assertIn("bad gpx", res.get_json()["error"])


if __name__ == "__main__":
    unittest.main()
