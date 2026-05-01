import difflib


def score_article_pair(text_a: str, text_b: str) -> float:
    """Return a SequenceMatcher similarity ratio between two text strings (0.0–1.0)."""
    return difflib.SequenceMatcher(None, text_a, text_b).ratio()
