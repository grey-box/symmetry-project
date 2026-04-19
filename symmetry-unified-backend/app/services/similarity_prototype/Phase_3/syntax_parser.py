import spacy

# Lazy-load the spaCy model: only called the first time a SyntaxParser is
# instantiated.  This prevents the model from loading in multiprocessing
# worker processes that never need it.
_nlp = None

def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("en_core_web_sm")
    return _nlp

class SyntaxParser:
    def __init__(self):
        self.nlp = _get_nlp()

    #step 1: Parse sentence into dependecy tree
    def parse(self, sentence):
        return self.nlp(sentence)
    
    #step 2: Check if sentence is passive voice
    #passive indicators: "nsubjpass" or "auxpass" dependency labels
    def is_passive(self, doc):
        for token in doc:
            if token.dep_ in ("nsubjpass", "auxpass"):
                return True
        return False
    
    #step 3: Extract roles from active sentence
    def extract_active_roles(self, doc):
        roles = {
            "subject": None,
            "verb": None,
            "object": None,
            "prep": None,
            "modifiers": []
        }

        for token in doc:
            #Main verb
            if token.dep_ == "ROOT":
                roles["verb"] = token.lemma_
            #Subject
            elif token.dep_ == "nsubj":
                roles["subject"] = token.lemma_
            #Direct object
            elif token.dep_ == "dobj":
                roles["object"] = token.lemma_
            #Object of preposition
            elif token.dep_ == "pobj":
                 if roles["object"] is None:
                     roles["object"] = token.lemma_
            #preposition
            elif token.dep_ == "prep":
                roles["prep"] = token.lemma_
            #Adjectives or adverb modifiers
            elif token.dep_ in ("amod", "advmod"):
                roles["modifiers"].append(token.lemma_)


        return roles
    
    #step 4: Extract roles from passive sentence  and normalize to active
    #"The man was bitten by the dog" 
    # → subject=dog, verb=bite, object=man (same as active)
    def extract_passive_roles(self, doc):
        roles = {
            "subject": None,
            "verb": None,
            "object": None,
            "prep": None,
            "modifiers": []
        }

        for token in doc:
            #Main verb
            if token.dep_ == "ROOT":
                roles["verb"] = token.lemma_
            #Passive subject (logical object)
            elif token.dep_ == "nsubjpass":
                roles["object"] = token.lemma_
            # Agent (by X) becomes the subject
            elif token.dep_ == "agent":
                # Get the noun inside "by X"
                for child in token.children:
                    if child.dep_ == "pobj":
                        roles["subject"] = child.lemma_
            # Preposition
            elif token.dep_ == "prep" and token.lemma_ != "by":
                roles["prep"] = token.lemma_

            #Adjectives or adverb modifiers
            elif token.dep_ in ("amod", "advmod"):
                roles["modifiers"].append(token.lemma_)
        return roles
    
    #Step 5: Main extract function 
    def extract_roles(self, sentence):
        doc = self.parse(sentence)

        if self.is_passive(doc):
            roles = self.extract_passive_roles(doc)
            roles["voice"] = "passive"
        else:
            roles = self.extract_active_roles(doc)
            roles["voice"] = "active"
        return roles
    
    # Batch extract roles for a list of sentences using nlp.pipe()
    # Much faster than calling extract_roles() one at a time because spaCy
    # processes sentences in batches internally instead of one by one
    def batch_extract_roles(self, sentences):
        roles_map = {}
        docs = list(self.nlp.pipe(sentences))
        for sentence, doc in zip(sentences, docs):
            if self.is_passive(doc):
                roles = self.extract_passive_roles(doc)
                roles["voice"] = "passive"
            else:
                roles = self.extract_active_roles(doc)
                roles["voice"] = "active"
            roles_map[sentence] = roles
        return roles_map

    # Helper: print parse tree for debugging
    def print_parse(self, sentence):
        doc = self.parse(sentence)
        print(f"\nParse tree for: '{sentence}'")
        print(f"{'Token':<15} | {'POS':<8} | {'Dep':<12} | {'Head':<15} | Lemma")
        print("-" * 70)
        for token in doc:
            print(f"{token.text:<15} | {token.pos_:<8} | {token.dep_:<12} | {token.head.text:<15} | {token.lemma_}")

#testing
# Testing
if __name__ == "__main__":
    parser = SyntaxParser()

    test_sentences = [
        "The cat sat on the mat",
        "A feline rested on a rug",
        "I wrote the letter",
        "The letter was written by me",
        "The dog bit the man",
        "The man was bitten by the dog",
        "I created a robot",
        "I built a robot",
        "The manager announced the policy during the meeting",
        "During the meeting the manager announced the policy",
        "The company increased revenue this year",
        "The company reduced revenue this year",
    ]

    print("=" * 70)
    for sentence in test_sentences:
        print(f"\nSentence: '{sentence}'")
        
        # Show full parse tree
        parser.print_parse(sentence)
        
        # Show extracted roles
        roles = parser.extract_roles(sentence)
        print(f"\nExtracted roles:")
        print(f"  Voice:     {roles['voice']}")
        print(f"  Subject:   {roles['subject']}")
        print(f"  Verb:      {roles['verb']}")
        print(f"  Object:    {roles['object']}")
        print(f"  Prep:      {roles['prep']}")
        print(f"  Modifiers: {roles['modifiers']}")
        print("-" * 70)