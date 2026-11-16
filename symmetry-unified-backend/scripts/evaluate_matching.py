"""Evaluate paragraph matching against hand-labeled article pairs."""

import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = BACKEND_ROOT / "tests" / "data"

sys.path.insert(0, str(BACKEND_ROOT))

from app.core.settings import SIMILARITY_THRESHOLD
from app.services.section_comparison import _compare_paragraphs, _get_model


def load_paragraphs(filename: str) -> list[str]:
    """Load non-empty lines as fixed paragraph snapshots."""
    path = DATA_DIR / filename
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def calculate_metrics(
    expected: set[tuple[int, int]],
    predicted: set[tuple[int, int]],
) -> dict[str, float | int]:
    """Calculate precision, recall, and F1 for predicted matches."""
    true_positives = len(expected & predicted)
    false_positives = len(predicted - expected)
    false_negatives = len(expected - predicted)

    precision = (
        true_positives / (true_positives + false_positives)
        if true_positives + false_positives
        else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if true_positives + false_negatives
        else 0.0
    )
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision + recall
        else 0.0
    )

    return {
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def evaluate_pair(case: dict, model) -> dict[str, float | int]:
    """Run the matcher and score one labeled article pair."""
    source = load_paragraphs(case["source_file"])
    target = load_paragraphs(case["target_file"])

    diffs = _compare_paragraphs(
        source,
        target,
        model,
        SIMILARITY_THRESHOLD,
        case["source_language"],
        case["target_language"],
    )

    predicted: set[tuple[int, int]] = set()

    for diff in diffs:
        if diff.status == "matched":
            source_index = source.index(diff.source_text)
            target_index = target.index(diff.target_text)
            predicted.add((source_index, target_index))

    expected = {
        (match["source_index"], match["target_index"])
        for match in case["expected_matches"]
    }

    metrics = calculate_metrics(expected, predicted)

    print(f"\nEvaluation case: {case['id']}")
    print(f"Expected matches:  {sorted(expected)}")
    print(f"Predicted matches: {sorted(predicted)}")
    print(f"Precision: {metrics['precision']:.3f}")
    print(f"Recall:    {metrics['recall']:.3f}")
    print(f"F1 score:  {metrics['f1']:.3f}")

    return metrics


def main() -> None:
    labels_path = DATA_DIR / "matching_evaluation.json"
    evaluation = json.loads(labels_path.read_text(encoding="utf-8"))

    print("Loading LaBSE matching model...")
    model = _get_model("sentence-transformers/LaBSE")

    results = [
        evaluate_pair(case, model)
        for case in evaluation["article_pairs"]
    ]

    average_precision = sum(r["precision"] for r in results) / len(results)
    average_recall = sum(r["recall"] for r in results) / len(results)
    average_f1 = sum(r["f1"] for r in results) / len(results)

    print("\nOverall results")
    print(f"Precision: {average_precision:.3f}")
    print(f"Recall:    {average_recall:.3f}")
    print(f"F1 score:  {average_f1:.3f}")


if __name__ == "__main__":
    main()