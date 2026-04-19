from .vectorizer import Vectorizer
import math

class SimilarityCalculator:
    def __init__(self):
        self.vectorizer = Vectorizer()

    
    #Step 6: Calculate cosine similarity between two TF-IDF vectors
    def cosine_similarity(self, vec1, vec2):
        import numpy as np
        v1, v2 = np.array(vec1), np.array(vec2)
        n1, n2 = np.linalg.norm(v1), np.linalg.norm(v2)
        return float(np.dot(v1, v2) / (n1 * n2)) if n1 and n2 else 0.0
    
    def compare(self, sentence1, sentence2):
        sentences = [sentence1, sentence2]

        #Get TF-IDF vectors for both sentences
        vectors = self.vectorizer.get_vectors(sentences)
        vec1 = vectors[sentence1]
        vec2 = vectors[sentence2]

        score = self.cosine_similarity(vec1, vec2)

        return round(score, 4) # Round to 4 decimal places for better readability
    
    def compare_multiple(self, pairs):
        results = []
        for sentence1, sentence2 in pairs:
            score = self.compare(sentence1, sentence2)
            results.append({
                "sentence_1": sentence1,
                "sentence_2": sentence2,
                "score": score
            })
        return results
    
#testing
if __name__ == "__main__":
    scorer = SimilarityCalculator()

    pairs = [
         ("The Cat sat on the Mat", "A feline rested on a rug"),
        ("The Cat sat on the Mat", "Stock markets crashed today"),
        ("The team completed the project successfully", "The project was successfully completed"),
        ("The company increased revenue this year", "The company reduced revenue this year"),
        ("The manager announced the policy during the meeting", "During the meeting, the manager announced the policy"),
        ("I created a robot", "I built a robot"),
        ("I wrote the letter", "The letter was written by me"),
    ]

    print(f"{'Score':<10} | {'Sentence A':<45} | Sentence B")
    print("-" * 110)

    results = scorer.compare_multiple(pairs)
    for r in results:
        print(f"{r['score']:<10} | {r['sentence_1']:<45} | {r['sentence_2']}")

