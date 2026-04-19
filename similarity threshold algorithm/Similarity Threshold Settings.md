
# Similarity Threshold Settings

**Source:** `symmetry-unified-backend/app/core/settings.py`

All thresholds are read from the environment (or `.env` file) with defaults.
Services import from `app.core.settings` — nothing is hardcoded in individual
modules.

---

## Override via .env

Create or edit `symmetry-unified-backend/.env`:

```
SIMILARITY_THRESHOLD=0.60
LEVENSHTEIN_DISAMBIGUATION_MARGIN=0.10
FAMILY_THRESHOLD_SAME=0.45
```

Any omitted key falls back to the default shown below.

---

## Cosine similarity threshold

```
SIMILARITY_THRESHOLD = 0.65   (default)

Used by:
  section_comparison.py  — gates section matches AND paragraph matches
  semantic_comparison.py — filters sentences below threshold

Per-request override:
  POST /symmetry/v1/articles/compare-sections
  body: { "similarity_threshold": 0.5 }
```

Lowering this value finds more matches but increases false positives.
Raising it requires stronger semantic similarity — useful for detecting
near-identical translations vs loosely related content.

---

## Levenshtein disambiguation margin

```
LEVENSHTEIN_DISAMBIGUATION_MARGIN = 0.08   (default)

Used by:
  section_comparison.py  _compare_paragraphs()

Fires when:
  top_cosine_score - second_cosine_score < 0.08

Effect:
  Levenshtein distance becomes the tiebreaker between the
  top-2 paragraph candidates.
```

Increase this margin to make Levenshtein disambiguation trigger more
aggressively. Decrease it (towards 0) to disable tiebreaking and always
trust the cosine score.

See [[Production Implementation]] for how this fits into the paragraph
matching algorithm.

---

## Language-family match thresholds

These thresholds are used by `similarity_scoring.py` for **lexical** word-match
scoring (not the transformer cosine similarity). They select the minimum score
required for a word pair to be considered a match, adjusted for how closely
related the two languages are.

```
FAMILY_THRESHOLD_SAME       = 0.50   same language family (e.g. Spanish ↔ Italian)
FAMILY_THRESHOLD_IE_BRANCHES = 0.60  different IE branches (e.g. English ↔ Spanish)
FAMILY_THRESHOLD_UNRELATED  = 0.70   different families (e.g. English ↔ Japanese)
FAMILY_THRESHOLD_UNKNOWN    = 0.70   one or both languages unrecognized
```

**Why lower thresholds for related languages?**
Related languages share cognates and loanwords that have similar spellings.
A Levenshtein score of 0.50 is meaningful between Spanish and Italian
("noche" / "notte") but would be noise between English and Arabic.

---

## Language families recognized

`similarity_scoring.py` maps language names to families for threshold selection:

```
GERMANIC      English, German, Dutch, Swedish, Norwegian, Danish, Icelandic
ROMANCE       Spanish, French, Italian, Portuguese, Romanian, Catalan
SLAVIC        Russian, Ukrainian, Polish, Czech, Slovak, Bulgarian,
              Serbian, Croatian, Slovene, Belarusian, Macedonian
SINO_TIBETAN  Mandarin, Cantonese, Chinese, Tibetan
AFRO_ASIATIC  Arabic, Hebrew, Amharic
ALTAIC        Turkish, Mongolian, Korean
DRAVIDIAN     Tamil, Telugu, Kannada, Malayalam
UNKNOWN       Any language not in the map above
```

Two languages in the same enum value (e.g. both GERMANIC) use
`FAMILY_THRESHOLD_SAME`. Two Indo-European languages in different branches
(e.g. GERMANIC + ROMANCE) use `FAMILY_THRESHOLD_IE_BRANCHES`.

---

## Band thresholds

Band thresholds classify a lexical similarity score into a qualitative category.
Each family relationship gets its own 4-level tuple:
`(very_close, same_branch_high, same_family_low, unrelated_low)`

```
BAND_SAME_FAMILY       = (0.75, 0.55, 0.30, 0.15)
BAND_IE_BRANCHES       = (0.80, 0.60, 0.35, 0.20)
BAND_DIFFERENT_FAMILIES = (0.85, 0.65, 0.40, 0.25)
BAND_UNKNOWN           = (0.85, 0.60, 0.25, 0.10)
```

Classification logic in `classify_band()`:

```
score ≥ very_close      → "very_close"
score ≥ same_branch     → "same_branch"
score ≥ same_family_low → "same_family_distant"
score ≥ unrelated_low   → "unrelated"
score < unrelated_low   → "completely_unrelated"
```

---

## Prototype minimum match threshold

This is **not** in `settings.py` — it is hardcoded in `ArticleComparator`:

```python
# article_comparator.py
self.MIN_MATCH_THRESHOLD = 0.20
```

Pairs scoring below 0.20 in the Phase 1+2+3 prototype are treated as no match.
This intentionally low floor allows the prototype to catch related sentences
that use completely different vocabulary.

The caller's `similarity_threshold` from the API also applies to prototype
mode — the effective gate is whichever is higher.

See [[Prototype Pipeline]] for full details.
