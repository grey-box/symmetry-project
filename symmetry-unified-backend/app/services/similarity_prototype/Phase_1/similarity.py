from .vectorizer import Vectorizer
import math

class SimilarityCalculator:
    def __init__(self):
        self.vectorizer = Vectorizer()

    
    #Step 6: Calculate cosine similarity between two TF-IDF vectors
    def cosine_similarity(self, vec1, vec2):
        
        #Dot product
        dot_product = sum(a * b for a, b in zip(vec1, vec2))

        #Magnitude of vec1
        magnitude_vec1 = math.sqrt(sum(a ** 2 for a in vec1))

        #magnitude of vec2
        magnitude_vec2 = math.sqrt(sum(b ** 2 for b in vec2))

        #avoid division by zero
        if magnitude_vec1 == 0 or magnitude_vec2 == 0:
            return 0.0
        
        #Cosine similarity formula
        cosine_sim = dot_product / (magnitude_vec1 * magnitude_vec2)
        return cosine_sim
    
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

