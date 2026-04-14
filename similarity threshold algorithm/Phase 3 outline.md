**Install requirement:**

```
pip install spacy
python -m spacy download en_core_web_sm
```

**What spaCy does:**

```
spaCy is a parser — not a similarity model
It reads a sentence and identifies the grammatical
role of every word:

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

---

**Why this solves our remaining problems:**

```
"The cat sat on the mat"
"A feline rested on a rug"

spaCy parse:
Sentence A: subject=cat,    verb=sit,  prep=on, object=mat
Sentence B: subject=feline, verb=rest, prep=on, object=rug

Structural comparison:
subject role: cat    vs feline → Phase 2 score = 0.963 ✅
verb role:    sit    vs rest   → same role → compare meaning
object role:  mat    vs rug    → same role → compare meaning
prep role:    on     vs on     → exact match ✅

Key insight:
"sat" and "rested" failed in Phase 2 because Wu-Palmer
scored them low (0.25) with no shared synset.
But in Phase 3 we know BOTH are the main verb of the sentence
so we compare them directly as verbs and give credit
for filling the same structural role
```

---
**Step 1: Parse sentence into dependency tree**

```
Input: "The cat sat on the mat"
           ↓ spaCy
Output:
Token    | POS   | Dep Label | Head
─────────────────────────────────────
the      | DET   | det       | cat
cat      | NOUN  | nsubj     | sat
sat      | VERB  | ROOT      | sat
on       | ADP   | prep      | sat
the      | DET   | det       | mat
mat      | NOUN  | pobj      | on

Key dependency labels:
nsubj  = subject
ROOT   = main verb
dobj   = direct object
pobj   = object of preposition
prep   = preposition
amod   = adjective modifier
advmod = adverb modifier
```


---

**Step 2: Extract key roles**

```
From the full parse, extract only the important roles:

def extract_roles(sentence):
    return {
        "subject":  word with dep="nsubj",
        "verb":     word with dep="ROOT",
        "object":   word with dep="dobj" or "pobj",
        "prep":     word with dep="prep",
        "modifiers": words with dep="amod" or "advmod"
    }

Example:
"The cat sat on the mat"
→ {
    "subject":  "cat",
    "verb":     "sit",    ← lemmatized
    "object":   "mat",
    "prep":     "on",
    "modifiers": []
  }

"A feline rested on a rug"
→ {
    "subject":  "feline",
    "verb":     "rest",   ← lemmatized
    "object":   "rug",
    "prep":     "on",
    "modifiers": []
  }
```


---

**Step 3: Active/Passive normalization**

```
This is where Phase 3 solves active/passive directly:

Active:  "The dog bit the man"
         subject=dog, verb=bite, object=man

Passive: "The man was bitten by the dog"
         spaCy detects: nsubjpass=man, agent=dog, verb=bite

Normalization:
if passive detected:
    swap subject and agent
    → subject=dog, verb=bite, object=man

Result: IDENTICAL structure to active voice ✅
Both sentences now parse to same roles
→ perfect structural match
```

---

**Step 4: Role-by-role comparison**

```
Compare each role pair using Phase 2 (WordNet) scores:

roles_A = {subject: "cat",    verb: "sit",  object: "mat",  prep: "on"}
roles_B = {subject: "feline", verb: "rest", object: "rug",  prep: "on"}

Role scores:
subject: compare("cat",    "feline") → Phase2 = 0.963
verb:    compare("sit",    "rest")   → Phase2 = 0.25 (low but same role)
object:  compare("mat",    "rug")    → Phase2 = 0.875
prep:    compare("on",     "on")     → exact = 1.0

Role weights (some roles matter more than others):
subject → weight 0.30
verb    → weight 0.30
object  → weight 0.25
prep    → weight 0.15

Weighted score:
= (0.963 × 0.30) + (0.25 × 0.30) + (0.875 × 0.25) + (1.0 × 0.15)
= 0.289  + 0.075  + 0.219  + 0.15
= 0.733
```

---

**Step 5: Combine all 3 phases**

```
Final score = weighted average of all phases:

Phase 1 (TF-IDF):    0.XX  → weight 0.20
Phase 2 (WordNet):   0.XX  → weight 0.30
Phase 3 (Syntax):    0.XX  → weight 0.50  ← highest weight

Why highest weight on Phase 3?
→ It uses both structure AND meaning
→ It handles active/passive directly
→ It's the most linguistically informed

Final = (0.20 × P1) + (0.30 × P2) + (0.50 × P3)
```

