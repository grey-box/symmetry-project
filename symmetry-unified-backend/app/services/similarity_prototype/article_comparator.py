import sys
import os
import re
import math
import multiprocessing
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from typing import List, Dict, Optional
from Phase_1.vectorizer import Vectorizer
from Phase_3.scorer import Scorer
from wikipedia_parser import parse_url_to_paragraph_sentences


# Pronouns to skip when comparing subject roles (mirrors role_comparator.py)
_GENERIC_PRONOUNS = frozenset({
    "it", "they", "he", "she", "we", "i", "you",
    "this", "that", "these", "those", "one", "there",
})

# ─── Module-level helpers used by multiprocessing workers ────────────────────
# These must be at module level (not inside a class or function) so that
# Python's "spawn" start method on Windows can pickle and find them.

# Each worker process stores its shared data here after _init_worker_persistent() runs.
_worker_state: dict = {}

# Module-level persistent pool – created once and reused across all section comparisons.
# Previously the pool was recreated per section, paying the ~1 s-per-worker spaCy /
# WordNet startup cost for every section.  With a persistent pool that cost is paid
# only on the very first comparison request.
_persistent_pool: Optional[multiprocessing.Pool] = None


def _init_worker_persistent(
    weights:              dict,
    role_weights:         dict,
    antonym_verb_penalty: float,
    known_antonym_pairs:  set,
) -> None:
    """Runs once per worker when the pool is first created.
    Loads the SynonymMatcher (WordNet + NLTK) and stores constant scoring
    parameters.  Per-section data (vectors, roles, tokens) is passed as
    task arguments instead so it does not need to be re-sent on every call."""
    from Phase_2.synonym_matcher import SynonymMatcher
    _worker_state.update({
        "weights":               weights,
        "role_weights":          role_weights,
        "antonym_verb_penalty":  antonym_verb_penalty,
        "known_antonym_pairs":   known_antonym_pairs,
        "matcher":               SynonymMatcher(),
    })


def _get_persistent_pool(
    weights:              dict,
    role_weights:         dict,
    antonym_verb_penalty: float,
    known_antonym_pairs:  set,
) -> multiprocessing.Pool:
    """Return the module-level worker pool, creating it on the first call."""
    global _persistent_pool
    if _persistent_pool is None:
        num_workers = multiprocessing.cpu_count()
        print(f"  Initializing persistent worker pool ({num_workers} workers)…")
        _persistent_pool = multiprocessing.Pool(
            processes=num_workers,
            initializer=_init_worker_persistent,
            initargs=(weights, role_weights, antonym_verb_penalty, known_antonym_pairs),
        )
    return _persistent_pool


def _cosine(vec_a: list, vec_b: list) -> float:
    """Cosine similarity between two vectors (inline to avoid object overhead)."""
    dot   = sum(a * b for a, b in zip(vec_a, vec_b))
    mag_a = math.sqrt(sum(a * a for a in vec_a))
    mag_b = math.sqrt(sum(b * b for b in vec_b))
    return dot / (mag_a * mag_b) if mag_a and mag_b else 0.0


def _compare_roles_worker(matcher, roles_a, roles_b, role_weights,
                          antonym_verb_penalty, known_antonym_pairs) -> float:
    """Standalone role comparison for use inside workers.
    Mirrors RoleComparator.compare_roles without needing the full object."""
    weighted_sum = 0.0
    total_weight = 0.0

    for role in ("subject", "verb", "object", "prep"):
        val_a = roles_a.get(role)
        val_b = roles_b.get(role)

        if val_a is None and val_b is None:
            continue
        if val_a is None or val_b is None:
            score = 0.1
        elif role == "subject" and (
            val_a.lower() in _GENERIC_PRONOUNS or val_b.lower() in _GENERIC_PRONOUNS
        ):
            # Pronoun subjects carry no topic information — skip entirely
            continue
        elif val_a == val_b:
            score = 1.0
        else:
            score = matcher.wu_palmer_similarity(val_a, val_b)
            if role == "subject":
                if not matcher.share_synset(val_a, val_b) and score < 0.9:
                    score = 0.0
            if role == "verb":
                is_antonym = (
                    matcher.are_direct_antonyms(val_a, val_b)
                    or (val_a, val_b) in known_antonym_pairs
                    or (val_b, val_a) in known_antonym_pairs
                )
                if is_antonym:
                    score -= antonym_verb_penalty
                elif not matcher.share_synset(val_a, val_b) and score < 0.85:
                    score = 0.0
            if role == "object":
                if not matcher.share_synset(val_a, val_b) and score < 0.75:
                    score = 0.0

        w             = role_weights[role]
        weighted_sum += score * w
        total_weight += w

    mods_a = roles_a.get("modifiers", [])
    mods_b = roles_b.get("modifiers", [])
    if mods_a or mods_b:
        if not mods_a or not mods_b:
            mod_score = 0.3
        else:
            mod_score = round(
                sum(max((matcher.wu_palmer_similarity(m_a, m_b) for m_b in mods_b), default=0.0)
                    for m_a in mods_a) / len(mods_a), 4)
        w             = role_weights["modifiers"]
        weighted_sum += mod_score * w
        total_weight += w

    return round(weighted_sum / total_weight, 4) if total_weight > 0 else 0.0


def _score_row(
    sent_a:           str,
    sentences_b:      list,
    candidate_indices,
    all_vectors:      dict,
    all_roles:        dict,
    all_tokens:       dict,
) -> list:
    """Compute one row of the score matrix.  Runs in a worker process.

    Per-section data (all_vectors, all_roles, all_tokens) is passed as
    arguments rather than read from _worker_state so the persistent pool
    does not need to be restarted between sections.

    candidate_indices: frozenset of column indices that should receive the full
    Phase 1+2+3 score.  All other columns get a Phase-1-only score so the
    expensive WordNet / role-comparison work is skipped for clearly unrelated
    pairs.  Pass None to score every column with the full pipeline.
    """
    st      = _worker_state
    matcher = st["matcher"]
    w       = st["weights"]

    vec_a    = all_vectors[sent_a]
    roles_a  = all_roles[sent_a]
    tokens_a = all_tokens[sent_a]

    row = []
    for j, sent_b in enumerate(sentences_b):
        # Phase 1 — cosine on pre-computed TF-IDF vectors (always computed)
        p1 = _cosine(vec_a, all_vectors[sent_b])

        if candidate_indices is not None and j not in candidate_indices:
            # Non-candidate: contribute Phase 1 weight only; skip costly lookups
            row.append(round(w["phase_1"] * p1, 4))
            continue

        # Phase 2 — WordNet synonym matching (candidates only)
        toks_b = all_tokens[sent_b]
        p2 = round((matcher.best_token_match(tokens_a, toks_b) +
                    matcher.best_token_match(toks_b, tokens_a)) / 2, 4)

        # Phase 3 — role comparison (candidates only)
        p3 = _compare_roles_worker(
            matcher, roles_a, all_roles[sent_b],
            st["role_weights"], st["antonym_verb_penalty"], st["known_antonym_pairs"],
        )

        row.append(round(w["phase_1"] * p1 + w["phase_2"] * p2 + w["phase_3"] * p3, 4))
    return row


class ArticleComparator:
    def __init__(self):
        self.scorer = Scorer()

        # Minimum score for a sentence pair to count as a genuine match
        # Lowered to 0.20 to catch more related sentences that use
        # different vocabulary but have similar meaning
        self.MIN_MATCH_THRESHOLD = 0.20

        # Stopwords used only in the diagnose() method for overlap analysis
        # No longer used as a gate in score_pair()
        self.STOPWORDS = {
            # Articles, pronouns, prepositions, conjunctions
            "the", "a", "an", "is", "are", "was", "were", "in", "on",
            "at", "to", "of", "and", "or", "it", "that", "this", "with",
            "for", "as", "be", "by", "its", "has", "have", "had", "been",
            "from", "which", "also", "into", "their", "they", "he", "she",
            "his", "her", "not", "but", "can", "more", "than", "about",
            "after", "during", "other", "such", "between", "when", "where",
            # Vague frequency/quantity words that appear everywhere
            "known", "used", "first", "one", "two", "three",
            "many", "most", "some", "all", "any", "each",
            # Modal verbs - not topic specific
            "may", "might", "could", "would", "should", "will",
            # Connectives and discourse markers
            "however", "although", "while", "since", "because",
            # Generic frequency adverbs
            "often", "usually", "generally", "typically", "commonly",
            # Generic nouns/adverbs that appear in all articles
            "well", "just", "time", "way", "part", "form",
            "number", "type", "example", "world", "life"
        }

    # ─────────────────────────────────────────────
    # SENTENCE CLEANING AND FILTERING
    # ─────────────────────────────────────────────

    # Remove noise from a sentence before processing
    def clean_sentence(self, sentence: str) -> str:
        # Remove URLs
        sentence = re.sub(r'http\S+', '', sentence)
        # Remove multiple spaces
        sentence = re.sub(r'\s+', ' ', sentence)
        # Remove geographic coordinates e.g. (12°N 45°E)
        sentence = re.sub(r'\(\d+°[NS].*?\)', '', sentence)
        # Remove citation brackets e.g. [1], [2]
        sentence = re.sub(r'\[\d+\]', '', sentence)
        return sentence.strip()

    # Check if a sentence is worth including
    # Filters out trivial, too-short, or boilerplate sentences
    def is_valid_sentence(self, sentence: str) -> bool:
        words = sentence.split()

        # Too short to be meaningful
        if len(words) < 4:
            return False

        # Common Wikipedia boilerplate to skip
        boilerplate = [
            "click here", "read more", "see also",
            "external links", "references", "further reading",
            "jump to", "retrieved from"
        ]
        lower = sentence.lower()
        if any(bp in lower for bp in boilerplate):
            return False

        return True

    # Extract a flat list of clean sentences from parsed article
    def get_flat_sentences(self, parsed: List[dict]) -> List[str]:
        flat = []
        for item in parsed:
            for sentence in item["sentences"]:
                cleaned = self.clean_sentence(sentence)
                if self.is_valid_sentence(cleaned):
                    flat.append(cleaned)
        return flat

    # ─────────────────────────────────────────────
    # WORD OVERLAP (DIAGNOSTIC USE ONLY)
    # ─────────────────────────────────────────────

    # Word overlap check kept for diagnostic purposes only
    # No longer used as a gate in score_pair()
    # The scorer itself handles filtering via low scores
    def quick_word_overlap(self, sentence_a: str, sentence_b: str) -> float:
        words_a = set(sentence_a.lower().split()) - self.STOPWORDS
        words_b = set(sentence_b.lower().split()) - self.STOPWORDS

        if not words_a or not words_b:
            return 0.0

        overlap = words_a & words_b
        if not overlap:
            return 0.0

        return len(overlap) / min(len(words_a), len(words_b))

    # ─────────────────────────────────────────────
    # SENTENCE PAIR SCORING
    # ─────────────────────────────────────────────

    # Score a single sentence pair using the full Phase 1+2+3 pipeline
    # No word overlap gate - the scorer handles unrelated sentences
    # naturally by returning low scores
    # This is more accurate than word overlap for cross-article comparison
    # because related sentences often use completely different vocabulary
    # Example:
    #   "Cats are obligate carnivores"
    #   "Dogs are omnivores"
    #   → zero word overlap but both about animal diet → should score ~0.35
    def score_pair(self, sentence_a: str, sentence_b: str) -> float:
        return self.scorer.score(sentence_a, sentence_b, verbose=False)

    # ─────────────────────────────────────────────
    # SCORE MATRIX
    # ─────────────────────────────────────────────

    # Build a matrix of all sentence pair scores
    # matrix[i][j] = score(sentences_a[i], sentences_b[j])
    # rows = sentences from Article A, cols = sentences from Article B
    #
    # Pre-computation (done once, before the hot loop):
    #   Phase 1 — TF-IDF vectors built from the full sentence pool.
    #   Phase 2 — preprocessed tokens stored per sentence.
    #   Phase 3 — spaCy roles extracted in one nlp.pipe() batch call.
    #
    # Parallelism: rows are distributed across CPU cores via
    # multiprocessing.Pool.  Each worker has its own SynonymMatcher with
    # its own WordNet cache, so there is no cross-process locking.
    # spaCy is NOT loaded in workers (lazy-load in SyntaxParser ensures this).
    def build_score_matrix(
        self,
        sentences_a: List[str],
        sentences_b: List[str],
        top_k: int = 8,
    ) -> List[List[float]]:
        """Build the N×M score matrix.

        top_k controls the candidate-pruning pre-filter: for each sentence in A
        the K sentences in B with the highest Phase-1 (TF-IDF cosine) score are
        selected as candidates and scored with the full Phase 1+2+3 pipeline.
        All other pairs receive a Phase-1-only score, skipping the expensive
        WordNet and role-comparison work.  This reduces Phase 2+3 work from
        O(N×M) to O(N×K), giving a large speedup on long articles without
        meaningfully affecting accuracy (the true best match is almost always
        among the top-K TF-IDF candidates).
        """
        total = len(sentences_a) * len(sentences_b)
        print(f"  Note: {total} pairs total — using top-{top_k} Phase-1 pre-filter")

        unique_sentences = list(dict.fromkeys(sentences_a + sentences_b))

        # ── Phase 1 pre-computation ──────────────────────────────────────────
        print("  Pre-computing TF-IDF vectors...", end="\r")
        vectorizer  = Vectorizer()
        all_vectors = vectorizer.get_vectors(unique_sentences)
        print("  Pre-computing TF-IDF vectors... done")

        # ── Phase 1 pre-filter: select top-K candidates per sentence_a ───────
        # Use numpy for a fast all-pairs cosine similarity matrix so we can
        # identify the best candidates without running Phase 2+3 on every pair.
        effective_k = min(top_k, len(sentences_b))
        candidate_sets: List = []

        if effective_k < len(sentences_b):
            print("  Selecting candidates via Phase-1 pre-filter...", end="\r")
            vecs_a = np.array([all_vectors[s] for s in sentences_a], dtype=np.float32)
            vecs_b = np.array([all_vectors[s] for s in sentences_b], dtype=np.float32)

            norms_a = np.linalg.norm(vecs_a, axis=1, keepdims=True)
            norms_b = np.linalg.norm(vecs_b, axis=1, keepdims=True)
            norms_a[norms_a == 0] = 1.0
            norms_b[norms_b == 0] = 1.0

            p1_matrix = (vecs_a / norms_a) @ (vecs_b / norms_b).T  # (N, M)

            for i in range(len(sentences_a)):
                top_indices = np.argpartition(p1_matrix[i], -effective_k)[-effective_k:]
                candidate_sets.append(frozenset(top_indices.tolist()))

            full_pairs = len(sentences_a) * effective_k
            print(f"  Candidates selected — Phase 2+3 pairs: {full_pairs} (was {total})")
        else:
            # Small enough to score everything with the full pipeline
            candidate_sets = [None] * len(sentences_a)
            print("  Article small enough — skipping pre-filter, scoring all pairs")

        # ── Phase 2 pre-computation ──────────────────────────────────────────
        # Cap tokens per paragraph to prevent O(N²) WordNet blowup.
        # Paragraphs can have 100+ tokens; 30 captures the main content words
        # while keeping best_token_match to at most 30×30 = 900 comparisons.
        _MAX_TOKENS = 30
        print("  Pre-computing tokens...        ", end="\r")
        preprocess = self.scorer.synonym_matcher.preprocessor.process
        all_tokens = {s: preprocess(s)[:_MAX_TOKENS] for s in unique_sentences}
        print("  Pre-computing tokens...         done")

        # ── Phase 3 pre-computation ──────────────────────────────────────────
        print("  Pre-computing spaCy roles...   ", end="\r")
        parser    = self.scorer.role_comparator.parser
        all_roles = parser.batch_extract_roles(unique_sentences)
        print("  Pre-computing spaCy roles...    done")

        # Constants needed by the standalone role-comparison helper in workers
        rc                   = self.scorer.role_comparator
        role_weights         = rc.ROLE_WEIGHTS
        antonym_verb_penalty = rc.ANTONYM_VERB_PENALTY
        known_antonym_pairs  = rc.KNOWN_ANTONYM_PAIRS

        # ── Parallel vs sequential decision ──────────────────────────────────
        # For very small inputs the IPC overhead of distributing tasks to the
        # pool exceeds the benefit of parallelism, so fall back to sequential.
        # The persistent pool means we no longer pay spaCy startup per section,
        # so this threshold only guards against task-distribution overhead.
        total_scored_pairs = len(sentences_a) * (
            effective_k if effective_k < len(sentences_b) else len(sentences_b)
        )
        _SEQUENTIAL_THRESHOLD = 60  # pairs below which sequential is faster

        if total_scored_pairs <= _SEQUENTIAL_THRESHOLD:
            print(f"  Building score matrix sequentially ({total_scored_pairs} pairs)...")
            _init_worker_persistent(
                self.scorer.WEIGHTS, role_weights,
                antonym_verb_penalty, known_antonym_pairs,
            )
            matrix = [
                _score_row(sent_a, sentences_b, candidate_sets[i],
                           all_vectors, all_roles, all_tokens)
                for i, sent_a in enumerate(sentences_a)
            ]
        else:
            pool = _get_persistent_pool(
                self.scorer.WEIGHTS, role_weights,
                antonym_verb_penalty, known_antonym_pairs,
            )
            print(f"  Building score matrix with {multiprocessing.cpu_count()} workers...")
            matrix = pool.starmap(
                _score_row,
                [
                    (sent_a, sentences_b, candidate_sets[i],
                     all_vectors, all_roles, all_tokens)
                    for i, sent_a in enumerate(sentences_a)
                ],
            )

        return matrix

    # ─────────────────────────────────────────────
    # BEST MATCH AGGREGATION
    # ─────────────────────────────────────────────

    # For each sentence in one article, find its best matching
    # sentence in the other article
    # direction="AB": for each sentence in A, find best match in B
    # direction="BA": for each sentence in B, find best match in A
    # Scores below MIN_MATCH_THRESHOLD are treated as no match (0.0)
    def best_match_scores(self, matrix: List[List[float]], direction: str) -> List[float]:
        scores = []

        if direction == "AB":
            # Each row = one sentence from A
            # Find the max score across all B sentences
            for row in matrix:
                best = max(row) if row else 0.0
                scores.append(best if best >= self.MIN_MATCH_THRESHOLD else 0.0)

        elif direction == "BA":
            # Each column = one sentence from B
            # Find the max score across all A sentences
            if not matrix:
                return []
            num_cols = len(matrix[0])
            for col_idx in range(num_cols):
                best = max(row[col_idx] for row in matrix)
                scores.append(best if best >= self.MIN_MATCH_THRESHOLD else 0.0)

        return scores

    # ─────────────────────────────────────────────
    # DIAGNOSTIC
    # ─────────────────────────────────────────────

    # Diagnostic tool to understand scoring behavior
    # Shows sample sentences, top matching pairs, and overlap distribution
    # Use this to debug unexpected scores
    def diagnose(self, sentences_a: List[str], sentences_b: List[str], top_n: int = 5):
        print("\n=== DIAGNOSIS ===")

        # Show sample sentences from each article
        print("\nSample sentences from Article A:")
        for i, s in enumerate(sentences_a[:5]):
            print(f"  A{i+1}: {s[:100]}")

        print("\nSample sentences from Article B:")
        for i, s in enumerate(sentences_b[:5]):
            print(f"  B{i+1}: {s[:100]}")

        # Find and rank best matching pairs
        print(f"\nTop {top_n} best matching pairs:")
        best_pairs = []
        for sent_a in sentences_a:
            for sent_b in sentences_b:
                overlap = self.quick_word_overlap(sent_a, sent_b)
                score   = self.score_pair(sent_a, sent_b)
                if score > 0:
                    best_pairs.append((score, overlap, sent_a[:80], sent_b[:80]))

        best_pairs.sort(reverse=True)
        for score, overlap, a, b in best_pairs[:top_n]:
            print(f"\n  Score: {score:.4f} | Overlap: {overlap:.4f}")
            print(f"  A: {a}")
            print(f"  B: {b}")

        # Show word overlap distribution for context
        print("\nWord overlap distribution:")
        zero   = sum(1 for s_a in sentences_a for s_b in sentences_b
                     if self.quick_word_overlap(s_a, s_b) == 0.0)
        low    = sum(1 for s_a in sentences_a for s_b in sentences_b
                     if 0.0 < self.quick_word_overlap(s_a, s_b) < 0.2)
        medium = sum(1 for s_a in sentences_a for s_b in sentences_b
                     if 0.2 <= self.quick_word_overlap(s_a, s_b) < 0.5)
        high   = sum(1 for s_a in sentences_a for s_b in sentences_b
                     if self.quick_word_overlap(s_a, s_b) >= 0.5)
        total  = len(sentences_a) * len(sentences_b)

        print(f"  Zero overlap:   {zero}/{total}  ({zero/total*100:.1f}%)")
        print(f"  Low  (0-0.2):   {low}/{total}   ({low/total*100:.1f}%)")
        print(f"  Med  (0.2-0.5): {medium}/{total} ({medium/total*100:.1f}%)")
        print(f"  High (0.5+):    {high}/{total}   ({high/total*100:.1f}%)")


    def diagnose_scores(self, sentences_a: List[str], sentences_b: List[str]):
        print("\n=== SCORE DISTRIBUTION ===")
        all_scores = []
        for sent_a in sentences_a:
            for sent_b in sentences_b:
                score = self.score_pair(sent_a, sent_b)
                all_scores.append(score)

        ranges = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        total = len(all_scores)
        for i in range(len(ranges)-1):
            count = sum(1 for s in all_scores if ranges[i] <= s < ranges[i+1])
            bar = "█" * int(count / total * 40)
            print(f"  {ranges[i]:.1f}-{ranges[i+1]:.1f}: {count:4d}/{total} {bar}")
    # ─────────────────────────────────────────────
    # MAIN ARTICLE COMPARISON
    # ─────────────────────────────────────────────

    # Compare two articles and return a similarity score 0-1
    # Uses symmetric best match aggregation:
    #   1. For each sentence in A, find best match in B → A→B score
    #   2. For each sentence in B, find best match in A → B→A score
    #   3. Average A→B and B→A → final score
    # Symmetric approach handles articles of different lengths fairly
    def compare(self, sentences_a: List[str], sentences_b: List[str], verbose: bool = True) -> float:
        if not sentences_a or not sentences_b:
            return 0.0

        if verbose:
            print(f"\n  Article A: {len(sentences_a)} sentences")
            print(f"  Article B: {len(sentences_b)} sentences")
            print(f"  Total comparisons: {len(sentences_a) * len(sentences_b)}")
            print(f"\n  Building score matrix...")

        # Build full score matrix
        matrix = self.build_score_matrix(sentences_a, sentences_b)

        # A → B direction: how well does A's content match B?
        ab_scores = self.best_match_scores(matrix, direction="AB")
        ab_avg    = sum(ab_scores) / len(ab_scores) if ab_scores else 0.0

        # B → A direction: how well does B's content match A?
        ba_scores = self.best_match_scores(matrix, direction="BA")
        ba_avg    = sum(ba_scores) / len(ba_scores) if ba_scores else 0.0

        # Symmetric final score
        final = round((ab_avg + ba_avg) / 2, 4)

        if verbose:
            ab_matched = sum(1 for s in ab_scores if s > 0)
            ba_matched = sum(1 for s in ba_scores if s > 0)

            print(f"\n  A→B: {ab_matched}/{len(sentences_a)} sentences matched")
            print(f"  A→B average score: {ab_avg:.4f}")
            print(f"\n  B→A: {ba_matched}/{len(sentences_b)} sentences matched")
            print(f"  B→A average score: {ba_avg:.4f}")
            print(f"\n  ─────────────────────────────────")
            print(f"  Final Article Score: {final}")

        return final


# ─────────────────────────────────────────────
# TESTING
# ─────────────────────────────────────────────
if __name__ == "__main__":
    comparator = ArticleComparator()

    # Test 1: Same article vs itself — expect ~1.0
    print("=" * 70)
    print("TEST 1: Same article vs itself (expect ~1.0)")
    print("=" * 70)
    url = "https://en.wikipedia.org/wiki/Cat"
    parsed = parse_url_to_paragraph_sentences(url, max_paragraphs=5)
    sentences = comparator.get_flat_sentences(parsed)
    score = comparator.compare(sentences, sentences)
    print(f"\n► Score: {score}")

    # Test 2: Related articles — expect ~0.30-0.45
    print("\n" + "=" * 70)
    print("TEST 2: Related articles - Cat vs Dog (expect ~0.30-0.45)")
    print("=" * 70)
    parsed_a = parse_url_to_paragraph_sentences(
        "https://en.wikipedia.org/wiki/Cat", max_paragraphs=5)
    parsed_b = parse_url_to_paragraph_sentences(
        "https://en.wikipedia.org/wiki/Dog", max_paragraphs=5)
    sentences_a = comparator.get_flat_sentences(parsed_a)
    sentences_b = comparator.get_flat_sentences(parsed_b)
    
    print("\nCat vs Dog score distribution:")

    score = comparator.compare(sentences_a, sentences_b)
    
    print(f"\n► Score: {score}")

    # Test 3: Unrelated articles — expect ~0.0-0.10
    print("\n" + "=" * 70)
    print("TEST 3: Unrelated articles - Cat vs Quantum Physics (expect ~0.0-0.10)")
    print("=" * 70)
    parsed_c = parse_url_to_paragraph_sentences(
        "https://en.wikipedia.org/wiki/Quantum_mechanics", max_paragraphs=5)
    sentences_c = comparator.get_flat_sentences(parsed_c)

    print("\nCat vs Quantum Physics score distribution:")
    
    score = comparator.compare(sentences_a, sentences_c)
    print(f"\n► Score: {score}")