import json
from pathlib import Path

from scripts.evaluate_matching import calculate_metrics


DATA_DIR = Path(__file__).parent / "data"
LABELS_PATH = DATA_DIR / "matching_evaluation.json"


def test_matching_evaluation_dataset_is_valid():
    evaluation = json.loads(LABELS_PATH.read_text(encoding="utf-8"))

    assert evaluation["version"] == 1
    assert evaluation["article_pairs"]

    for case in evaluation["article_pairs"]:
        source_path = DATA_DIR / case["source_file"]
        target_path = DATA_DIR / case["target_file"]

        assert source_path.exists()
        assert target_path.exists()
        assert case["expected_matches"]

        source_lines = [
            line
            for line in source_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        target_lines = [
            line
            for line in target_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        for match in case["expected_matches"]:
            assert 0 <= match["source_index"] < len(source_lines)
            assert 0 <= match["target_index"] < len(target_lines)


def test_calculate_metrics_for_perfect_matches():
    expected = {(0, 0), (1, 5), (3, 2)}
    predicted = {(0, 0), (1, 5), (3, 2)}

    metrics = calculate_metrics(expected, predicted)

    assert metrics["true_positives"] == 3
    assert metrics["false_positives"] == 0
    assert metrics["false_negatives"] == 0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0


def test_calculate_metrics_for_partial_matches():
    expected = {(0, 0), (1, 1)}
    predicted = {(0, 0), (2, 2)}

    metrics = calculate_metrics(expected, predicted)

    assert metrics["true_positives"] == 1
    assert metrics["false_positives"] == 1
    assert metrics["false_negatives"] == 1
    assert metrics["precision"] == 0.5
    assert metrics["recall"] == 0.5
    assert metrics["f1"] == 0.5