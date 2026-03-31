import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from Phase_1.vectorizer import Vectorizer
from Phase_1.similarity import SimilarityCalculator
from Phase_2.synonym_matcher import SynonymMatcher
from Phase_3.role_comparator import RoleComparator

class Scorer:
    def __init__(self):
        self.similarity_scorer = SimilarityCalculator() #phase 1 similarity calculator for baseline
        self.synonym_matcher = SynonymMatcher() # phase 2 synonym matcher for semantic similarity
        self.role_comparator = RoleComparator() # phase 3 role comparator for syntactic role comparison and antonym detection

        #how mmuchg eahc phase contributes to final score
        #Phase 3 weights highest - uses both structure and meaning

        self.WEIGHTS = {
            "phase_1": 0.20, #baseline similarity
            "phase_2": 0.30, #semantic similarity with synonyms
            "phase_3": 0.50  #syntactic role comparison with antonym detection
        }

    def score(self, sentence1, sentence2, verbose=True):

        #phase 1: baseline similarity
        p1 = self.similarity_scorer.compare(sentence1, sentence2)
        #pahse 2: semantic similarity with synonyms
        p2 = self.synonym_matcher.compare(sentence1, sentence2)
        #phase 3: syntactic role comparison with antonym detection
        p3 = self.role_comparator.compare(sentence1, sentence2)

        #weighted final score
        final = round((self.WEIGHTS["phase_1"] * p1) + (self.WEIGHTS["phase_2"] * p2) + (self.WEIGHTS["phase_3"] * p3), 4)
        # if verbose:
        #     print(f"\n  Phase 1 (TF-IDF):   {p1:.4f} x {self.WEIGHTS['phase_1']} = {p1 * self.WEIGHTS['phase_1']:.4f}")
        #     print(f"  Phase 2 (WordNet):  {p2:.4f} x {self.WEIGHTS['phase_2']} = {p2 * self.WEIGHTS['phase_2']:.4f}")
        #     print(f"  Phase 3 (Syntax):   {p3:.4f} x {self.WEIGHTS['phase_3']} = {p3 * self.WEIGHTS['phase_3']:.4f}")
        #     print(f"  ─────────────────────────────────")
        #     print(f"  Final Score:        {final}")

        return final
    
    def score_many(self, pairs, verbose=False):
        results = []
        for sentence1, sentence2 in pairs:
            final = self.score(sentence1, sentence2, verbose=verbose)
            results.append({
                "sentence_1": sentence1,
                "sentence_2": sentence2,
                "score": final
            })
        return results
    
# Testing
if __name__ == "__main__":
    scorer = Scorer()

    pairs = [
        ("The cat sat on the mat",          "A feline rested on a rug"),
        ("The cat sat on the mat",          "Stock markets crashed today"),
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
        score = scorer.score(sentence_a, sentence_b, verbose=True)
        print(f"\n  ► FINAL SCORE: {score}")
        print("-" * 70)