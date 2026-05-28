import json
import unittest
from pathlib import Path

from presentation.presentation import evaluate, PerformanceMetrics
from model.model import run_model, ModelOutput

_PROJECT_ROOT  = Path(__file__).resolve().parent.parent
_SAMPLE_00_DIR = _PROJECT_ROOT / "samples" / "00"


# 1. Unit test: logic test for evaluate() with no input/output

class TestEvaluate(unittest.TestCase):

    def test_perfect_match(self):
        # Expecting precision=1, recall=1, F1=1 when predicted and expected are identical
        items = ["ItemA", "ItemB", "ItemC"]
        m = evaluate(predicted=items, expected=items)

        self.assertEqual(m.precision, 1.0)
        self.assertEqual(m.recall, 1.0)
        self.assertEqual(m.f1, 1.0)
        self.assertEqual(m.jaccard, 1.0)
        self.assertEqual(m.false_positives, [])
        self.assertEqual(m.false_negatives, [])

    def test_no_overlap(self):
        # Expecting precision=0, recall=0, F1=0 when predicted and expected have no items in common
        m = evaluate(predicted=["ItemA"], expected=["ItemB"])

        self.assertEqual(m.precision, 0.0)
        self.assertEqual(m.recall, 0.0)
        self.assertEqual(m.f1, 0.0)
        self.assertEqual(m.jaccard, 0.0)
        self.assertEqual(len(m.true_positives), 0)

    def test_partial_overlap(self):
        # Expecting precision=2/3, recall=2/3, F1=2/3 when 2 out of 3 predicted items are correct and 1 expected item is missed
        m = evaluate(
            predicted=["ItemA", "ItemB", "ItemC"],
            expected= ["ItemA", "ItemB", "ItemD"],
        )

        self.assertAlmostEqual(m.precision, 2/3)
        self.assertAlmostEqual(m.recall, 2/3)
        self.assertIn("ItemC", m.false_positives)
        self.assertIn("ItemD", m.false_negatives)

    def test_jaccard_asimmetry(self):
        # Expecting Jaccard Index to reflect the ratio of intersection over union, which is asymmetric when predicted and expected have different sizes
        m = evaluate(
            predicted=["ItemA", "ItemB"],
            expected= ["ItemA"],
        )

        self.assertEqual(m.f1, 2/3)
        self.assertEqual(m.jaccard, 0.5)

    def test_case_insensitive(self):
        # Expecting precision=1, recall=1, F1=1 when predicted and expected match case-insensitively
        m = evaluate(
            predicted=["  item a  ", "ITEM B"],
            expected= ["Item A", "item b"],
        )

        self.assertEqual(m.precision, 1.0)
        self.assertEqual(m.recall, 1.0)
        self.assertEqual(m.jaccard, 1.0)

    def test_empty_predicted(self):
        # Expecting precision=0, recall=0, F1=0 when no items are predicted (no true positives possible)
        m = evaluate(predicted=[], expected=["ItemA"])

        self.assertEqual(m.precision, 0.0)
        self.assertEqual(m.recall, 0.0)
        self.assertEqual(m.f1, 0.0)
        self.assertEqual(m.jaccard, 0.0)

    def test_empty_expected(self):
        # Expecting precision=0, recall=0, F1=0 when no items are expected (any predicted item is a false positive)
        m = evaluate(predicted=["ItemA"], expected=[])

        self.assertEqual(m.precision, 0.0)
        self.assertEqual(m.recall, 0.0)
        self.assertEqual(m.jaccard, 0.0)

    def test_f1_formula(self):
        # Test a specific case to verify the F1 formula is applied correctly
        # Precision = 1/2, recall = 1/1 → F1 = 2*(0.5*1)/(0.5+1) = 2/3
        m = evaluate(predicted=["ItemA", "ItemB"], expected=["ItemA"])

        self.assertAlmostEqual(m.precision, 0.5)
        self.assertAlmostEqual(m.recall, 1.0)
        self.assertAlmostEqual(m.f1, 2/3)


# 2. Unit test: verify that the mock implementation of run_model() respects the interface contract

class TestRunModelMock(unittest.TestCase):

    def setUp(self):
        self.output: ModelOutput = run_model("<input_data/>")

    def test_returns_typed_dict(self):
        # The output must be a ModelOutput (TypedDict) with the expected keys.
        self.assertIn("suggested_items", self.output)

    def test_suggested_items_is_list_of_strings(self):
        items = self.output["suggested_items"]
        self.assertIsInstance(items, list)
        for item in items:
            self.assertIsInstance(item, str,
                msg=f"Every item should be a string, found: {type(item)}")

    def test_suggested_items_not_empty(self):
        # The mock is calibrated to return a non-empty list of suggested items.
        self.assertGreater(len(self.output["suggested_items"]), 0)


# 3. End-to-end: test the entire presentation pipeline using the real sample file 00

class TestPresentationE2E(unittest.TestCase):

    def setUp(self):
        self.xml_path = _SAMPLE_00_DIR / "output.xml"
        self.expected_path = _SAMPLE_00_DIR / "expected_output.json"

    def test_sample_files_exist(self):
        # Verify that the sample files exist before running the end-to-end test.
        self.assertTrue(self.xml_path.exists(),
            msg=f"output.xml not found: {self.xml_path}")
        self.assertTrue(self.expected_path.exists(),
            msg=f"expected_output.json not found: {self.expected_path}")

    def test_expected_output_schema(self):
        # Verify that the expected_output.json has the correct schema (contains "suggested_items" as a non-empty list).
        with open(self.expected_path, encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("suggested_items", data)
        self.assertIsInstance(data["suggested_items"], list)
        self.assertGreater(len(data["suggested_items"]), 0)

    def test_e2e_metrics_in_range(self):
        # Run the end-to-end pipeline and verify that the computed metrics are within the valid range [0, 1].
        xml_input = self.xml_path.read_text(encoding="utf-8")

        with open(self.expected_path, encoding="utf-8") as f:
            ground_truth = json.load(f)

        model_output = run_model(xml_input)
        metrics = evaluate(
            predicted=model_output["suggested_items"],
            expected=ground_truth["suggested_items"],
        )

        for metric_name, value in [
            ("precision", metrics.precision),
            ("recall", metrics.recall),
            ("f1", metrics.f1),
            ("jaccard", metrics.jaccard),
        ]:
            self.assertGreaterEqual(value, 0.0, msg=f"{metric_name} < 0")
            self.assertLessEqual(   value, 1.0, msg=f"{metric_name} > 1")

    def test_mock_achieves_perfect_score_on_sample_00(self):
        # The mock is calibrated to achieve perfect precision, recall, and F1 on sample 00.
        xml_input = self.xml_path.read_text(encoding="utf-8")

        with open(self.expected_path, encoding="utf-8") as f:
            ground_truth = json.load(f)

        model_output = run_model(xml_input)
        metrics = evaluate(
            predicted=model_output["suggested_items"],
            expected=ground_truth["suggested_items"],
        )

        self.assertAlmostEqual(metrics.f1, 1.0,
            msg="The mock must achieve F1=1.0 on sample 00 (it is calibrated on it)")
        self.assertAlmostEqual(metrics.jaccard, 1.0,
            msg="The mock must achieve Jaccard Index=1.0 on sample 00 (it is calibrated on it)")


if __name__ == "__main__":
    unittest.main()