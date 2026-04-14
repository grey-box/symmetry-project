
# Prototype Pipeline — Implementation Reference

**Status: Implemented and integrated into the production API**

The prototype is the Phase 1+2+3 pipeline described in [[Phase 1 outline]],
[[Phase 2 outline]], and [[Phase 3 outline]]. It lives at:

```
symmetry-unified-backend/
  app/services/similarity_prototype/
    article_comparator.py    ← main orchestrator (ArticleComparator class)
    wikipedia_parser.py      ← URL → paragraph sentences
    article_scorer.py        ← standalone scorer helper
    Phase_1/
      vectorizer.py          ← TF-IDF vector builder
      preprocessor.py        ← tokenize / stopword / stem
      similarity.py          ← cosine similarity helper
    Phase_2/
      synonym_matcher.py     ← WordNet Wu-Palmer matching
    Phase_3/
      syntax_parser.py       ← spaCy dependency parser
      role_comparator.py     ← role-by-role comparison
      scorer.py              ← Phase 1+2+3 weighted combiner
```

---

## How the phases combine

Each sentence pair goes through all three phases and the scores are combined
with fixed weights:

```
score = (phase_1_weight × TF-IDF cosine)
      + (phase_2_weight × WordNet best-token-match)
      + (phase_3_weight × spaCy role comparison)

Weights live in Scorer (Phase_3/scorer.py):
  phase_1 → 0.20
  phase_2 → 0.30
  phase_3 → 0.50
```

Phase 3 gets the highest weight because it uses both structure AND meaning
and directly handles active/passive normalization.

---

## Top-K pre-filter optimization

Running the full Phase 2+3 pipeline on every sentence pair in an N×M matrix
is expensive (WordNet lookups + spaCy parsing). The pipeline avoids O(N×M)
Phase 2+3 work using a two-stage strategy:

```
Step 1 — Phase 1 pre-filter (fast):
  Compute TF-IDF cosine for ALL N×M pairs using numpy matrix multiply.
  For each sentence in A, keep only the top-K candidates from B.
  Default: top_k = 8

Step 2 — Full pipeline (expensive, candidates only):
  Run Phase 2+3 only on the top-K candidates per sentence.
  All other pairs keep their Phase-1-only score.

Result:
  Phase 2+3 work drops from O(N×M) → O(N×K)
  Accuracy is nearly unchanged — the true best match is almost always
  in the top-8 TF-IDF candidates.
```

---

## Persistent worker pool

Phase 2 (WordNet) and Phase 3 (spaCy) have high startup costs — loading the
WordNet database and the spaCy `en_core_web_sm` model can take ~1 second per
worker. The pipeline solves this with a **module-level persistent pool**:

```
First comparison request:
  → Pool created with cpu_count() workers
  → Each worker loads WordNet + stores scoring constants
  → Cost paid once

All subsequent requests:
  → Existing workers reused (no startup cost)
  → New per-section data sent as task arguments
```

Workers are initialized via `_init_worker_persistent()` and store their state
in `_worker_state`. Per-section data (TF-IDF vectors, tokens, spaCy roles)
is pre-computed on the main process and passed as task arguments so the pool
does not need to restart between sections.

For very small inputs (≤ 60 scored pairs), the pipeline falls back to
sequential execution to avoid IPC overhead exceeding the benefit of
parallelism.

---

## Sentence cleaning and filtering

Before scoring, `ArticleComparator` cleans and validates each paragraph:

```python
clean_sentence():
  - Remove URLs
  - Collapse multiple spaces
  - Remove coordinate strings like (12°N 45°E)
  - Remove citation brackets like [1], [2]

is_valid_sentence():
  - Reject < 4 words
  - Reject Wikipedia boilerplate:
    "see also", "external links", "references",
    "further reading", "jump to", "retrieved from"
```

---

## Minimum match threshold

```
ArticleComparator.MIN_MATCH_THRESHOLD = 0.20

Pairs scoring below 0.20 are treated as no match (score → 0.0).
This is intentionally low to catch semantically related sentences
that use completely different vocabulary.

Example:
  "Cats are obligate carnivores"
  "Dogs are omnivores"
  → zero word overlap, but both about animal diet → should score ~0.35
```

The caller-supplied `similarity_threshold` from the API also applies
(see [[Similarity Threshold Settings]]). The effective match threshold is
`max(MIN_MATCH_THRESHOLD, similarity_threshold)`.

---

## Role comparison scoring (Phase 3 detail)

Roles are extracted by spaCy for each sentence:

```
subject → nsubj dependency
verb    → ROOT dependency (lemmatized)
object  → dobj or pobj dependency
prep    → prep dependency
modifiers → amod / advmod dependencies
```

Each role pair is scored with Wu-Palmer similarity, with special rules:

```
subject:
  - Skip if either side is a generic pronoun
    (it, they, he, she, we, i, you, this, that, ...)
  - Score 0.0 if no shared WordNet synset AND Wu-Palmer < 0.9

verb:
  - Apply antonym penalty if direct antonyms detected
  - Score 0.0 if no shared synset AND Wu-Palmer < 0.85

object:
  - Score 0.0 if no shared synset AND Wu-Palmer < 0.75

Role weights:
  subject   → 0.30
  verb      → 0.30
  object    → 0.25
  prep      → 0.15
  modifiers → small additional weight
```

---

## Integration with section_comparison.py

The prototype integrates with the production section comparison pipeline
via `_compare_paragraphs_prototype()` in `section_comparison.py`.

```
API call with model_name = "similarity_prototype":

  1. Section structure matching still uses LaBSE (multilingual transformer)
     because the prototype's NLP tools are English-only.

  2. For each matched section, paragraphs are translated to English
     using MarianMT (Helsinki-NLP models) before prototype scoring.
     Translation runs concurrently for both sides.

  3. Original (non-English) text is preserved in the ParagraphDiff
     output so the UI displays source-language content.

  4. ArticleComparator.build_score_matrix() is called on the
     English-translated paragraphs.

  5. Greedy best-match assignment using prototype scores,
     with caller-supplied similarity_threshold as the gate.
```

See [[Production Implementation]] for the full section comparison pipeline.

---

## Prototype score interpretation

```
~0.00–0.10  Completely unrelated sentences
~0.10–0.20  Weak signal (below MIN_MATCH_THRESHOLD, treated as no match)
~0.20–0.35  Related topic, different framing
~0.35–0.55  Same topic, partial content overlap
~0.55–0.75  Strong match (same content, different wording)
~0.75–1.00  Near-identical sentences

Tested benchmarks (article_comparator.py __main__ tests):
  Same article vs itself    → ~1.0
  Cat vs Dog (related)      → ~0.30–0.45
  Cat vs Quantum Mechanics  → ~0.00–0.10
```
