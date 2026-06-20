import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Callable, Optional

ALL_CATEGORIES = ["base", "middle", "insulation", "shell", "pants", "shoes", "gear"]
POS_CATEGORIES = {"base", "middle", "insulation", "shell", "pants", "shoes"}

@dataclass
class CategoryMetrics:
    category: str
    validated: bool

    true_positives: list[str] = field(default_factory=list)
    false_positives: list[str] = field(default_factory=list)
    false_negatives: list[str] = field(default_factory=list)

    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    jaccard: float = 0.0

    position_accuracy: Optional[float] = None
    position_mismatches: list[tuple[str, Optional[str], Optional[str]]] = field(default_factory=list)

    predicted_preview: list[str] = field(default_factory=list)

@dataclass
class PerformanceMetrics:
    per_category: dict[str, CategoryMetrics]
    overall: CategoryMetrics

def _normalize(name: str) -> str:
    return name.strip().lower()

def _extract_items(category_block: dict) -> list[dict]:
    if not isinstance(category_block, dict):
        return []
    items = category_block.get("items", [])
    return items if isinstance(items, list) else []

def evaluate_category(
    category: str,
    predicted_items: list[dict],
    expected_items: list[dict],
    has_position: bool,
) -> CategoryMetrics:
    # First checks if the items are correctly predicted, then (for true positives) checks if the position is correct
    pred_by_name = {_normalize(i["name"]): i for i in predicted_items if "name" in i}
    exp_by_name = {_normalize(i["name"]): i for i in expected_items if "name" in i}

    pred_names = set(pred_by_name.keys())
    exp_names = set(exp_by_name.keys())

    tp_names = pred_names & exp_names
    fp_names = pred_names - exp_names
    fn_names = exp_names - pred_names

    tp = [pred_by_name[n]["name"] for n in tp_names]
    fp = [pred_by_name[n]["name"] for n in fp_names]
    fn = [exp_by_name[n]["name"] for n in fn_names]

    precision = len(tp_names) / len(pred_names) if pred_names else 0.0
    recall = len(tp_names) / len(exp_names) if exp_names else 0.0
    f1 = (
        2 * precision * recall / (precision + recall)
        if (precision + recall) > 0
        else 0.0
    )
    union_size = len(pred_names | exp_names)
    jaccard = len(tp_names) / union_size if union_size > 0 else 0.0

    position_accuracy: Optional[float] = None
    position_mismatches: list[tuple[str, Optional[str], Optional[str]]] = []

    if has_position and tp_names:
        correct = 0
        for n in tp_names:
            pred_pos = pred_by_name[n].get("position")
            exp_pos = exp_by_name[n].get("position")
            if pred_pos == exp_pos:
                correct += 1
            else:
                position_mismatches.append((exp_by_name[n]["name"], pred_pos, exp_pos))
        position_accuracy = correct / len(tp_names)

    return CategoryMetrics(
        category=category,
        validated=True,
        true_positives=tp,
        false_positives=fp,
        false_negatives=fn,
        precision=precision,
        recall=recall,
        f1=f1,
        jaccard=jaccard,
        position_accuracy=position_accuracy,
        position_mismatches=position_mismatches,
    )


def evaluate(model_output: dict, ground_truth: dict) -> PerformanceMetrics:
    # Model evaluation by category, then overall (micro-average). Only validated categories are included in the overall metrics.
    validated_categories = set(ground_truth.get("_validated_categories", ALL_CATEGORIES))

    per_category: dict[str, CategoryMetrics] = {}

    for cat in ALL_CATEGORIES:
        predicted_items = _extract_items(model_output.get(cat, {}))

        if cat not in validated_categories:
            per_category[cat] = CategoryMetrics(
                category=cat,
                validated=False,
                predicted_preview=[i.get("name", "?") for i in predicted_items],
            )
            continue

        expected_items = _extract_items(ground_truth.get(cat, {}))
        per_category[cat] = evaluate_category(
            cat,
            predicted_items,
            expected_items,
            has_position=(cat in POS_CATEGORIES
        ),
        )

    validated_metrics = [m for m in per_category.values() if m.validated]

    all_tp = sum(len(m.true_positives) for m in validated_metrics)
    all_fp = sum(len(m.false_positives) for m in validated_metrics)
    all_fn = sum(len(m.false_negatives) for m in validated_metrics)

    overall_precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0.0
    overall_recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0.0
    overall_f1 = (
        2 * overall_precision * overall_recall / (overall_precision + overall_recall)
        if (overall_precision + overall_recall) > 0
        else 0.0
    )
    union = all_tp + all_fp + all_fn
    overall_jaccard = all_tp / union if union > 0 else 0.0

    pos_correct_total = 0.0
    pos_tp_total = 0
    for m in validated_metrics:
        if m.position_accuracy is not None:
            n_tp = len(m.true_positives)
            pos_correct_total += m.position_accuracy * n_tp
            pos_tp_total += n_tp
    overall_position_accuracy = (
        pos_correct_total / pos_tp_total if pos_tp_total > 0 else None
    )

    overall = CategoryMetrics(
        category="overall",
        validated=True,
        precision=overall_precision,
        recall=overall_recall,
        f1=overall_f1,
        jaccard=overall_jaccard,
        position_accuracy=overall_position_accuracy,
    )

    return PerformanceMetrics(per_category=per_category, overall=overall)


def print_report(sample_name: str, model_output: dict, metrics: PerformanceMetrics) -> None:
    sep = "─" * 60
    print(f"\n{sep}")
    print(f"  Sample: {sample_name}")
    print(sep)

    overall_strategy = model_output.get("overall_strategy")
    if overall_strategy:
        print(f"\n  Overall strategy:\n      {overall_strategy}")

    for cat in ALL_CATEGORIES:
        cm = metrics.per_category[cat]
        print(f"\n{'─' * 40}")

        if not cm.validated:
            print(f"  {cat.upper()}  —    ground truth not validated for this category, metrics not computed")
            if cm.predicted_preview:
                print("   Model predictions:")
                for name in cm.predicted_preview:
                    print(f"       {name}")
            continue

        print(f"  {cat.upper()}")
        print(f"  Precision : {cm.precision:.2%}")
        print(f"  Recall    : {cm.recall:.2%}")
        print(f"  F1        : {cm.f1:.2%}")
        print(f"  Jaccard   : {cm.jaccard:.2%}")
        if cm.position_accuracy is not None:
            print(f"  Position  : {cm.position_accuracy:.2%}  (upon {len(cm.true_positives)} true positives)")

        if cm.true_positives:
            print(f"   TP: {', '.join(cm.true_positives)}")
        if cm.false_positives:
            print(f"   FP: {', '.join(cm.false_positives)}")
        if cm.false_negatives:
            print(f"   FN: {', '.join(cm.false_negatives)}")
        if cm.position_mismatches:
            print("   Wrong positions:")
            for name, pred_pos, exp_pos in cm.position_mismatches:
                print(f"      {name}: predicted='{pred_pos}', expected='{exp_pos}'")

    o = metrics.overall
    print(f"\n{'═' * 40}")
    print("  OVERALL")
    print(f"{'═' * 40}")
    print(f"  Precision : {o.precision:.2%}")
    print(f"  Recall    : {o.recall:.2%}")
    print(f"  F1        : {o.f1:.2%}")
    print(f"  Jaccard   : {o.jaccard:.2%}")
    if o.position_accuracy is not None:
        print(f"  Position  : {o.position_accuracy:.2%}")

    print(f"\n{sep}\n")

# Entry point. Takes the XLM and gives back the model output dictionary
ModelFn = Callable[[str], dict]

def presentation(sample: dict[str, str], model_fn: Optional[ModelFn] = None) -> PerformanceMetrics:
    xml_path = Path(sample["xml_output"])
    expected_path = Path(sample["expected_output"])

    if not xml_path.exists():
        raise FileNotFoundError(f"Input XML not found: {xml_path}")
    if not expected_path.exists():
        raise FileNotFoundError(f"Ground truth not found: {expected_path}")

    xml_input = xml_path.read_text(encoding="utf-8")

    with open(expected_path, "r", encoding="utf-8") as f:
        ground_truth = json.load(f)

    if model_fn is None:
        from model.pipeline import execute_analysis
        model_fn = execute_analysis

    model_output = model_fn(xml_input)

    if "error" in model_output:
        raise RuntimeError(f"Model execution failed: {model_output['error']}")

    metrics = evaluate(model_output, ground_truth)

    print_report(
        sample_name=sample["folder"],
        model_output=model_output,
        metrics=metrics,
    )

    return metrics