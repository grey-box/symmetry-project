
# Similarity Threshold Algorithm — Documentation Hub

This vault documents Project Symmetry's similarity scoring system: from the
research prototype (Phases 1–3) to the production section comparison pipeline.

---

## Prototype Pipeline (Research)

The prototype is a custom NLP pipeline built without pretrained sentence embeddings.
It runs inside `symmetry-unified-backend/app/services/similarity_prototype/`.

| Page | What it covers |
|------|----------------|
| [[Road map outline]] | Four-phase design overview and combined pipeline |
| [[Phase 1 outline]] | TF-IDF + Cosine Similarity (word overlap) |
| [[Phase 2 outline]] | WordNet + Wu-Palmer Similarity (synonym knowledge) |
| [[Phase 3 outline]] | spaCy Dependency Parsing (syntax / active-passive) |
| [[Phase 4 outline]] | Word Co-occurrence Matrix (planned, not yet implemented) |
| [[Prototype Pipeline]] | How Phases 1–3 are wired together in `ArticleComparator` |

---

## Production System

The live comparison feature uses multilingual sentence transformers (LaBSE)
for section and paragraph matching.

| Page | What it covers |
|------|----------------|
| [[Production Implementation]] | LaBSE-based section & paragraph comparison |
| [[Similarity Threshold Settings]] | All configurable thresholds (`core/settings.py`) |

---

## Quick reference — threshold defaults

| Setting | Default | Where used |
|---------|---------|-----------|
| `SIMILARITY_THRESHOLD` | `0.65` | Section + paragraph matching |
| `LEVENSHTEIN_DISAMBIGUATION_MARGIN` | `0.08` | Paragraph tiebreaker |
| `FAMILY_THRESHOLD_SAME` | `0.50` | Same language family |
| `FAMILY_THRESHOLD_IE_BRANCHES` | `0.60` | Different IE branches |
| `FAMILY_THRESHOLD_UNRELATED` | `0.70` | Unrelated families |
| Prototype `MIN_MATCH_THRESHOLD` | `0.20` | Prototype paragraph match |
