
# Production Implementation — Section Comparison Pipeline

**Status: Live**
**Source:** `symmetry-unified-backend/app/services/section_comparison.py`

The production comparison system matches Wikipedia articles section-by-section
and paragraph-by-paragraph using multilingual sentence transformers (LaBSE)
with Levenshtein distance as a disambiguation tiebreaker.

---

## Two comparison modes

The API accepts a `model_name` parameter to select between two pipelines:

```
model_name = "sentence-transformers/LaBSE"  (default)
  → Full multilingual embedding pipeline
  → Works directly on any language pair
  → No translation required

model_name = "similarity_prototype"
  → Phase 1+2+3 custom NLP pipeline (see [[Prototype Pipeline]])
  → Sections still matched with LaBSE (multilingual)
  → Paragraphs translated to English, then scored by prototype
```

Other sentence-transformer models from the [[Model Registry]] can also be
passed and will work the same as LaBSE for both section and paragraph matching.

---

## Step-by-step pipeline

### Step 1 — Section matching

Sections from the source article are matched to sections from the target
article using a **greedy best-match** algorithm:

```
For each section, build a representation:
  text = section.title + ". " + section.clean_content[:200]

Encode all source and target section texts with the transformer model.

Build a cosine similarity matrix:
  sim_matrix[i][j] = cosine_similarity(source[i], target[j])

Greedy assignment:
  Sort all (i, j) pairs by similarity descending.
  Pick the best pair where neither i nor j has been used.
  Accept only if score ≥ similarity_threshold.
  Repeat until no pairs remain above threshold.

Result:
  matched_pairs    → list of (source_idx, target_idx, score)
  unmatched_source → sections missing in target
  unmatched_target → sections added in target
```

### Step 2 — Paragraph splitting

Each matched section is split into paragraph-sized chunks:

```
Primary: split on double-newline (\n\n) — preserves HTML <p> boundaries

Fallback (for long single-paragraph sections > 300 chars):
  Split on sentence boundaries (period/!/?  followed by whitespace)
  Group sentences into ~150-word chunks
```

### Step 3 — Paragraph matching

For each matched section pair, paragraphs are matched with the same greedy
strategy as sections, but with Levenshtein disambiguation:

```
1. Encode all source and target paragraphs with the transformer.
2. Compute cosine similarity matrix.
3. For each source paragraph, sort target candidates by cosine score.
4. Levenshtein disambiguation:
     if top_score - second_score < LEVENSHTEIN_DISAMBIGUATION_MARGIN (0.08):
       compute normalized Levenshtein for both candidates
       pick whichever scores higher on Levenshtein
5. Accept match if final score ≥ similarity_threshold.
6. Remaining unmatched target paragraphs → status "added_in_target".
```

### Step 4 — Result assembly

```python
SectionCompareResponse:
  source_title, target_title
  source_lang, target_lang
  source_section_count, target_section_count
  matched_section_count
  missing_section_count   # in source, not in target
  added_section_count     # in target, not in source
  overall_similarity      # average similarity of matched sections
  model_name
  section_diffs: List[SectionDiff]
    ├── source_title, target_title
    ├── section_similarity
    ├── status: "matched" | "missing_in_target" | "added_in_target"
    └── paragraph_diffs: List[ParagraphDiff]
          ├── source_text, target_text
          ├── similarity_score
          ├── levenshtein_score  (set when disambiguation ran)
          └── status: "matched" | "missing_in_target" | "added_in_target"
```

---

## Levenshtein disambiguation

Cosine similarity from transformer embeddings can be ambiguous when two
candidate paragraphs have nearly identical semantic scores. Levenshtein
distance (character-level edit distance) provides a complementary signal
that is sensitive to surface-level differences.

```
When it fires:
  top_score - second_score < 0.08 (LEVENSHTEIN_DISAMBIGUATION_MARGIN)

Formula:
  normalized_levenshtein = 1 - (edit_distance / max(len(A), len(B)))
  → 0.0 = completely different strings
  → 1.0 = identical strings

Decision:
  If Levenshtein favors the second candidate over the first,
  swap the selection. The levenshtein_score is recorded in the
  ParagraphDiff for transparency.
```

See [[Similarity Threshold Settings]] for the margin value and how to override it.

---

## Model caching

Models are loaded on demand and kept in a module-level `_model_cache` dict.
The first request for a given model name pays the load cost (~5–15 s for LaBSE);
subsequent requests reuse the cached model.

```python
# section_comparison.py
_model_cache: dict = {}

def _get_model(model_name: str) -> SentenceTransformer:
    if model_name not in _model_cache:
        _model_cache[model_name] = SentenceTransformer(model_name)
    return _model_cache[model_name]
```

---

## API endpoint

```
POST /symmetry/v1/articles/compare-sections

Body:
{
  "source_query":        "Cat",
  "target_query":        "Cat",
  "source_lang":         "en",
  "target_lang":         "es",
  "similarity_threshold": 0.5,      # optional, default 0.65
  "model_name":          "sentence-transformers/LaBSE"  # optional
}
```

The `source_query` and `target_query` can be article titles or Wikipedia URLs.
When comparing the same article across languages, both fields are typically
the same title.

---

## Similarity score interpretation (LaBSE)

```
0.90–1.00  Near-identical content (often direct translations)
0.75–0.90  Strong match — same content, minor differences
0.65–0.75  Moderate match — related content, some gaps
0.50–0.65  Weak match — same topic, significant differences
< 0.50     Sections treated as unmatched (below default threshold)
```

These ranges are approximate and vary by language pair. Related languages
(e.g. Spanish ↔ Portuguese) tend to score higher for equivalent content
than unrelated language pairs (e.g. English ↔ Arabic).

See [[Similarity Threshold Settings]] for how language family thresholds
are used in the lexical scoring module.

---

## Prototype mode flow (model_name = "similarity_prototype")

```
Section matching:    LaBSE embeddings (multilingual — same as default)
                            ↓
Paragraph matching:  Translate both sides to English via MarianMT
                     (concurrent translation with ThreadPoolExecutor)
                            ↓
                     ArticleComparator.build_score_matrix()
                     (Phase 1+2+3 pipeline — see [[Prototype Pipeline]])
                            ↓
                     Greedy assignment with caller's similarity_threshold
                     (falls back to MIN_MATCH_THRESHOLD = 0.20 if None)
                            ↓
                     Original (non-English) text preserved in output
```
