
**Status: Planned — not yet implemented**

---

**Phase 4: Build Your Own Vector Space**
Word Co-occurrence Matrix (poor man's Word2Vec)

```
How it works:
1. Take a large corpus of text (e.g. Wikipedia dump)
2. Count how often words appear near each other
3. Words with similar contexts get similar vectors:
   "cat" and "feline" both appear near "meow", "fur", "pet"
   so they end up with similar vectors
4. Average word vectors to get sentence vectors
5. Cosine similarity for final score

Pros: Learns meaning from context, no pretrained model needed
Cons: Need a large corpus, takes time to build
```

---

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

---

**Step 1: Build the co-occurrence matrix**

```
Corpus (simplified):
  "The cat sat on the mat"
  "A feline rested on a rug"
  "The cat meowed loudly"

Window size = 2 (look 2 words left/right of each target word)

Co-occurrence counts for "cat":
  cat ←→ the   : 2
  cat ←→ sat   : 1
  cat ←→ feline: 0   ← they never appear in the same window
  cat ←→ meowed: 1

Co-occurrence counts for "feline":
  feline ←→ a    : 1
  feline ←→ rested: 1

Note: with a tiny corpus like this, "cat" and "feline" still look different.
With millions of Wikipedia sentences they converge because both appear near
"purr", "meow", "whiskers", "fur", "breed", "domesticated", etc.
```

---

**Step 2: Reduce dimensionality (SVD)**

```
The raw co-occurrence matrix is huge (vocabulary × vocabulary).
We compress it with Singular Value Decomposition (SVD):

Raw matrix: 50,000 words × 50,000 words
      ↓ SVD
Dense matrix: 50,000 words × 300 dimensions

Each row is now a 300-dimensional "meaning vector" for one word.
Words that appear in similar contexts have similar vectors.
```

---

**Step 3: Sentence vectors + cosine similarity**

```
Sentence → word vectors → average → sentence vector

"The cat sat on the mat"
  → vectors for [cat, sat, mat] (stopwords removed)
  → average those 3 vectors
  → one 300-dim sentence vector

Same for second sentence, then cosine similarity.
```

---

**Integration with current pipeline:**

```
Phase 4 would slot in as an additional scorer in ArticleComparator:

current weights (Phases 1–3):
  phase_1: 0.20   (TF-IDF)
  phase_2: 0.30   (WordNet)
  phase_3: 0.50   (spaCy syntax)

with Phase 4 added (proposed):
  phase_1: 0.10   (TF-IDF)
  phase_2: 0.20   (WordNet)
  phase_3: 0.35   (spaCy syntax)
  phase_4: 0.35   (co-occurrence vectors)

File would live at:
  similarity_prototype/Phase_4/cooccurrence.py
  similarity_prototype/Phase_4/vectorizer.py
```

---

**Why it hasn't been built yet:**

```
The production system (LaBSE) already provides deep semantic vectors
trained on hundreds of millions of multilingual sentences.
Phase 4 would only be useful inside the prototype pipeline,
which is English-only and intentionally avoids pretrained models.

Phase 4 becomes valuable if:
  - You want to eliminate the WordNet dependency entirely
  - You want the prototype to handle domain-specific vocabulary
    (e.g. medical, legal) not well-covered by WordNet
  - You have a domain-specific Wikipedia corpus to train on
```

See [[Road map outline]] for the full four-phase pipeline diagram.
