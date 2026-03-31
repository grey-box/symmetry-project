
from .preprocessor import Preprocessor
import math

class Vectorizer:
    def __init__(self):
        self.preprocessor = Preprocessor()
        self.vocabulary = []

    #step 2: Build vocab from all sentences
    def build_vocabulary(self, sentences):
        unique_words = set()
        for sentence in sentences:
            tokens = self.preprocessor.process(sentence)
            unique_words.update(tokens)
        self.vocabulary = list(unique_words)
        return self.vocabulary
    
    #step 3: Calculate TF for a sentence
    def calculate_tf(self, tokens):
        tf = {}
        total_words = len(tokens)
        for word in tokens:
            tf[word] = tf.get(word, 0) + 1
        for word in tf:
            tf[word] /= total_words
        return tf
    
    #Step 4:  Calculate IDF across all sentences
    def calculate_idf(self, sentences):
        total_sentences = len(sentences)
        idf = {}
        all_tokens = []

        # Create a list of token sets for each sentence to count how many sentences contain each word
        for sentence in sentences:
            tokens = set(self.preprocessor.process(sentence))
            all_tokens.append(tokens)

        # Calculate IDF for each word in the vocabulary
        for word in self.vocabulary:
            sentences_with_word = sum(1 for tokens in all_tokens if word in tokens)
            idf[word] = math.log(total_sentences /  sentences_with_word) + 1

        return idf
    
    #Step 5: Calculate TF-IDF vector for a sentence
    def calcualate_tfidf(self, sentence, idf):
        tokens = self.preprocessor.process(sentence)
        tf = self.calculate_tf(tokens)
       
        tfdif_vector = []
        for word in self.vocabulary:
            tf_value = tf.get(word, 0.0)
            idf_value = idf.get(word, 0.0)
            tfdif_vector.append(tf_value * idf_value)
        return tfdif_vector
    
    def get_vectors(self, sentences):
        self.build_vocabulary(sentences)
        idf = self.calculate_idf(sentences)
        vectors = {}
        for sentence in sentences:
            vectors[sentence] = self.calcualate_tfidf(sentence, idf)
        return vectors
    



#testing
if __name__ == "__main__":
    vectorizer = Vectorizer()
    sentences = [
        "The Cat sat on the Mat!!",
        "A feline rested on a rug",
        "The manager announced the policy during the meeting",
        "During the meeting, the manager announced the policy",
        "I wrote the letter",
        "The letter was written by me"
    ]

    #build vocab
    vocab = vectorizer.build_vocabulary(sentences)
    print("Vocabulary:", vocab)

    #get vectors
    vectors = vectorizer.get_vectors(sentences)
    print("\nTF-IDF Vectors:")
    for sentence, vector in vectors.items():
        print(f"\nSentence: {sentence}")

        #only show non-zero values 
        non_zero = {
            vectorizer.vocabulary[i]: round(vector[i], 4)
            for i in range(len(vector))
            if vector[i] > 0
        }
        print(f"Non-zero values: {non_zero}")

