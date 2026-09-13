import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from input_handler.input_handler import build_input_xml
from presentation.presentation import (
    ModelFn,
    PerformanceMetrics,
    evaluate,
    print_report,
)

_SAMPLE_FILES = {
    "personal_information": "personal_information.json",
    "hike_information": "hike_information.json",
    "course": "course.gpx",
    "expected_output": "expected_output.json",
}

METRIC_KEYS = ("precision", "recall", "f1", "jaccard")


@dataclass
class SampleEvaluation:
    sample_name: str
    ok: bool
    error: Optional[str] = None
    metrics: Optional[PerformanceMetrics] = None
    model_output: Optional[dict] = None
    skipped: bool = False
    
@dataclass
class Aggregates:
    per_sample_average: dict[str, Optional[float]]
    pooled: dict[str, Optional[float]]
    n_ok: int
    n_failed: int
    n_skipped: int


def discover_samples(samples_dir: Path) -> list[dict[str, str]]:
    samples: list[dict[str, str]] = []
    for folder in sorted(samples_dir.iterdir()):
        if not folder.is_dir():
            continue
        sample = {"folder": folder.name}
        for key, filename in _SAMPLE_FILES.items():
            sample[key] = str(folder / filename)
        samples.append(sample)
    return samples


def evaluate_sample(
    sample: dict[str, str],
    model_fn: ModelFn,
    use_weather: bool = True,
) -> SampleEvaluation:
    name = sample["folder"]
    try:
        with open(sample["personal_information"], encoding="utf-8") as f:
            personal_info = json.load(f)
        with open(sample["hike_information"], encoding="utf-8") as f:
            hike_info = json.load(f)
        course_gpx = Path(sample["course"]).read_text(encoding="utf-8")

        xml_input = build_input_xml(
            course_gpx, personal_info, hike_info, use_weather=use_weather
        )

        model_output = model_fn(xml_input)
        if not isinstance(model_output, dict):
            raise RuntimeError(
                f"Model returned {type(model_output).__name__}, expected dict"
            )
        if "error" in model_output:
            return SampleEvaluation(
                name,
                False,
                error=str(model_output["error"]),
                model_output=model_output,
            )

        expected_raw = Path(sample["expected_output"]).read_text(encoding="utf-8")
        if not expected_raw.strip():
            return SampleEvaluation(
                name, False, model_output=model_output, skipped=True
            )

        ground_truth = json.loads(expected_raw)
        if "_validated_categories" in ground_truth and not ground_truth["_validated_categories"]:
            return SampleEvaluation(
                name, False, model_output=model_output, skipped=True
            )

        metrics = evaluate(model_output, ground_truth)
        return SampleEvaluation(name, True, metrics=metrics, model_output=model_output)
    except Exception as e:
        return SampleEvaluation(name, False, error=f"{type(e).__name__}: {e}")

def _metrics_of(r: "SampleEvaluation") -> PerformanceMetrics:
    assert r.metrics is not None, f"{r.sample_name}: expected metrics on an ok sample"
    return r.metrics


def _model_output_of(r: "SampleEvaluation") -> dict:
    assert (
        r.model_output is not None
    ), f"{r.sample_name}: expected model_output on an ok sample"
    return r.model_output

def aggregate(results: list[SampleEvaluation]) -> Aggregates:
    ok = [r for r in results if r.ok]

    per_sample_average: dict[str, Optional[float]] = {}
    if ok:
        for key in METRIC_KEYS:
            per_sample_average[key] = (
                sum(getattr(_metrics_of(r).overall, key) for r in ok) / len(ok)
            )
        pos_values: list[float] = []
        for r in ok:
            pa = _metrics_of(r).overall.position_accuracy
            if pa is not None:
                pos_values.append(pa)
        per_sample_average["position_accuracy"] = (
            sum(pos_values) / len(pos_values) if pos_values else None
        )

    all_tp = all_fp = all_fn = 0
    pos_correct = 0.0
    pos_tp = 0
    for r in ok:
        for cm in _metrics_of(r).per_category.values():
            if not cm.validated:
                continue
            all_tp += len(cm.true_positives)
            all_fp += len(cm.false_positives)
            all_fn += len(cm.false_negatives)
            if cm.position_accuracy is not None:
                pos_correct += cm.position_accuracy * len(cm.true_positives)
                pos_tp += len(cm.true_positives)

    precision = all_tp / (all_tp + all_fp) if (all_tp + all_fp) > 0 else 0.0
    recall = all_tp / (all_tp + all_fn) if (all_tp + all_fn) > 0 else 0.0
    pooled: dict[str, Optional[float]] = {
        "precision": precision,
        "recall": recall,
        "f1": (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        ),
        "jaccard": (
            all_tp / (all_tp + all_fp + all_fn)
            if (all_tp + all_fp + all_fn) > 0
            else 0.0
        ),
        "position_accuracy": pos_correct / pos_tp if pos_tp > 0 else None,
    }

    n_skipped = sum(1 for r in results if r.skipped)
    return Aggregates(
        per_sample_average=per_sample_average,
        pooled=pooled,
        n_ok=len(ok),
        n_failed=len(results) - len(ok) - n_skipped,
        n_skipped=n_skipped,
    )


def _print_metrics(metrics: dict[str, Optional[float]]) -> None:
    for key in METRIC_KEYS:
        print(f"  {key:<16}: {metrics[key]:.2%}")
    pos = metrics.get("position_accuracy")
    if pos is not None:
        print(f"  position_accuracy: {pos:.2%}")


def print_summary(
    results: list[SampleEvaluation], aggregates: Aggregates, verbose: bool = False
) -> None:
    sep = "─" * 60
    print(f"\n{sep}")
    print(
        f"  Evaluation report ({len(results)} samples, "
        f"{aggregates.n_ok} ok, {aggregates.n_skipped} skipped, "
        f"{aggregates.n_failed} failed)"
    )
    print(sep)

    for r in results:
        if r.skipped:
            print(f"\n  {r.sample_name}: SKIPPED")
            continue
        if not r.ok:
            print(f"\n  {r.sample_name}: FAILED - {r.error}")
            continue
        o = _metrics_of(r).overall
        pos = f" Pos={o.position_accuracy:.2%}" if o.position_accuracy is not None else ""
        print(
            f"\n  {r.sample_name}: F1={o.f1:.2%} Jaccard={o.jaccard:.2%}"
            f" Precision={o.precision:.2%} Recall={o.recall:.2%}{pos}"
        )
        if verbose:
            print_report(r.sample_name, _model_output_of(r), _metrics_of(r))

    print(f"\n{'═' * 40}")
    print("  PER-SAMPLE AVERAGE")
    print(f"{'═' * 40}")
    _print_metrics(aggregates.per_sample_average)

    print(f"\n{'═' * 40}")
    print("  POOLED")
    print(f"{'═' * 40}")
    _print_metrics(aggregates.pooled)

    print(f"\n{sep}\n")


def _metrics_to_dict(metrics: PerformanceMetrics) -> dict:
    per_category = {}
    for cat, cm in metrics.per_category.items():
        per_category[cat] = {
            "validated": cm.validated,
            "true_positives": cm.true_positives,
            "false_positives": cm.false_positives,
            "false_negatives": cm.false_negatives,
            "precision": cm.precision,
            "recall": cm.recall,
            "f1": cm.f1,
            "jaccard": cm.jaccard,
            "position_accuracy": cm.position_accuracy,
        }
    o = metrics.overall
    return {
        "per_category": per_category,
        "overall": {
            "precision": o.precision,
            "recall": o.recall,
            "f1": o.f1,
            "jaccard": o.jaccard,
            "position_accuracy": o.position_accuracy,
        },
    }


def _results_to_dict(
    results: list[SampleEvaluation], aggregates: Aggregates, meta: dict
) -> dict:
    return {
        "meta": meta,
        "per_sample": [
            {
                "sample": r.sample_name,
                "ok": r.ok,
                "skipped": r.skipped,
                "error": r.error,
                "metrics": _metrics_to_dict(r.metrics) if r.metrics else None,
            }
            for r in results
        ],
        "per_sample_average": aggregates.per_sample_average,
        "pooled": aggregates.pooled,
        "n_ok": aggregates.n_ok,
        "n_skipped": aggregates.n_skipped,
        "n_failed": aggregates.n_failed,
    }


def _load_model_fn(model_name: str) -> ModelFn:
    if model_name == "mock":
        from model.model import run_model

        return run_model
    from model.pipeline import execute_analysis

    return execute_analysis


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate the model against the samples ground truth"
    )
    parser.add_argument("--model", choices=["mock", "real"], default="mock")
    parser.add_argument("--samples-dir", default="samples")
    parser.add_argument(
        "--samples",
        default=None,
        help=(
            "Comma-separated list of sample folder names to evaluate "
            "(e.g. '00,02'). Default: all samples in --samples-dir."
        ),
    )
    parser.add_argument("--no-weather", action="store_true")
    parser.add_argument("--output", default="evaluation_results.json")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--fail-under",
        type=float,
        default=None,
        metavar="F1",
        help=(
            "Exit with a non-zero status if the pooled F1 score drops below "
            "this value (0-1). Useful as a regression gate in CI when "
            "iterating on the prompt or the pipeline."
        ),
    )
    args = parser.parse_args(argv)

    samples_dir = Path(args.samples_dir)
    if not samples_dir.is_dir():
        print(f"Samples directory not found: {samples_dir}")
        return 1

    samples = discover_samples(samples_dir)
    if args.samples:
        wanted = {name.strip() for name in args.samples.split(",") if name.strip()}
        unknown = wanted - {s["folder"] for s in samples}
        if unknown:
            print(f"Unknown sample folder(s): {', '.join(sorted(unknown))}")
            return 1
        samples = [s for s in samples if s["folder"] in wanted]

    if not samples:
        print(f"No samples found in {samples_dir}")
        return 1

    model_fn = _load_model_fn(args.model)
    use_weather = not args.no_weather

    results: list[SampleEvaluation] = []
    for i, sample in enumerate(samples, start=1):
        print(f"Evaluating sample {i}/{len(samples)}: {sample['folder']}")
        results.append(evaluate_sample(sample, model_fn, use_weather=use_weather))

    aggregates = aggregate(results)
    print_summary(results, aggregates, verbose=args.verbose)

    meta = {
        "date": datetime.now().isoformat(timespec="seconds"),
        "model": args.model,
        "use_weather": use_weather,
        "samples_dir": str(samples_dir),
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(_results_to_dict(results, aggregates, meta), f, indent=2)
    print(f"Results written to {args.output}")

    if aggregates.n_ok == 0:
        print("\nNo sample could be scored (all skipped or failed).")
        return 1

    if args.fail_under is not None:
        pooled_f1 = aggregates.pooled["f1"]
        if pooled_f1 < args.fail_under:
            print(
                f"\nPooled F1 {pooled_f1:.2%} is below the --fail-under "
                f"threshold {args.fail_under:.2%}."
            )
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())