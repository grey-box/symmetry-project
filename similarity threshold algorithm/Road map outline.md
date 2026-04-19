
> **Implementation status**
> Phases 1–3 are **implemented** in `similarity_prototype/` and integrated into
> the production API via `model_name = "similarity_prototype"`.
> Phase 4 is **planned but not yet implemented**.
> The primary production pipeline uses LaBSE sentence transformers — see
> [[Production Implementation]] for details.

---

**Phase 1: Word Overlap (Simplest)**
[[Phase 1 outline]]
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

---
**Phase 2: Add Synonym Knowledge**
[[Phase 2 outline]]
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

---
**Phase 3: Handle Sentence Structure**
[[Phase 3 outline]]
Syntactic Tree Matching

```
How it works:
1. Parse both sentences into a syntax tree (subject, verb, object)
2. Compare the trees structurally
3. Active/passive becomes same structure after parsing:

"The dog bit the man"     → subject=dog,  verb=bite, object=man
"The man was bitten by the dog" → subject=dog, verb=bite, object=man
                                    ↑ same after normalization!

Pros: Solves your active/passive problem directly
Cons: More complex to implement
Library needed: spaCy (just a parser, not a trained similarity model)
```

---
**Phase 4: Build Your Own Vector Space** *(planned)*
[[Phase 4 outline]]
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

Pros: Learns meaning from context, no pretrained model
Cons: Need a large corpus, takes time to build
```

---
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
**AI recommendations**
- Use **spaCy** (just a parser, not a similarity model) for syntax tree parsing to solve active/passive voice
- Build **TF-IDF + WordNet** from scratch for semantic scoring
- Combine both into your pipeline

---

**See also:**
- [[Prototype Pipeline]] — how the phases are wired together in code
- [[Production Implementation]] — the LaBSE-based production system
- [[Similarity Threshold Settings]] — all configurable thresholds
- [[Index]] — full documentation hub