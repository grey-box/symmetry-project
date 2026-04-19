
**What WordNet is:**

```
WordNet is a free static English word database (not an AI model)
It organizes words into groups of synonyms called "synsets"

Example:
"car" → synset → ["car", "auto", "automobile", "machine", "motorcar"]
"dog" → synset → ["dog", "domestic dog", "Canis familiaris"]

It also stores:
- Synonyms   → words with same meaning
- Hypernyms  → parent category  ("cat" → "feline" → "animal")
- Hyponyms   → child category   ("animal" → "feline" → "cat")
- Lemmas     → root word forms  ("written", "wrote", "writing" → "write")
```

---

**The Core Idea:**

```
Phase 1 (TF-IDF):
"I created a robot" vs "I built a robot"
     ↓
tokens A: ["created", "robot"]
tokens B: ["built",   "robot"]
     ↓
No shared words → score contribution from verbs = 0.0

Phase 2 (WordNet on top of TF-IDF):
"created" → WordNet → synset → ["created", "built", "made", "constructed"]
"built"   → WordNet → synset → ["built", "created", "constructed"]
     ↓
"created" and "built" are in the same synset → MATCH FOUND
     ↓
Score gets boosted → higher final score
```

--- 

**Step 1: Synset Lookup**

```
Input: two tokens  ("created", "built")
          ↓
1a. Look up synsets for token A
    "created" → [Synset('create.v.01'), Synset('make.v.01')]

1b. Look up synsets for token B
    "built" → [Synset('construct.v.01'), Synset('make.v.01')]

1c. Check for overlap
    Synset('make.v.01') appears in BOTH → MATCH
          ↓
Output: similarity score between 0-1
```

---

**Step 2: Wu-Palmer Similarity**

```
Not all synonym matches are equal:

"cat" vs "feline"  → very close in WordNet tree → score: 0.90
"cat" vs "animal"  → further apart              → score: 0.50
"cat" vs "object"  → very far apart             → score: 0.10

Wu-Palmer measures the DISTANCE between two words
in the WordNet hierarchy tree:

                    entity
                      │
                   object
                      │
                   animal
                    /    \
                feline   canine
                  │
                 cat

"cat" vs "feline" → 1 step apart  → high score
"cat" vs "canine" → 3 steps apart → lower score
"cat" vs "object" → 5 steps apart → low score
```

---

**Step 3: Token-to-Token Matching**

```
Input: 
tokens A: ["created", "robot"]
tokens B: ["built",   "robot"]
          ↓
For each token in A, find best matching token in B:

"created" vs "built"  → Wu-Palmer → 0.89  ← best match
"created" vs "robot"  → Wu-Palmer → 0.11
"robot"   vs "built"  → Wu-Palmer → 0.10
"robot"   vs "robot"  → Wu-Palmer → 1.00  ← best match (exact)
          ↓
Best matches: 
  "created" → "built" = 0.89
  "robot"   → "robot" = 1.00
          ↓
Average best matches = (0.89 + 1.00) / 2 = 0.945
```


---

**Step 4: Combine Phase 1 + Phase 2 Scores**

```
Final score = (Phase1_weight × TF-IDF score) 
            + (Phase2_weight × WordNet score)

Example weights to start with:
Final score = (0.4 × TF-IDF) + (0.6 × WordNet)

Why higher weight on WordNet?
→ WordNet directly addresses our biggest weakness (synonyms)
→ Weights can be tuned later based on results
```

---

**Key limitation Phase 2 still won't fix:**

```
"The company increased revenue"
"The company reduced revenue"

"increased" and "reduced" ARE antonyms in WordNet
BUT Wu-Palmer measures conceptual distance, not opposition
So they may still score higher than expected

This is a Phase 3 problem (syntax trees) where we
detect negation and antonym relationships directly
```

