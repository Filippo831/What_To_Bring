import argparse
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_FEEDBACK_DIR = _PROJECT_ROOT / "feedback_data" / "cases"
_DEFAULT_SAMPLES_DIR = _PROJECT_ROOT / "samples"


def _discover_pending_cases(feedback_dir: Path, samples_dir: Path) -> list[Path]:
    """Cases with a feedback.json that haven't been promoted into samples/ yet."""
    if not feedback_dir.is_dir():
        return []
    pending = []
    for case_dir in sorted(feedback_dir.iterdir()):
        if not case_dir.is_dir():
            continue
        if not (case_dir / "feedback.json").exists():
            continue
        dest = samples_dir / f"fb-{case_dir.name}"
        if dest.exists():
            continue
        pending.append(case_dir)
    return pending


def _build_expected_output(model_output: dict, feedback: dict, case_id: str) -> dict:
    categories = feedback.get("categories", {})
    validated = list(categories.keys())

    expected: dict = {
        "_note": (
            f"Auto-generated from user feedback on case {case_id} "
            f"({feedback.get('submitted_at', 'unknown date')}). "
            "REVIEW BEFORE TRUSTING: this is self-reported by the user, not "
            "expert-validated. User comment: "
            f"{feedback.get('comment') or '(none)'}"
        ),
        "_validated_categories": validated,
    }
    for cat, entry in categories.items():
        if entry.get("accurate"):
            expected[cat] = {"items": model_output.get(cat, {}).get("items", [])}
        else:
            expected[cat] = {"items": entry.get("actual_items", [])}

    for cat in ("base", "middle", "insulation", "shell", "pants", "shoes", "gear"):
        expected.setdefault(cat, {"items": []})

    return expected


def promote_case(case_dir: Path, samples_dir: Path, *, dry_run: bool = False) -> Path:
    case_id = case_dir.name
    with open(case_dir / "feedback.json", encoding="utf-8") as f:
        feedback = json.load(f)
    with open(case_dir / "model_output.json", encoding="utf-8") as f:
        model_output = json.load(f)

    dest = samples_dir / f"fb-{case_id}"
    expected_output = _build_expected_output(model_output, feedback, case_id)

    if dry_run:
        print(f"[dry-run] would create {dest}")
        print(json.dumps(expected_output, indent=2))
        return dest

    dest.mkdir(parents=True, exist_ok=False)
    shutil.copy(case_dir / "course.gpx", dest / "course.gpx")
    shutil.copy(
        case_dir / "personal_information.json", dest / "personal_information.json"
    )
    shutil.copy(case_dir / "hike_information.json", dest / "hike_information.json")
    with open(dest / "expected_output.json", "w", encoding="utf-8") as f:
        json.dump(expected_output, f, indent=2)

    return dest


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--feedback-dir", default=str(_DEFAULT_FEEDBACK_DIR))
    parser.add_argument("--samples-dir", default=str(_DEFAULT_SAMPLES_DIR))
    parser.add_argument("--list", action="store_true", help="List pending cases and exit")
    parser.add_argument("--case", help="Promote a single case by id")
    parser.add_argument("--all", action="store_true", help="Promote every pending case")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be created without writing anything",
    )
    args = parser.parse_args(argv)

    feedback_dir = Path(args.feedback_dir)
    samples_dir = Path(args.samples_dir)

    pending = _discover_pending_cases(feedback_dir, samples_dir)

    if args.list or not (args.case or args.all):
        if not pending:
            print("No pending feedback cases to promote.")
        else:
            print(f"{len(pending)} pending case(s):")
            for case_dir in pending:
                with open(case_dir / "feedback.json", encoding="utf-8") as f:
                    fb = json.load(f)
                cats = ", ".join(fb.get("categories", {}).keys())
                print(f"  {case_dir.name}  (categories: {cats or 'none'})")
        return 0

    to_promote: list[Path] = []
    if args.case:
        case_dir = feedback_dir / args.case
        if not (case_dir / "feedback.json").exists():
            print(f"No feedback.json found for case '{args.case}' in {feedback_dir}")
            return 1
        to_promote = [case_dir]
    elif args.all:
        to_promote = pending

    if not to_promote:
        print("Nothing to promote.")
        return 0

    for case_dir in to_promote:
        dest = promote_case(case_dir, samples_dir, dry_run=args.dry_run)
        if not args.dry_run:
            print(f"Promoted {case_dir.name} -> {dest}")

    if not args.dry_run:
        print(
            f"\n{len(to_promote)} sample(s) added under {samples_dir}. "
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
