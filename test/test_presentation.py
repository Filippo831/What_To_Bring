import json
import unittest
from pathlib import Path

from presentation.presentation import (
    evaluate,
    evaluate_category,
    ALL_CATEGORIES,
    POS_CATEGORIES,
    PerformanceMetrics,
    presentation,
)
from model.model import run_model

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_SAMPLE_00_DIR = _PROJECT_ROOT / "samples" / "00"


# 1. Unit test: evaluate category

class TestEvaluateCategory(unittest.TestCase):

    def test_perfect_match_with_correct_position(self):
        predicted = [{"name": "ItemA", "position": "worn"}]
        expected  = [{"name": "ItemA", "position": "worn"}]

        m = evaluate_category("base", predicted, expected, has_position=True)

        self.assertEqual(m.precision, 1.0)
        self.assertEqual(m.recall, 1.0)
        self.assertEqual(m.f1, 1.0)
        self.assertEqual(m.jaccard, 1.0)
        self.assertEqual(m.position_accuracy, 1.0)
        self.assertEqual(m.position_mismatches, [])

    def test_item_correct_but_position_wrong(self):
        # item correctly selected, but position not corresponding
        predicted = [{"name": "ItemA", "position": "worn"}]
        expected  = [{"name": "ItemA", "position": "backpack"}]

        m = evaluate_category("shell", predicted, expected, has_position=True)

        self.assertEqual(m.precision, 1.0)
        self.assertEqual(m.recall, 1.0)
        self.assertEqual(m.f1, 1.0)
        self.assertEqual(m.position_accuracy, 0.0)
        self.assertEqual(len(m.position_mismatches), 1)
        self.assertEqual(m.position_mismatches[0], ("ItemA", "worn", "backpack"))

    def test_category_without_position_concept(self):
        predicted = [{"name": "Trekking poles"}]
        expected  = [{"name": "Trekking poles"}]

        m = evaluate_category("gear", predicted, expected, has_position=False)

        self.assertEqual(m.f1, 1.0)
        self.assertIsNone(m.position_accuracy)
        self.assertEqual(m.position_mismatches, [])

    def test_partial_overlap(self):
        predicted = [{"name": "ItemA", "position": "worn"}, {"name": "ItemC", "position": "worn"}]
        expected  = [{"name": "ItemA", "position": "worn"}, {"name": "ItemD", "position": "worn"}]

        m = evaluate_category("base", predicted, expected, has_position=True)

        self.assertAlmostEqual(m.precision, 0.5)
        self.assertAlmostEqual(m.recall, 0.5)
        self.assertIn("ItemC", m.false_positives)
        self.assertIn("ItemD", m.false_negatives)
        self.assertEqual(m.position_accuracy, 1.0)

    def test_case_insensitive_name_matching(self):
        predicted = [{"name": "  item a  ", "position": "worn"}]
        expected  = [{"name": "Item A", "position": "worn"}]

        m = evaluate_category("base", predicted, expected, has_position=True)

        self.assertEqual(m.precision, 1.0)
        self.assertEqual(m.recall, 1.0)

    def test_empty_predicted(self):
        m = evaluate_category("base", [], [{"name": "ItemA", "position": "worn"}], has_position=True)

        self.assertEqual(m.precision, 0.0)
        self.assertEqual(m.recall, 0.0)
        self.assertIsNone(m.position_accuracy)

    def test_empty_expected(self):
        m = evaluate_category("base", [{"name": "ItemA", "position": "worn"}], [], has_position=True)

        self.assertEqual(m.precision, 0.0)
        self.assertEqual(m.recall, 0.0)

    def test_both_empty(self):
        # if nothing is predicted, no error
        m = evaluate_category("insulation", [], [], has_position=True)

        self.assertEqual(m.precision, 0.0)
        self.assertEqual(m.recall, 0.0)
        self.assertEqual(m.true_positives, [])
        self.assertEqual(m.false_positives, [])
        self.assertEqual(m.false_negatives, [])


# 2. Unit test: overall aggregation of multiple categories
class TestEvaluateAggregate(unittest.TestCase):

    def setUp(self):
        self.model_output = {
            "base":       {"items": [{"name": "BaseA", "position": "worn"}]},
            "middle":     {"items": [{"name": "MidA", "position": "worn"}]},
            "insulation": {"items": [{"name": "InsA", "position": "backpack"}]},
            "shell":      {"items": [{"name": "ShellA", "position": "backpack"}]},
            "pants":      {"items": [{"name": "long pants", "position": "worn"}]},
            "shoes":      {"items": [{"name": "high shoes", "position": "worn"}]},
            "gear":       {"items": [{"name": "GearA"}]},
            "overall_strategy": "test",
        }

    def test_only_validated_categories_are_scored(self):
        ground_truth = {
            "_validated_categories": ["base", "middle"],
            "base":   {"items": [{"name": "BaseA", "position": "worn"}]},
            "middle": {"items": [{"name": "MidA", "position": "worn"}]},
        }

        metrics: PerformanceMetrics = evaluate(self.model_output, ground_truth)

        self.assertTrue(metrics.per_category["base"].validated)
        self.assertTrue(metrics.per_category["middle"].validated)
        self.assertFalse(metrics.per_category["insulation"].validated)
        self.assertFalse(metrics.per_category["shell"].validated)

    def test_unvalidated_category_shows_preview_not_scored(self):
        ground_truth = {
            "_validated_categories": ["base"],
            "base": {"items": [{"name": "BaseA", "position": "worn"}]},
        }

        metrics = evaluate(self.model_output, ground_truth)
        shell_metrics = metrics.per_category["shell"]

        self.assertFalse(shell_metrics.validated)
        self.assertEqual(shell_metrics.predicted_preview, ["ShellA"])
        self.assertEqual(shell_metrics.precision, 0.0)
        self.assertEqual(shell_metrics.false_positives, [])

    def test_overall_aggregates_only_validated_categories(self):
        ground_truth = {
            "_validated_categories": ["base", "middle"],
            "base":   {"items": [{"name": "BaseA", "position": "worn"}]},
            "middle": {"items": [{"name": "MidA", "position": "worn"}]},
        }

        metrics = evaluate(self.model_output, ground_truth)

        self.assertEqual(metrics.overall.precision, 1.0)
        self.assertEqual(metrics.overall.recall, 1.0)
        self.assertEqual(metrics.overall.f1, 1.0)
        self.assertEqual(metrics.overall.position_accuracy, 1.0)

    def test_overall_with_mixed_position_correctness(self):
        ground_truth = {
            "_validated_categories": ["base", "middle"],
            "base":   {"items": [{"name": "BaseA", "position": "backpack"}]},
            "middle": {"items": [{"name": "MidA", "position": "worn"}]},
        }

        metrics = evaluate(self.model_output, ground_truth)

        self.assertEqual(metrics.overall.precision, 1.0)
        self.assertEqual(metrics.overall.position_accuracy, 0.5)

    def test_default_validated_categories_is_all(self):
        ground_truth = {
            "base":       {"items": [{"name": "BaseA", "position": "worn"}]},
            "middle":     {"items": [{"name": "MidA", "position": "worn"}]},
            "insulation": {"items": [{"name": "InsA", "position": "backpack"}]},
            "shell":      {"items": [{"name": "ShellA", "position": "backpack"}]},
            "pants":      {"items": [{"name": "long pants", "position": "worn"}]},
            "shoes":      {"items": [{"name": "high shoes", "position": "worn"}]},
            "gear":       {"items": [{"name": "GearA"}]},
        }

        metrics = evaluate(self.model_output, ground_truth)

        for cat in ALL_CATEGORIES:
            self.assertTrue(metrics.per_category[cat].validated)
        self.assertEqual(metrics.overall.f1, 1.0)


# 3. Unit test: mock respecting the expected output schema of the model
class TestRunModelMock(unittest.TestCase):

    def setUp(self):
        self.output = run_model("<input_data/>")

    def test_has_all_expected_categories(self):
        for cat in ALL_CATEGORIES:
            self.assertIn(cat, self.output)
            self.assertIn("items", self.output[cat])
            self.assertIsInstance(self.output[cat]["items"], list)

    def test_has_overall_strategy(self):
        self.assertIn("overall_strategy", self.output)
        self.assertIsInstance(self.output["overall_strategy"], str)

    def test_items_with_position_have_position_field(self):
        for cat in POS_CATEGORIES:
            for item in self.output[cat]["items"]:
                self.assertIn("position", item)
                self.assertIn(item["position"], ("worn", "backpack"))

    def test_gear_items_have_no_position_field_required(self):
        for item in self.output["gear"]["items"]:
            self.assertIn("name", item)


# 4. E2E test: presentation with mock model
def _fake_gemini_response(xml_input: str) -> dict:
    # just to keep tests free and fast
    _ = xml_input
    return {
        "base": {
            "motivation": "fixture",
            "items": [
                {"position": "worn", "name": "Men's Hiking Synthetic SS T-Shirt MH500"},
                {"position": "backpack", "name": "Men's Long-Sleeved Hiking T-Shirt MH500"},
            ],
        },
        "middle": {
            "motivation": "fixture",
            "items": [
                {"position": "worn", "name": "Men's MH120 Hiking Fleece Zip"},
                {"position": "backpack", "name": "Men's Hiking Fleece MH500"},
            ],
        },
        "insulation": {
            "motivation": "fixture",
            "items": [{"position": "backpack", "name": "Men's MT500 Down Puffer Jacket"}],
        },
        "shell": {
            "motivation": "fixture",
            "items": [{"position": "backpack", "name": "Men's Waterproof Hiking Jacket MH500"}],
        },
        "pants": {
            "motivation": "fixture",
            "items": [{"name": "long pants", "position": "worn"}],
        },
        "shoes": {
            "motivation": "fixture",
            "items": [{"name": "high shoes", "position": "worn"}],
        },
        "gear": {
            "motivation": "fixture",
            "items": [{"name": "trekking poles"}],
        },
        "overall_strategy": "fixture overall strategy",
    }


def _fake_failed_response(xml_input: str) -> dict:
    _ = xml_input
    return {"error": "simulated failure"}


class TestPresentationE2E(unittest.TestCase):

    def setUp(self):
        self.sample = {
            "folder": "00",
            "xml_output": str(_SAMPLE_00_DIR / "output.xml"),
            "expected_output": str(_SAMPLE_00_DIR / "expected_output.json"),
        }

    def test_sample_files_exist(self):
        self.assertTrue(Path(self.sample["xml_output"]).exists())
        self.assertTrue(Path(self.sample["expected_output"]).exists())

    def test_expected_output_schema(self):
        with open(self.sample["expected_output"], encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("_validated_categories", data)
        for cat in ALL_CATEGORIES:
            self.assertIn(cat, data)
            self.assertIn("items", data[cat])

    def test_e2e_with_mock_achieves_perfect_score_on_validated_categories(self):
        metrics = presentation(self.sample, model_fn=run_model)

        self.assertAlmostEqual(metrics.overall.f1, 1.0)
        self.assertAlmostEqual(metrics.overall.jaccard, 1.0)
        self.assertEqual(metrics.overall.position_accuracy, 1.0)

    def test_e2e_with_realistic_fixture_metrics_in_range(self):
        metrics = presentation(self.sample, model_fn=_fake_gemini_response)

        for cm in list(metrics.per_category.values()) + [metrics.overall]:
            for value in (cm.precision, cm.recall, cm.f1, cm.jaccard):
                self.assertGreaterEqual(value, 0.0)
                self.assertLessEqual(value, 1.0)
            if cm.position_accuracy is not None:
                self.assertGreaterEqual(cm.position_accuracy, 0.0)
                self.assertLessEqual(cm.position_accuracy, 1.0)

    def test_e2e_unvalidated_categories_do_not_crash_or_count_as_errors(self):
        metrics = presentation(self.sample, model_fn=_fake_gemini_response)

        self.assertFalse(metrics.per_category["pants"].validated)
        self.assertEqual(metrics.per_category["pants"].false_positives, [])
        self.assertIn("long pants", metrics.per_category["pants"].predicted_preview)

    def test_model_error_raises_runtime_error(self):
        with self.assertRaises(RuntimeError):
            presentation(self.sample, model_fn=_fake_failed_response)

    def test_missing_xml_raises_file_not_found(self):
        bad_sample = dict(self.sample)
        bad_sample["xml_output"] = str(_SAMPLE_00_DIR / "does_not_exist.xml")

        with self.assertRaises(FileNotFoundError):
            presentation(bad_sample, model_fn=run_model)


if __name__ == "__main__":
    unittest.main()