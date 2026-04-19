import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Optional, List, Dict
from wikipedia_parser import get_flat_sentences
from article_comparator import ArticleComparator


class ArticleScorer:
    """Phase 4 top-level entry point.

    Accepts two Wikipedia URLs and returns a similarity score using the
    full Phase 1+2+3 pipeline via ArticleComparator.

    Usage
    -----
    scorer = ArticleScorer(max_paragraphs=10)
    score  = scorer.score(url_a, url_b)
    detail = scorer.score_with_details(url_a, url_b)
    """

    def __init__(self, max_paragraphs: Optional[int] = None):
        # max_paragraphs=None uses the full article; set a limit to trade
        # accuracy for speed during development / testing.
        self.max_paragraphs = max_paragraphs
        self.comparator     = ArticleComparator()

    # ─────────────────────────────────────────────
    # INTERNAL HELPERS
    # ─────────────────────────────────────────────

    def _fetch_sentences(self, url: str) -> List[str]:
        """Fetch and clean sentences from a Wikipedia URL."""
        raw_sentences = get_flat_sentences(url, self.max_paragraphs)
        # Apply ArticleComparator's cleaning/filtering on top of the parser's
        # basic cleaning, so both paths use identical sentence quality gates.
        return [
            self.comparator.clean_sentence(s)
            for s in raw_sentences
            if self.comparator.is_valid_sentence(s)
        ]

    def _top_matches(
        self,
        sentences_a: List[str],
        sentences_b: List[str],
        matrix:      List[List[float]],
        top_n:       int = 5,
    ) -> List[Dict]:
        """Return the top_n highest-scoring sentence pairs from the matrix."""
        pairs = [
            (matrix[i][j], sentences_a[i], sentences_b[j])
            for i in range(len(sentences_a))
            for j in range(len(sentences_b))
            if matrix[i][j] > 0
        ]
        pairs.sort(reverse=True)
        return [
            {"score": score, "sentence_a": s_a, "sentence_b": s_b}
            for score, s_a, s_b in pairs[:top_n]
        ]

    # ─────────────────────────────────────────────
    # PUBLIC API
    # ─────────────────────────────────────────────

    def score(self, url_a: str, url_b: str) -> float:
        """Fetch both articles and return a similarity score in [0, 1].

        This is the fast path: no intermediate results are kept.
        Use score_with_details() if you need the breakdown.
        """
        sentences_a = self._fetch_sentences(url_a)
        sentences_b = self._fetch_sentences(url_b)
        return self.comparator.compare(sentences_a, sentences_b, verbose=False)

    def score_with_details(self, url_a: str, url_b: str, top_n: int = 5) -> Dict:
        """Fetch both articles and return a score plus a full breakdown.

        Returns
        -------
        dict with keys:
            url_a, url_b        — the input URLs
            score               — final symmetric similarity score [0, 1]
            sentences_a         — number of sentences extracted from A
            sentences_b         — number of sentences extracted from B
            ab_matched          — sentences in A that found a match in B
            ba_matched          — sentences in B that found a match in A
            ab_avg              — average best-match score A→B
            ba_avg              — average best-match score B→A
            top_matches         — list of top_n highest-scoring sentence pairs,
                                  each with keys: score, sentence_a, sentence_b
            error               — only present if fetching/parsing failed
        """
        sentences_a = self._fetch_sentences(url_a)
        sentences_b = self._fetch_sentences(url_b)

        if not sentences_a or not sentences_b:
            return {
                "url_a": url_a,
                "url_b": url_b,
                "score": 0.0,
                "error": "Could not extract sentences from one or both articles.",
            }

        # Build the matrix once and reuse it for both directions + top matches
        matrix = self.comparator.build_score_matrix(sentences_a, sentences_b)

        ab_scores  = self.comparator.best_match_scores(matrix, direction="AB")
        ab_matched = sum(1 for s in ab_scores if s > 0)
        ab_avg     = sum(ab_scores) / len(ab_scores) if ab_scores else 0.0

        ba_scores  = self.comparator.best_match_scores(matrix, direction="BA")
        ba_matched = sum(1 for s in ba_scores if s > 0)
        ba_avg     = sum(ba_scores) / len(ba_scores) if ba_scores else 0.0

        final_score = round((ab_avg + ba_avg) / 2, 4)

        return {
            "url_a":       url_a,
            "url_b":       url_b,
            "score":       final_score,
            "sentences_a": len(sentences_a),
            "sentences_b": len(sentences_b),
            "ab_matched":  ab_matched,
            "ba_matched":  ba_matched,
            "ab_avg":      round(ab_avg, 4),
            "ba_avg":      round(ba_avg, 4),
            "top_matches": self._top_matches(sentences_a, sentences_b, matrix, top_n),
        }


# ─────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────
if __name__ == "__main__":
    scorer = ArticleScorer(max_paragraphs=5)

    tests = [
        (
            "https://en.wikipedia.org/wiki/Cat",
            "https://en.wikipedia.org/wiki/Cat",
            "Same article (expect ~1.0)",
        ),
        (
            "https://en.wikipedia.org/wiki/Cat",
            "https://en.wikipedia.org/wiki/Dog",
            "Related articles (expect ~0.30–0.45)",
        ),
        (
            "https://en.wikipedia.org/wiki/Cat",
            "https://en.wikipedia.org/wiki/Quantum_mechanics",
            "Unrelated articles (expect ~0.0–0.10)",
        ),
    ]

    for url_a, url_b, label in tests:
        print("=" * 70)
        print(f"TEST: {label}")
        print("=" * 70)

        d = scorer.score_with_details(url_a, url_b)

        if "error" in d:
            print(f"  ERROR: {d['error']}")
            continue

        print(f"  Sentences:   {d['sentences_a']} (A)  vs  {d['sentences_b']} (B)")
        print(f"  A→B matched: {d['ab_matched']}/{d['sentences_a']}  "
              f"(avg {d['ab_avg']:.4f})")
        print(f"  B→A matched: {d['ba_matched']}/{d['sentences_b']}  "
              f"(avg {d['ba_avg']:.4f})")
        print(f"\n  ► Score: {d['score']}")

        if d["top_matches"]:
            print(f"\n  Top {len(d['top_matches'])} matching sentence pairs:")
            for m in d["top_matches"]:
                print(f"\n    [{m['score']:.4f}]")
                print(f"      A: {m['sentence_a'][:90]}")
                print(f"      B: {m['sentence_b'][:90]}")
        print()
