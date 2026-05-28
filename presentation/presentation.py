import json
from pathlib import Path
from dataclasses import dataclass

from model.model import run_model, ModelOutput

@dataclass
class PerformanceMetrics:
    true_positives: list[str]
    false_positives: list[str]
    false_negatives: list[str]
    precision: float
    recall: float
    f1: float
    jaccard: float


def evaluate(predicted: list[str], expected: list[str]) -> PerformanceMetrics:

    #Evaluate the model's performance by comparing the predicted items with the expected items.

    pred_set = {item.strip().lower() for item in predicted}
    exp_set = {item.strip().lower() for item in expected}

    tp = [item for item in predicted if item.strip().lower() in exp_set]
    fp = [item for item in predicted if item.strip().lower() not in exp_set]
    fn = [item for item in expected if item.strip().lower() not in pred_set]

    precision = len(tp) / len(predicted) if predicted else 0.0
    recall = len(tp) / len(expected) if expected else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    union_size = len(pred_set | exp_set)
    jaccard = len(pred_set & exp_set) / union_size if union_size > 0 else 0.0

    return PerformanceMetrics(
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        jaccard=jaccard
    )


def print_report(sample_name: str, model_output: ModelOutput, metrics: PerformanceMetrics) -> None:

    # Print a detailed report of the model's performance on the sample

    sep = "--" * 60
    print(f"\n{sep}")
    print(f"Sample: {sample_name}")
    print(sep)

    print("\nSuggested items:")
    for item in model_output["suggested_items"]:
        print(f"  - {item}")

    print(f"\n{'--' * 40}")
    print("Performance Metrics:")
    print(f"{'--' * 40}")
    print(f"Precision: {metrics.precision:.2%} ({len(metrics.true_positives)}/{len(metrics.true_positives) + len(metrics.false_positives)} suggested items correct)")
    print(f"Recall: {metrics.recall:.2%} ({len(metrics.true_positives)}/{len(metrics.true_positives) + len(metrics.false_negatives)} expected items identified)")
    print(f"F1 Score: {metrics.f1:.2%}")
    print(f"Jaccard Index: {metrics.jaccard:.2%}")
    if metrics.true_positives:
        print(f"\nTrue Positives ({len(metrics.true_positives)}):")
        for item in metrics.true_positives:
            print(f"  + {item}")

    if metrics.false_positives:
        print(f"\nFalse Positives ({len(metrics.false_positives)}):")
        for item in metrics.false_positives:
            print(f"  - {item}")

    if metrics.false_negatives:
        print(f"\nFalse Negatives ({len(metrics.false_negatives)}):")
        for item in metrics.false_negatives:
            print(f"  ? {item}")

    print(f"\n{sep}\n")


def presentation(sample: dict[str, str]) -> PerformanceMetrics:

    """
    Evaluate a single sample.
 
    Parameters
    ----------
    sample : dict with keys
        - "folder"               : folder name (used as label)
        - "xml_output"           : path to the XML produced by input_handler
        - "expected_output"      : path to the expected_output.json file
    """

    xml_path = Path(sample["xml_output"])
    expected_path = Path(sample["expected_output"])
 
    if not xml_path.exists():
        raise FileNotFoundError(f"XML di input non trovato: {xml_path}")
    if not expected_path.exists():
        raise FileNotFoundError(f"Ground truth non trovata: {expected_path}")
 
    xml_input = xml_path.read_text(encoding="utf-8")
 
    with open(expected_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)
 
    expected_items: list[str] = ground_truth["suggested_items"]
 
    model_output: ModelOutput = run_model(xml_input)
 
    metrics = evaluate(
        predicted=model_output["suggested_items"],
        expected=expected_items,
    )
 
    print_report(
        sample_name=sample["folder"],
        model_output=model_output,
        metrics=metrics,
    )
 
    return metrics