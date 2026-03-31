import nltk
from nltk.corpus import wordnet
from nltk.stem import WordNetLemmatizer
from Phase_1.preprocessor import Preprocessor

# Only download NLTK data if it isn't already present locally.
def _ensure_nltk_data():
    _packages = {
        'wordnet':                        'corpora/wordnet',
        'averaged_perceptron_tagger':     'taggers/averaged_perceptron_tagger',
        'averaged_perceptron_tagger_eng': 'taggers/averaged_perceptron_tagger_eng',
    }
    for pkg, path in _packages.items():
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(pkg, quiet=True)

_ensure_nltk_data()

class SynonymMatcher:
    def __init__(self):
        self.preprocessor = Preprocessor()
        self.lemmatizer = WordNetLemmatizer()
      
        # Per-instance caches for expensive WordNet / NLTK lookups.
        # Keyed on word strings (or sorted word-pairs for symmetric functions)
        # so that the same inputs never trigger a second lookup within a run.
        self._pos_cache            = {}
        self._lemma_cache          = {}
        self._wup_cache            = {}
        self._share_synset_cache   = {}
        self._antonym_cache        = {}
        self._direct_antonym_cache = {}

        self.IRREGULAR_VERBS = {
    "sat": "sit",
    "went": "go",
    "ran": "run",
    "ate": "eat",
    "saw": "see",
    "took": "take",
    "came": "come",
    "said": "say",
    "got": "get",
    "made": "make",
    "knew": "know",
    "thought": "think",
    "told": "tell",
    "became": "become",
    "showed": "show",
    "felt": "feel",
    "left": "leave",
    "kept": "keep",
    "brought": "bring",
    "began": "begin",
    "grown": "grow",
    "drawn": "draw",
    "worn": "wear",
    "chosen": "choose",
    "spoken": "speak",
    "stolen": "steal",
    "broken": "break",
    "forgotten": "forget",
    "hidden": "hide",
    "risen": "rise",
    "fallen": "fall",
    "driven": "drive",
    "ridden": "ride",
    "rung": "ring",
    "sung": "sing",
    "sunk": "sink",
    "swum": "swim",
    "thrown": "throw",
    "blown": "blow",
    "grown": "grow",
    "known": "know",
    "shown": "show",
    "flown": "fly",
    "drew": "draw",
    "drove": "drive",
    "rode": "ride",
    "rose": "rise",
    "fell": "fall",
    "rang": "ring",
    "sang": "sing",
    "sank": "sink",
    "swam": "swim",
    "threw": "throw",
    "blew": "blow",
    "grew": "grow",
    "flew": "fly",
    "wore": "wear",
    "spoke": "speak",
    "broke": "break",
    "chose": "choose",
    "stole": "steal",
    "forgot": "forget",
    "hid": "hide",
}

    #Step 1: get POS tag (noun,verb,adjective,adverb)
    #Wordnet needs POS tag to look up the right synset
    def get_pos_tag(self, word):
        if word in self._pos_cache:
            return self._pos_cache[word]

        tag = nltk.pos_tag([word])[0][1]

        #Convert nltk POS tags to wordnet POS tags
        if tag.startswith('J'):
            result = wordnet.ADJ
        elif tag.startswith('V'):
            result = wordnet.VERB
        elif tag.startswith('R'):
            result = wordnet.ADV
        else:
            result = wordnet.NOUN

        self._pos_cache[word] = result
        return result
        
    #lemmatize before WordNet lookup
    def lemmatize(self, word):
        key = word.lower()
        if key in self._lemma_cache:
            return self._lemma_cache[key]

        # Check irregular verbs first
        if key in self.IRREGULAR_VERBS:
            result = self.IRREGULAR_VERBS[key]
            self._lemma_cache[key] = result
            return result

        pos = self.get_pos_tag(word)
        lemmatized = self.lemmatizer.lemmatize(word, pos=pos)

        # If unchanged try forcing VERB pos
        if lemmatized == word:
            verb_lemma = self.lemmatizer.lemmatize(word, pos=wordnet.VERB)
            if verb_lemma != word:
                lemmatized = verb_lemma

        self._lemma_cache[key] = lemmatized
        return lemmatized

    #Step 2: Get all sysnets for a word
    def get_synsets(self, word):
        lemmatized_word = self.lemmatize(word)
        pos = self.get_pos_tag(lemmatized_word)
        synsets = wordnet.synsets(lemmatized_word, pos=pos)

        if not synsets:
            # If no synsets found with POS, try without POS
            synsets = wordnet.synsets(lemmatized_word)

        return synsets
    
    def share_synset(self, word_a, word_b):
        # Symmetric: normalize key order so (a,b) and (b,a) share one cache entry
        key = (min(word_a, word_b), max(word_a, word_b))
        if key in self._share_synset_cache:
            return self._share_synset_cache[key]

        # Check if both words appear in ANY of the same synsets
        # This is a much stricter check than Wu-Palmer distance
        word_a = self.lemmatize(word_a)
        word_b = self.lemmatize(word_b)

        synsets_a = set(s.name() for s in wordnet.synsets(word_a))
        synsets_b = set(s.name() for s in wordnet.synsets(word_b))

        # Direct synset overlap
        if synsets_a & synsets_b:
            self._share_synset_cache[key] = True
            return True

        # Check if word_b appears as a lemma in any of word_a's synsets
        for syn in wordnet.synsets(word_a):
            lemma_names = [l.name() for l in syn.lemmas()]
            if word_b in lemma_names:
                self._share_synset_cache[key] = True
                return True

        self._share_synset_cache[key] = False
        return False
    
    #antonym detection
    def are_antonyms(self, word_a, word_b):
        key = (word_a, word_b)
        if key in self._antonym_cache:
            return self._antonym_cache[key]

        # Lemmatize first so WordNet finds the right entries
        word_a = self.lemmatize(word_a)
        word_b = self.lemmatize(word_b)

        result = False
        synsets = wordnet.synsets(word_a)
        for syn in synsets:
            for lemma in syn.lemmas():
                for antonym in lemma.antonyms():
                    ant_word = antonym.name()

                    #check if word_b IS the antonym
                    if ant_word == word_b:
                        result = True
                        break
                    #check if word_b is a SYNONYM of the antonym
                    ant_synsets = wordnet.synsets(ant_word)
                    b_synsets = wordnet.synsets(word_b)
                    for ant_syn in ant_synsets:
                        for b_syn in b_synsets:
                            sim = ant_syn.wup_similarity(b_syn)
                            if sim and sim > 0.95:
                                result = True
                                break
                        if result:
                            break
                if result:
                    break
            if result:
                break

        self._antonym_cache[key] = result
        return result
    
    #direct antonym check (without synset similarity)
    def are_direct_antonyms(self, word_a, word_b):
        key = (word_a, word_b)
        if key in self._direct_antonym_cache:
            return self._direct_antonym_cache[key]

        word_a = self.lemmatize(word_a)
        word_b = self.lemmatize(word_b)
        synsets = wordnet.synsets(word_a)
        result = False
        for syn in synsets:
            for lemma in syn.lemmas():
                antonyms = [ant.name() for ant in lemma.antonyms()]
                if word_b in antonyms:
                    result = True
                    break
            if result:
                break

        self._direct_antonym_cache[key] = result
        return result

    #Step 3: Wu-palmer similarity between two words
    def wu_palmer_similarity(self, word1, word2):
        # Symmetric: normalize key order so (a,b) and (b,a) share one cache entry
        key = (min(word1, word2), max(word1, word2))
        if key in self._wup_cache:
            return self._wup_cache[key]

        word_a = self.lemmatize(word1)
        word_b = self.lemmatize(word2)

        synsets_1 = self.get_synsets(word_a)
        synsets_2 = self.get_synsets(word_b)

        #if either word is not found in Wordnet, return 0 similarity
        if not synsets_1 or not synsets_2:
            self._wup_cache[key] = 0.0
            return 0.0

        #find the best similarity between any pair of synsets
        max_similarity = 0.0
        for syn1 in synsets_1:
            for syn2 in synsets_2:
                similarity = syn1.wup_similarity(syn2)
                if similarity is not None and similarity > max_similarity:
                    max_similarity = similarity

        result = round(max_similarity, 4)
        self._wup_cache[key] = result
        return result
    
    #Step 4: token to token best match
    #for each token in A find the best matching token in B
    def best_token_match(self, tokens_a, tokens_b):
        if not tokens_a or not tokens_b:
            return 0.0
        
        total_similarity = 0.0

        for token_a in tokens_a:
            best_match_score = 0.0
            best_match_word = None

            for token_b in tokens_b:
                #check exact mathch first
                if token_a == token_b:
                    score = 1.0
                else:
                    if self.are_antonyms(token_a, token_b):
                        score = 0.0
                    else:
                        wu_score = self.wu_palmer_similarity(token_a, token_b)
                        shares_synset = self.share_synset(token_a, token_b)
                       
                        if shares_synset:
                         score = wu_score
                        elif wu_score >= 0.9:
                         score = wu_score
                        else:
                         score = 0.0

                if score > best_match_score:
                    best_match_score = score
                    best_match_word = token_b
            
            # print(f"  '{token_a}' best match → '{best_match_word}' = {best_match_score}")
            total_similarity += best_match_score

        return round(total_similarity / len(tokens_a), 4) # Average similarity across all tokens in A
    
    #Step 5: Symmetric matching
    #Run matching both ways A -> B and B -> A and average the scores
    #This ensures the score is the same regardless of input order
    def compare(self, sentence_a, sentence_b):
        tokens_a = self.preprocessor.process(sentence_a)
        tokens_b = self.preprocessor.process(sentence_b)

        # print(f"\nTokens A: {tokens_a}")
        # print(f"Tokens B: {tokens_b}")

        # print("\nA → B matches:")
        score_ab = self.best_token_match(tokens_a, tokens_b)

        # print("\nB → A matches:")
        score_ba = self.best_token_match(tokens_b, tokens_a)

        # Symmetric average
        final_score = round((score_ab + score_ba) / 2, 4)
        return final_score


#testing
if __name__ == "__main__":
    matcher = SynonymMatcher()

    

    pairs = [
        ("The Cat sat on the Mat",          "A feline rested on a rug"),
        ("The Cat sat on the Mat",          "Stock markets crashed today"),
        ("The company increased revenue",   "The company reduced revenue"),
        ("I created a robot",               "I built a robot"),
        ("I wrote the letter",              "The letter was written by me"),
        ("The manager announced the policy during the meeting",
         "During the meeting the manager announced the policy"),
    ]


    print("=" * 70)
    for sentence_a, sentence_b in pairs:
        print(f"\nSentence A: {sentence_a}")
        print(f"Sentence B: {sentence_b}")
        score = matcher.compare(sentence_a, sentence_b)
        print(f"Final WordNet Score: {score}")
        print("-" * 70)




