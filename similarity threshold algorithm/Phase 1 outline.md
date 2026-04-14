
**What TF-IDF actually is:**

```
TF  (Term Frequency)     = how often a word appears in THIS sentence
IDF (Inverse Doc Freq)   = how unique the word is ACROSS all sentences

TF-IDF = TF × IDF

Example:
"the" appears everywhere → low IDF → low TF-IDF (not important)
"feline" appears rarely  → high IDF → high TF-IDF (very important)
```

1. 1. The tf–idf is the product of two statistics, _term frequency_ and _inverse document frequency_. There are various ways for determining the exact values of both statistics.
2.  A formula that aims to define the importance of a keyword or phrase within a document or a web page.
![[Pasted image 20260310153506.png]]
![[Pasted image 20260310153619.png]]
![[Pasted image 20260310153845.png]]
![[Pasted image 20260310154220.png]]

---
**Step 1: Text Preprocessing**

```
Input:  "The Cat sat on the Mat!!"
            ↓
1a. Lowercase        → "the cat sat on the mat!!"
1b. Remove punctuation → "the cat sat on the mat"
1c. Tokenize         → ["the", "cat", "sat", "on", "the", "mat"]
1d. Remove stopwords → ["cat", "sat", "mat"]
        (stopwords = "the", "on", "is", "a" etc - common words with no meaning)
1e. Stemming/Lemmatization → ["cat", "sit", "mat"]
        (reduces words to root: "running" → "run", "sat" → "sit")

Output: ["cat", "sit", "mat"]
```

---
**Step 2: Build Vocabulary**

```
Sentence A tokens: ["cat", "sit", "mat"]
Sentence B tokens: ["feline", "rest", "rug"]

Combined Vocabulary: ["cat", "sit", "mat", "feline", "rest", "rug"]
         (every unique word across both sentences)
```

---
**Step 3: Calculate TF (Term Frequency)**

```
Formula: TF(word) = count of word in sentence / total words in sentence

Sentence A: ["cat", "sit", "mat"]
TF("cat")    = 1/3 = 0.33
TF("sit")    = 1/3 = 0.33
TF("mat")    = 1/3 = 0.33
TF("feline") = 0/3 = 0.00   ← word not in this sentence
TF("rest")   = 0/3 = 0.00
TF("rug")    = 0/3 = 0.00

Sentence A TF vector: [0.33, 0.33, 0.33, 0.00, 0.00, 0.00]
Sentence B TF vector: [0.00, 0.00, 0.00, 0.33, 0.33, 0.33]
```

---
**Step 4: Calculate IDF (Inverse Document Frequency)**

```
Formula: IDF(word) = log(total sentences / sentences containing word)

Total sentences = 2

IDF("cat")    = log(2/1) = 0.69  ← appears in 1 sentence
IDF("sit")    = log(2/1) = 0.69
IDF("mat")    = log(2/1) = 0.69
IDF("feline") = log(2/1) = 0.69  ← appears in 1 sentence
IDF("rest")   = log(2/1) = 0.69
IDF("rug")    = log(2/1) = 0.69

Note: if a word appeared in BOTH sentences:
IDF = log(2/2) = log(1) = 0.00  ← common words get penalized
```

---
**Step 5: Calculate TF-IDF**

```
Formula: TF-IDF(word) = TF(word) × IDF(word)

Sentence A TF-IDF vector:
"cat"    = 0.33 × 0.69 = 0.23
"sit"    = 0.33 × 0.69 = 0.23
"mat"    = 0.33 × 0.69 = 0.23
"feline" = 0.00 × 0.69 = 0.00
"rest"   = 0.00 × 0.69 = 0.00
"rug"    = 0.00 × 0.69 = 0.00

Vector A: [0.23, 0.23, 0.23, 0.00, 0.00, 0.00]
Vector B: [0.00, 0.00, 0.00, 0.23, 0.23, 0.23]
```

---
**Step 6: Cosine Similarity**

```
Formula: similarity = (A · B) / (|A| × |B|)

A · B = dot product  = (0.23×0.00) + (0.23×0.00) + ... = 0.00
|A|   = magnitude    = √(0.23² + 0.23² + 0.23²) = 0.40
|B|   = magnitude    = √(0.23² + 0.23² + 0.23²) = 0.40

similarity = 0.00 / (0.40 × 0.40) = 0.00
```

---
**This exposes Phase 1's big limitation:**

```
"cat/sit/mat" vs "feline/rest/rug"
No shared words → score = 0.00
Even though they mean the same thing!

This is exactly why Phase 2 (WordNet synonyms) is needed
```

