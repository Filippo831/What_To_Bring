import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from evaluation.run_evaluation import (
    SampleEvaluation,
    aggregate,
    discover_samples,
    evaluate_sample,
    main,
)
from presentation.presentation import evaluate

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SAMPLE_00_DIR = _PROJECT_ROOT / "samples" / "00"


def _perfect_output() -> dict:
    return {
        "base": {
            "motivation": "m",
            "items": [{"position": "worn", "name": "BaseA"}],
        },
        "middle": {
            "motivation": "m",
            "items": [{"position": "worn", "name": "MidA"}],
        },
        "insulation": {"motivation": "m", "items": []},
        "shell": {
            "motivation": "m",
            "items": [{"position": "backpack", "name": "ShellA"}],
        },
        "pants": {"motivation": "m", "items": []},
        "shoes": {"motivation": "m", "items": []},
        "gear": {"motivation": "m", "items": []},
        "overall_strategy": "s",
    }


def _perfect_ground_truth() -> dict:
    return {
        "_validated_categories": ["base", "middle", "shell"],
        "base": {"items": [{"name": "BaseA", "position": "worn"}]},
        "middle": {"items": [{"name": "MidA", "position": "worn"}]},
        "insulation": {"items": []},
        "shell": {"items": [{"name": "ShellA", "position": "backpack"}]},
        "pants": {"items": []},
        "shoes": {"items": []},
        "gear": {"items": []},
    }


def _imperfect_output() -> dict:
    output = _perfect_output()
    output["middle"]["items"] = [{"position": "backpack", "name": "MidA"}]
    output["shell"]["items"] = []
    return output


def _result(name: str, model_output: dict, ground_truth: dict) -> SampleEvaluation:
    return SampleEvaluation(name, True, metrics=evaluate(model_output, ground_truth))


class TestDiscoverSamples(unittest.TestCase):
    def test_discovers_folders_with_sample_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "00").mkdir()
            for f in (
                "personal_information.json",
                "hike_information.json",
                "course.gpx",
                "expected_output.json",
            ):
                (root / "00" / f).touch()
            (root / "01").mkdir()
            (root / "01" / "personal_information.json").touch()
            (root / "notes.txt").touch()

            samples = discover_samples(root)

            self.assertEqual([s["folder"] for s in samples], ["00", "01"])
            self.assertEqual(samples[0]["course"], str(root / "00" / "course.gpx"))
            self.assertEqual(
                samples[0]["expected_output"], str(root / "00" / "expected_output.json")
            )

    def test_no_samples_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(discover_samples(Path(tmp)), [])


class TestAggregate(unittest.TestCase):
    def test_per_sample_average_of_overall_metrics(self):
        a = _result("A", _perfect_output(), _perfect_ground_truth())
        b = _result("B", _imperfect_output(), _perfect_ground_truth())

        agg = aggregate([a, b])

        self.assertEqual(agg.n_ok, 2)
        self.assertEqual(agg.n_failed, 0)
        self.assertAlmostEqual(agg.per_sample_average["f1"], 0.9)
        self.assertAlmostEqual(agg.per_sample_average["precision"], 1.0)
        self.assertAlmostEqual(agg.per_sample_average["recall"], (1.0 + 2 / 3) / 2)
        self.assertAlmostEqual(agg.per_sample_average["jaccard"], (1.0 + 2 / 3) / 2)
        self.assertAlmostEqual(agg.per_sample_average["position_accuracy"], 0.75)

    def test_pooled_micro_average(self):
        a = _result("A", _perfect_output(), _perfect_ground_truth())
        b = _result("B", _imperfect_output(), _perfect_ground_truth())

        agg = aggregate([a, b])

        self.assertAlmostEqual(agg.pooled["precision"], 1.0)
        self.assertAlmostEqual(agg.pooled["recall"], 5 / 6)
        self.assertAlmostEqual(agg.pooled["f1"], 10 / 11)
        self.assertAlmostEqual(agg.pooled["jaccard"], 5 / 6)
        self.assertAlmostEqual(agg.pooled["position_accuracy"], 0.8)

    def test_position_average_skips_samples_without_position(self):
        a = _result("A", _perfect_output(), _perfect_ground_truth())
        gear_output = {
            "base": {"motivation": "m", "items": []},
            "middle": {"motivation": "m", "items": []},
            "insulation": {"motivation": "m", "items": []},
            "shell": {"motivation": "m", "items": []},
            "pants": {"motivation": "m", "items": []},
            "shoes": {"motivation": "m", "items": []},
            "gear": {"motivation": "m", "items": [{"name": "trekking poles"}]},
            "overall_strategy": "s",
        }
        gear_truth = {
            "_validated_categories": ["gear"],
            "base": {"items": []},
            "middle": {"items": []},
            "insulation": {"items": []},
            "shell": {"items": []},
            "pants": {"items": []},
            "shoes": {"items": []},
            "gear": {"items": [{"name": "trekking poles"}]},
        }
        c = _result("C", gear_output, gear_truth)

        agg = aggregate([a, c])

        self.assertIsNone(c.metrics.overall.position_accuracy)
        self.assertAlmostEqual(agg.per_sample_average["position_accuracy"], 1.0)

    def test_failed_samples_excluded(self):
        a = _result("A", _perfect_output(), _perfect_ground_truth())
        failed = SampleEvaluation("B", False, error="boom")

        agg = aggregate([a, failed])

        self.assertEqual(agg.n_ok, 1)
        self.assertEqual(agg.n_failed, 1)
        self.assertAlmostEqual(agg.pooled["f1"], 1.0)
        self.assertAlmostEqual(agg.per_sample_average["f1"], 1.0)


class TestEvaluateSample(unittest.TestCase):
    def _sample_dict(self) -> dict[str, str]:
        d = {"folder": "00"}
        for key, filename in (
            ("personal_information", "personal_information.json"),
            ("hike_information", "hike_information.json"),
            ("course", "course.gpx"),
            ("expected_output", "expected_output.json"),
        ):
            d[key] = str(_SAMPLE_00_DIR / filename)
        return d

    def test_ok_with_fake_model(self):
        def fake_model(xml_input: str) -> dict:
            self.assertIn("<InputData", xml_input)
            return {
                "base": {
                    "motivation": "m",
                    "items": [
                        {
                            "position": "worn",
                            "name": "Men's Hiking Synthetic SS T-Shirt MH500",
                        }
                    ],
                },
                "middle": {
                    "motivation": "m",
                    "items": [{"position": "worn", "name": "Men's MH120 Hiking Fleece Zip"}],
                },
                "insulation": {"motivation": "m", "items": []},
                "shell": {
                    "motivation": "m",
                    "items": [
                        {
                            "position": "backpack",
                            "name": "Men's Ultra-Light Rain Jacket FH500",
                        }
                    ],
                },
                "pants": {"motivation": "m", "items": []},
                "shoes": {"motivation": "m", "items": []},
                "gear": {"motivation": "m", "items": []},
                "overall_strategy": "s",
            }

        with mock.patch(
            "evaluation.run_evaluation.build_input_xml", return_value="<InputData/>"
        ):
            result = evaluate_sample(self._sample_dict(), fake_model)

        self.assertTrue(result.ok)
        self.assertIsNone(result.error)
        self.assertAlmostEqual(result.metrics.overall.f1, 1.0)
        self.assertAlmostEqual(result.metrics.overall.position_accuracy, 1.0)

    def test_model_error_marks_sample_failed(self):
        def fake_model(xml_input: str) -> dict:
            return {"error": "simulated failure"}

        with mock.patch(
            "evaluation.run_evaluation.build_input_xml", return_value="<InputData/>"
        ):
            result = evaluate_sample(self._sample_dict(), fake_model)

        self.assertFalse(result.ok)
        self.assertIn("simulated failure", result.error)

    def test_missing_files_marks_sample_failed(self):
        bad = {
            "folder": "x",
            "personal_information": "/nonexistent/personal_information.json",
            "hike_information": "/nonexistent/hike_information.json",
            "course": "/nonexistent/course.gpx",
            "expected_output": "/nonexistent/expected_output.json",
        }

        result = evaluate_sample(bad, lambda xml_input: _perfect_output())

        self.assertFalse(result.ok)
        self.assertIn("FileNotFoundError", result.error)


class TestMain(unittest.TestCase):
    def test_main_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            samples_dir = root / "samples"
            sample_dir = samples_dir / "00"
            sample_dir.mkdir(parents=True)
            (sample_dir / "personal_information.json").write_text('{"name": "x"}')
            (sample_dir / "hike_information.json").write_text("{}")
            (sample_dir / "course.gpx").write_text("<gpx/>")
            with open(_SAMPLE_00_DIR / "expected_output.json", encoding="utf-8") as f:
                expected = json.load(f)
            (sample_dir / "expected_output.json").write_text(json.dumps(expected))

            out = root / "report.json"
            with mock.patch(
                "evaluation.run_evaluation.build_input_xml",
                return_value="<InputData/>",
            ):
                code = main(
                    [
                        "--model",
                        "mock",
                        "--samples-dir",
                        str(samples_dir),
                        "--no-weather",
                        "--output",
                        str(out),
                    ]
                )

            self.assertEqual(code, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data["meta"]["model"], "mock")
            self.assertEqual(data["n_ok"], 1)
            self.assertEqual(data["n_failed"], 0)
            self.assertAlmostEqual(data["pooled"]["f1"], 1.0)
            self.assertAlmostEqual(data["per_sample"][0]["metrics"]["overall"]["f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
