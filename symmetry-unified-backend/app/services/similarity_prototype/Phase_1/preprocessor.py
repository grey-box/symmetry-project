import nltk # Natural Language Toolkit for text processing
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from nltk.tokenize import word_tokenize
import re # Regular expressions for text cleaning
import math

# Only download NLTK data if it isn't already present locally.
# Avoids repeated network/disk checks on every import (and in every
# multiprocessing worker process).
def _ensure_nltk_data():
    _packages = {
        'punkt':     'tokenizers/punkt',
        'stopwords': 'corpora/stopwords',
        'wordnet':   'corpora/wordnet',
        'punkt_tab': 'tokenizers/punkt_tab',
    }
    for pkg, path in _packages.items():
        try:
            nltk.data.find(path)
        except LookupError:
            nltk.download(pkg, quiet=True)

_ensure_nltk_data()


class Preprocessor:
    # Initialize the Preprocessor class with stop words and lemmatizer
    def __init__(self):
        self.stop_words = set(stopwords.words('english'))
        self.lemmatizer = WordNetLemmatizer()
    
    def lowercase(self, text):
        # Convert text to lowercase
        return text.lower()
    
    def remove_punctuation(self, text):
        # Remove punctuation from text using the standard library
        return re.sub(r'[^\w\s]', '', text)
    
    def tokenize(self, text):
        # Tokenize the text into words
        return word_tokenize(text)
    
    def remove_stopwords(self, tokens):
        # Remove stop words from the list of tokens
        return [word for word in tokens if word not in self.stop_words]

    def lemmatize(self, tokens):
        # Lemmatize the tokens to their base form
        return [self.lemmatizer.lemmatize(word) for word in tokens]
    
    def process(self, text):
        # Process the text through all the steps
        text = self.lowercase(text)
        text = self.remove_punctuation(text)
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords(tokens)
        tokens = self.lemmatize(tokens)
        return tokens
    
#testing
if __name__ == "__main__":
    preprocessor = Preprocessor()
    sentences = [
        "The Cat sat on the Mat!!",
        "A feline rested on a rug",
        "The manager announced the policy during the meeting",
        "During the meeting, the manager announced the policy",
        "I wrote the letter",
        "The letter was written by me"
        ]
    
    for s in sentences:
        result = preprocessor.process(s)
        print(f"Original: {s}")
        print(f"Processed: {result}\n")
        print()