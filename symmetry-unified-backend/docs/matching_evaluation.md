# Section and Paragraph Matching Evaluation

This evaluation provides a repeatable way to measure paragraph-matching
accuracy against fixed, hand-labeled article snapshots.

## Files

- `tests/data/matching_evaluation.json` contains expected paragraph matches.
- `tests/data/obama_A.txt` and `obama_B.txt` are fixed article snapshots.
- `scripts/evaluate_matching.py` runs the matcher and reports precision,
  recall, and F1.
- `tests/test_matching_evaluation.py` validates the dataset and metric logic.

## Running the evaluation

From `symmetry-unified-backend`, run:

```bash
python scripts/evaluate_matching.py