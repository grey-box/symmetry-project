# Similarity Threshold Algorithm

Complete documentation for Project Symmetry's similarity scoring system, covering both the research prototype (Phases 1–3) and the production LaBSE-based pipeline.

---

## Table of Contents

1. [Road Map Overview](#road-map-overview)
2. [Phase 1 — TF-IDF + Cosine Similarity](#phase-1--tf-idf--cosine-similarity)
3. [Phase 2 — WordNet + Wu-Palmer Similarity](#phase-2--wordnet--wu-palmer-similarity)
4. [Phase 3 — spaCy Dependency Parsing](#phase-3--spacy-dependency-parsing)
5. [Phase 4 — Word Co-occurrence Matrix (Planned)](#phase-4--word-co-occurrence-matrix-planned)
6. [Prototype Pipeline — Implementation Reference](#prototype-pipeline--implementation-reference)
7. [Production Implementation — Section Comparison Pipeline](#production-implementation--section-comparison-pipeline)
8. [Similarity Threshold Settings](#similarity-threshold-settings)

---

## Quick Reference — Threshold Defaults

| Setting | Default | Where used |
|---------|---------|-----------|
| `SIMILARITY_THRESHOLD` | `0.65` | Section + paragraph matching |
| `LEVENSHTEIN_DISAMBIGUATION_MARGIN` | `0.08` | Paragraph tiebreaker |
| `FAMILY_THRESHOLD_SAME` | `0.50` | Same language family |
| `FAMILY_THRESHOLD_IE_BRANCHES` | `0.60` | Different IE branches |
| `FAMILY_THRESHOLD_UNRELATED` | `0.70` | Unrelated families |
| Prototype `MIN_MATCH_THRESHOLD` | `0.20` | Prototype paragraph match |

---

## Road Map Overview

> **Implementation status**
> Phases 1–3 are **implemented** in `similarity_prototype/` and integrated into
> the production API via `model_name = "similarity_prototype"`.
> Phase 4 is **planned but not yet implemented**.
> The primary production pipeline uses LaBSE sentence transformers — see
> [Production Implementation](#production-implementation--section-comparison-pipeline) for details.

**Phase 1: Word Overlap (Simplest)**
TF-IDF + Cosine Similarity

```
How it works:
1. Build a vocabulary of all words across both sentences
2. Score each word by how unique/important it is
3. Represent each sentence as a vector of these scores
4. Cosine similarity between vectors = 0-1 score

Pros: Simple, fast, no ML needed
Cons: "cat" and "feline" = completely different (no synonym knowledge)
```

**Phase 2: Add Synonym Knowledge**
WordNet + Wu-Palmer Similarity

```
How it works:
1. For each word, look up synonyms in WordNet (a free word database)
2. Match words by meaning not just spelling
3. Score based on best word-to-word matches

Pros: Handles synonyms like cat/feline
Cons: Still struggles with sentence structure, passive/active voice
Library needed: nltk.corpus.wordnet (just a static database, not a model)
```

**Phase 3: Handle Sentence Structure**
Syntactic Tree Matching

```
How it works:
1. Parse both sentences into a syntax tree (subject, verb, object)
2. Compare the trees structurally
3. Active/passive becomes same structure after parsing:

"The dog bit the man"     → subject=dog,  verb=bite, object=man
"The man was bitten by the dog" → subject=dog, verb=bite, object=man
                                    ↑ same after normalization!

Pros: Solves active/passive problem directly
Cons: More complex to implement
Library needed: spaCy (a parser, not a trained similarity model)
```

**Phase 4: Build Your Own Vector Space** *(planned)*
Word Co-occurrence Matrix (poor man's Word2Vec)

```
How it works:
1. Take a large corpus of text (e.g. Wikipedia dump)
2. Count how often words appear near each other
3. Words with similar contexts get similar vectors
4. Average word vectors to get sentence vectors
5. Cosine similarity for final score

Pros: Learns meaning from context, no pretrained model
Cons: Need a large corpus, takes time to build
```

**Full Pipeline combining all phases:**

```
Input: Sentence A, Sentence B
            ↓
    Phase 1: TF-IDF score      → quick filter (unrelated = stop here)
            ↓
    Phase 2: WordNet matching  → synonym handling
            ↓
    Phase 3: Syntax tree       → active/passive normalization
            ↓
    Phase 4: Co-occurrence     → deep semantic score
            ↓
    Weighted average of all scores → final 0-1 score
```

---

## Phase 1 — TF-IDF + Cosine Similarity

**What TF-IDF actually is:**

```
TF  (Term Frequency)     = how often a word appears in THIS sentence
IDF (Inverse Doc Freq)   = how unique the word is ACROSS all sentences

TF-IDF = TF × IDF

Example:
"the" appears everywhere → low IDF → low TF-IDF (not important)
"feline" appears rarely  → high IDF → high TF-IDF (very important)
```

### Step 1: Text Preprocessing

```
Input:  "The Cat sat on the Mat!!"
            ↓
1a. Lowercase        → "the cat sat on the mat!!"
1b. Remove punctuation → "the cat sat on the mat"
1c. Tokenize         → ["the", "cat", "sat", "on", "the", "mat"]
1d. Remove stopwords → ["cat", "sat", "mat"]
1e. Stemming/Lemmatization → ["cat", "sit", "mat"]

Output: ["cat", "sit", "mat"]
```

### Step 2: Build Vocabulary

```
Sentence A tokens: ["cat", "sit", "mat"]
Sentence B tokens: ["feline", "rest", "rug"]

Combined Vocabulary: ["cat", "sit", "mat", "feline", "rest", "rug"]
```

### Step 3: Calculate TF (Term Frequency)

```
Formula: TF(word) = count of word in sentence / total words in sentence

Sentence A: ["cat", "sit", "mat"]
TF("cat")    = 1/3 = 0.33
TF("feline") = 0/3 = 0.00   ← word not in this sentence

Sentence A TF vector: [0.33, 0.33, 0.33, 0.00, 0.00, 0.00]
Sentence B TF vector: [0.00, 0.00, 0.00, 0.33, 0.33, 0.33]
```

### Step 4: Calculate IDF (Inverse Document Frequency)

```
Formula: IDF(word) = log(total sentences / sentences containing word)

Total sentences = 2
IDF("cat")    = log(2/1) = 0.69

Note: if a word appeared in BOTH sentences:
IDF = log(2/2) = log(1) = 0.00  ← common words get penalized
```

### Step 5: Calculate TF-IDF

```
Formula: TF-IDF(word) = TF(word) × IDF(word)

Sentence A TF-IDF vector:
"cat"    = 0.33 × 0.69 = 0.23
"feline" = 0.00 × 0.69 = 0.00
```

### Step 6: Cosine Similarity

```
Formula: similarity = (A · B) / (|A| × |B|)

A · B = dot product  = (0.23×0.00) + ... = 0.00
|A|   = magnitude    = √(0.23² + 0.23² + 0.23²) = 0.40

similarity = 0.00 / (0.40 × 0.40) = 0.00
```

**Phase 1's big limitation:** "cat" and "feline" score 0.0 because they share no words. Phase 2 addresses this with synonym knowledge.

---

## Phase 2 — WordNet + Wu-Palmer Similarity

**What WordNet is:**

```
WordNet is a free static English word database (not an AI model).
It organizes words into groups of synonyms called "synsets".

Example:
"car" → synset → ["car", "auto", "automobile", "machine", "motorcar"]

It also stores:
- Synonyms   → words with same meaning
- Hypernyms  → parent category  ("cat" → "feline" → "animal")
- Hyponyms   → child category   ("animal" → "feline" → "cat")
- Lemmas     → root word forms
```

**The Core Idea:**

```
Phase 1 (TF-IDF):
"I created a robot" vs "I built a robot"
tokens A: ["created", "robot"]
tokens B: ["built",   "robot"]
→ No shared words → score = 0.0

Phase 2 (WordNet):
"created" → synset → ["created", "built", "made", "constructed"]
"built"   → synset → ["built", "created", "constructed"]
→ MATCH FOUND → score boosted
```

### Step 1: Synset Lookup

```
Input: two tokens ("created", "built")
1a. Look up synsets for token A
    "created" → [Synset('create.v.01'), Synset('make.v.01')]
1b. Look up synsets for token B
    "built" → [Synset('construct.v.01'), Synset('make.v.01')]
1c. Synset('make.v.01') appears in BOTH → MATCH
```

### Step 2: Wu-Palmer Similarity

```
Not all synonym matches are equal:

"cat" vs "feline"  → very close in WordNet tree → score: 0.90
"cat" vs "animal"  → further apart              → score: 0.50
"cat" vs "object"  → very far apart             → score: 0.10

WordNet hierarchy example:
                    entity
                      │
                   object
                      │
                   animal
                    /    \
                feline   canine
                  │
                 cat
```

### Step 3: Token-to-Token Matching

```
tokens A: ["created", "robot"]
tokens B: ["built",   "robot"]

For each token in A, find best matching token in B:
"created" vs "built"  → Wu-Palmer → 0.89  ← best match
"robot"   vs "robot"  → Wu-Palmer → 1.00  ← exact match

Average best matches = (0.89 + 1.00) / 2 = 0.945
```

### Step 4: Combine Phase 1 + Phase 2 Scores

```
Final score = (0.4 × TF-IDF) + (0.6 × WordNet)

Higher weight on WordNet because it directly addresses the synonym weakness.
```

**Key limitation Phase 2 still won't fix:** antonyms like "increased" vs "reduced" may still score unexpectedly high. This is addressed in Phase 3 via syntax trees.

---

## Phase 3 — spaCy Dependency Parsing

**Install requirement:**

```bash
pip install spacy
python -m spacy download en_core_web_sm
```

**What spaCy does:**

```
spaCy is a parser — not a similarity model.
It reads a sentence and identifies the grammatical role of every word:

"The cat sat on the mat"
        ↓ spaCy
{
  "cat" → subject (nsubj)
  "sat" → root verb (ROOT)
  "mat" → object of preposition (pobj)
  "on"  → preposition (prep)
  "the" → determiner (det)
}
```

### Step 1: Parse into Dependency Tree

```
Token    | POS   | Dep Label | Head
─────────────────────────────────────
the      | DET   | det       | cat
cat      | NOUN  | nsubj     | sat
sat      | VERB  | ROOT      | sat
on       | ADP   | prep      | sat
mat      | NOUN  | pobj      | on

Key dependency labels:
nsubj  = subject
ROOT   = main verb
dobj   = direct object
pobj   = object of preposition
amod   = adjective modifier
```

### Step 2: Extract Key Roles

```python
def extract_roles(sentence):
    return {
        "subject":   word with dep="nsubj",
        "verb":      word with dep="ROOT",
        "object":    word with dep="dobj" or "pobj",
        "prep":      word with dep="prep",
        "modifiers": words with dep="amod" or "advmod"
    }
```

### Step 3: Active/Passive Normalization

```
Active:  "The dog bit the man"
         subject=dog, verb=bite, object=man

Passive: "The man was bitten by the dog"
         spaCy detects: nsubjpass=man, agent=dog, verb=bite

Normalization:
if passive detected:
    swap subject and agent
    → subject=dog, verb=bite, object=man

Result: IDENTICAL structure to active voice ✅
```

### Step 4: Role-by-Role Comparison

```
roles_A = {subject: "cat",    verb: "sit",  object: "mat",  prep: "on"}
roles_B = {subject: "feline", verb: "rest", object: "rug",  prep: "on"}

Role weights:
subject → 0.30
verb    → 0.30
object  → 0.25
prep    → 0.15

Weighted score:
= (0.963 × 0.30) + (0.25 × 0.30) + (0.875 × 0.25) + (1.0 × 0.15)
= 0.733
```

### Step 5: Combine All 3 Phases

```
Final = (0.20 × Phase1) + (0.30 × Phase2) + (0.50 × Phase3)

Phase 3 gets the highest weight because it uses both structure AND meaning,
and directly handles active/passive normalization.
```

---

## Phase 4 — Word Co-occurrence Matrix (Planned)

**Status: Not yet implemented.**

**Why this is different from Phases 1–3:**

```
Phases 1–3 use STATIC knowledge:
  Phase 1 → counts words in the input sentences only
  Phase 2 → WordNet — a fixed hand-curated dictionary
  Phase 3 → spaCy grammar rules — fixed parser

Phase 4 uses LEARNED knowledge:
  Reads millions of real sentences
  Discovers statistical patterns of word co-occurrence
  "cat" and "feline" become close because they share context
  No human had to write a rule — it emerged from data
```

### Step 1: Build Co-occurrence Matrix

```
Window size = 2 (look 2 words left/right of each target word)

With a tiny corpus, "cat" and "feline" look different.
With millions of Wikipedia sentences they converge because both appear near
"purr", "meow", "whiskers", "fur", "breed", "domesticated", etc.
```

### Step 2: Reduce Dimensionality (SVD)

```
Raw matrix: 50,000 words × 50,000 words
      ↓ SVD
Dense matrix: 50,000 words × 300 dimensions

Each row is a 300-dimensional "meaning vector" for one word.
```

### Step 3: Sentence Vectors + Cosine Similarity

```
Sentence → word vectors → average → sentence vector → cosine similarity
```

### Proposed Integration Weights

```
with Phase 4 added:
  phase_1: 0.10   (TF-IDF)
  phase_2: 0.20   (WordNet)
  phase_3: 0.35   (spaCy syntax)
  phase_4: 0.35   (co-occurrence vectors)

File would live at:
  similarity_prototype/Phase_4/cooccurrence.py
  similarity_prototype/Phase_4/vectorizer.py
```

**Why it hasn't been built yet:** The production system (LaBSE) already provides deep semantic vectors trained on hundreds of millions of multilingual sentences. Phase 4 would only be useful inside the prototype pipeline (English-only, intentionally avoids pretrained models).

---

## Prototype Pipeline — Implementation Reference

**Status: Implemented and integrated into the production API**

The prototype is the Phase 1+2+3 pipeline. It lives at:

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

### How the Phases Combine

```
score = (0.20 × TF-IDF cosine)
      + (0.30 × WordNet best-token-match)
      + (0.50 × spaCy role comparison)
```

### Top-K Pre-filter Optimization

Running Phase 2+3 on every sentence pair in an N×M matrix is expensive. The pipeline avoids O(N×M) work using a two-stage strategy:

```
Step 1 — Phase 1 pre-filter (fast):
  Compute TF-IDF cosine for ALL N×M pairs using numpy matrix multiply.
  For each sentence in A, keep only the top-K candidates from B.
  Default: top_k = 8

Step 2 — Full pipeline (expensive, candidates only):
  Run Phase 2+3 only on the top-K candidates per sentence.

Result: Phase 2+3 work drops from O(N×M) → O(N×K)
```

### Persistent Worker Pool

Phase 2 (WordNet) and Phase 3 (spaCy) have high startup costs. The pipeline uses a **module-level persistent pool**:

```
First comparison request:
  → Pool created with cpu_count() workers
  → Each worker loads WordNet + spaCy model
  → Cost paid once

All subsequent requests:
  → Existing workers reused (no startup cost)
```

Workers are initialized via `_init_worker_persistent()` and store state in `_worker_state`. For very small inputs (≤ 60 scored pairs), the pipeline falls back to sequential execution.

### Sentence Cleaning and Filtering

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

### Minimum Match Threshold

```
ArticleComparator.MIN_MATCH_THRESHOLD = 0.20

Pairs scoring below 0.20 are treated as no match.
The effective threshold is max(MIN_MATCH_THRESHOLD, similarity_threshold).
```

---

## Production Implementation — Section Comparison Pipeline

**Status: Live**
**Source:** `symmetry-unified-backend/app/services/section_comparison.py`

The production comparison system matches Wikipedia articles section-by-section and paragraph-by-paragraph using **LaBSE** (multilingual sentence transformer) with Levenshtein distance as a disambiguation tiebreaker.

### Two Comparison Modes

| `model_name` | Description |
|-------------|-------------|
| `sentence-transformers/LaBSE` (default) | Full multilingual embedding pipeline. Works on any language pair, no translation required. |
| `similarity_prototype` | Phase 1+2+3 custom NLP pipeline. Sections matched with LaBSE; paragraphs translated to English then scored by prototype. |

### Step 1 — Section Matching

```
For each section, build a representation:
  text = section.title + ". " + section.clean_content[:200]

Encode all source and target section texts with the transformer.
Build a cosine similarity matrix.

Greedy assignment:
  Sort all (i, j) pairs by similarity descending.
  Pick the best pair where neither i nor j has been used.
  Accept only if score ≥ similarity_threshold.

Result:
  matched_pairs    → list of (source_idx, target_idx, score)
  unmatched_source → sections missing in target
  unmatched_target → sections added in target
```

### Step 2 — Paragraph Splitting

```
Primary: split on double-newline (\n\n) — preserves HTML <p> boundaries

Fallback (for long single-paragraph sections > 300 chars):
  Split on sentence boundaries (period/!/?  followed by whitespace)
  Group sentences into ~150-word chunks
```

### Step 3 — Paragraph Matching

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

### Step 4 — Result Assembly

```python
SectionCompareResponse:
  source_title, target_title
  source_lang, target_lang
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

### Levenshtein Disambiguation

```
When it fires:
  top_score - second_score < 0.08

Formula:
  normalized_levenshtein = 1 - (edit_distance / max(len(A), len(B)))
  → 0.0 = completely different strings
  → 1.0 = identical strings
```

### Model Caching

Models are loaded on demand and kept in a module-level `_model_cache` dict. The first request for a given model name pays the load cost (~5–15 s for LaBSE). Subsequent requests reuse the cached model.

---

## Similarity Threshold Settings

**Source:** `symmetry-unified-backend/app/core/settings.py`

All thresholds are read from environment variables with defaults. Nothing is hardcoded in individual modules.

### Override via .env

```env
SIMILARITY_THRESHOLD=0.60
LEVENSHTEIN_DISAMBIGUATION_MARGIN=0.10
FAMILY_THRESHOLD_SAME=0.45
```

### Cosine Similarity Threshold

```
SIMILARITY_THRESHOLD = 0.65   (default)

Used by:
  section_comparison.py  — gates section AND paragraph matches
  semantic_comparison.py — filters sentences below threshold

Per-request override:
  POST /symmetry/v1/articles/compare-sections
  body: { "similarity_threshold": 0.5 }
```

### Levenshtein Disambiguation Margin

```
LEVENSHTEIN_DISAMBIGUATION_MARGIN = 0.08   (default)

Fires when: top_cosine_score - second_cosine_score < 0.08
Effect: Levenshtein distance becomes the tiebreaker for top-2 paragraph candidates.
```

### Language-Family Match Thresholds

Used by `similarity_scoring.py` for lexical word-match scoring (not transformer cosine similarity):

```
FAMILY_THRESHOLD_SAME        = 0.50   same family (e.g. Spanish ↔ Italian)
FAMILY_THRESHOLD_IE_BRANCHES = 0.60   different IE branches (e.g. English ↔ Spanish)
FAMILY_THRESHOLD_UNRELATED   = 0.70   different families (e.g. English ↔ Japanese)
FAMILY_THRESHOLD_UNKNOWN     = 0.70   one or both languages unrecognized
```

**Why lower thresholds for related languages?** Related languages share cognates with similar spellings. A Levenshtein score of 0.50 is meaningful between Spanish and Italian ("noche" / "notte") but would be noise between English and Arabic.

### Language Families Recognized

| Family | Languages |
|--------|-----------|
| GERMANIC | English, German, Dutch, Swedish, Norwegian, Danish, Icelandic |
| ROMANCE | Spanish, French, Italian, Portuguese, Romanian, Catalan |
| SLAVIC | Russian, Ukrainian, Polish, Czech, Slovak, Bulgarian, Serbian, Croatian, Slovene, Belarusian, Macedonian |
| SINO_TIBETAN | Mandarin, Cantonese, Chinese, Tibetan |
| AFRO_ASIATIC | Arabic, Hebrew, Amharic |
| ALTAIC | Turkish, Mongolian, Korean |
| DRAVIDIAN | Tamil, Telugu, Kannada, Malayalam |
| UNKNOWN | Any language not in the map above |

### Band Thresholds

Band thresholds classify a lexical similarity score into a qualitative category. Each family relationship gets its own 4-level tuple: `(very_close, same_branch_high, same_family_low, unrelated_low)`.

```
BAND_SAME_FAMILY        = (0.75, 0.55, 0.30, 0.15)
BAND_IE_BRANCHES        = (0.80, 0.60, 0.35, 0.20)
BAND_DIFFERENT_FAMILIES = (0.85, 0.65, 0.40, 0.25)
BAND_UNKNOWN            = (0.85, 0.60, 0.25, 0.10)
```

Classification logic in `classify_band()`:

```
score ≥ very_close      → "very_close"
score ≥ same_branch     → "same_branch"
score ≥ same_family_low → "same_family_distant"
score ≥ unrelated_low   → "unrelated"
score < unrelated_low   → "completely_unrelated"
```

### Prototype Minimum Match Threshold

This is **not** in `settings.py` — it is hardcoded in `ArticleComparator`:

```python
# article_comparator.py
self.MIN_MATCH_THRESHOLD = 0.20
```

The effective match threshold is `max(MIN_MATCH_THRESHOLD, similarity_threshold)`.
