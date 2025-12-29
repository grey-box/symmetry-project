from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
comparison_models = [
    "sentence-transformers/LaBSE",
    "xlm-roberta-base",
    "multi-qa-distilbert-cos-v1",
    "multi-qa-MiniLM-L6-cos-v1",
    "multi-qa-mpnet-base-cos-v1"
]

def semantic_compare(model_name, og_article, translated_article, source_language, target_language, sim_threshold):  # main function
    """
    semantic_compare(model_name, og_article, translated_article, source_language, target_language, sim_threshold)
    Performs semantic comparison between two articles in different languages.
    
    Expected parameters:
    {
        "model_name": "string - name of the transformer model to use",
        "og_article": "string - original article text",
        "translated_article": "string - translated article text",
        "source_language": "string - language code of original article",
        "target_language": "string - language code of translated article",
        "sim_threshold": "float - similarity threshold value"
    }
    
    Returns:
    {
        "source_sentences": [sentences from original article],
        "target_sentences": [sentences from translated article],
        "missing_info_index": [indices of missing content],
        "extra_info_index": [indices of extra content]
    }
    """
    # Load a multilingual sentence transformer model (LaBSE or cmlm)
    match model_name:
        case "sentence-transformers/LaBSE":
            model = SentenceTransformer('sentence-transformers/LaBSE')
        case "xlm-roberta-base":
            model = SentenceTransformer('xlm-roberta-base')
        case "multi-qa-distilbert-cos-v1":
            model = SentenceTransformer('multi-qa-distilbert-cos-v1')
        case "multi-qa-MiniLM-L6-cos-v1":
            model = SentenceTransformer('multi-qa-MiniLM-L6-cos-v1')
        case "multi-qa-mpnet-base-cos-v1":
            model = SentenceTransformer('multi-qa-mpnet-base-cos-v1')
        case _:   
            model = SentenceTransformer('sentence-transformers/LaBSE') 

    og_article_sentences = preprocess_input(og_article, source_language)
    translated_article_sentences = preprocess_input(translated_article, target_language)

    # encode the sentences
    og_embeddings = model.encode(og_article_sentences)
    translated_embeddings = model.encode(translated_article_sentences)

    if sim_threshold is None:
        sim_threshold = 0.75

    missing_info, missing_info_index = sentences_diff(og_article_sentences, og_embeddings, translated_embeddings, sim_threshold)
    extra_info, extra_info_index = sentences_diff(translated_article_sentences, translated_embeddings, og_embeddings, sim_threshold)
    return og_article_sentences, translated_article_sentences, missing_info_index, extra_info_index

def universal_sentences_split(text):
    """
    Splits text into sentences using universal splitting rules.
    
    Expected parameters:
    {
        "text": "string - text to be split into sentences"
    }
    
    Returns:
    {
        "sentences": [array of split sentences]
    }
    """
    sentences = []
    for sentence in text.replace('!', '.').replace('?', '.').split('.'):
        if sentence.strip():
            sentences.append(sentence.strip())
    return sentences

def preprocess_input(article, language):
    """
    Preprocesses input text based on language using appropriate spaCy model.
    
    Expected parameters:
    {
        "article": "string - article text to preprocess",
        "language": "string - language code for the article"
    }
    
    Returns:
    {
        "sentences": [array of preprocessed sentences]
    }
    """
    # Define a mapping of languages to spaCy model names
    language_model_map = {
        "en": "en_core_web_sm",  # English
        "de": "de_core_news_sm",  # German
        "fr": "fr_core_news_sm",  # French
        "es": "es_core_news_sm",  # Spanish
        "it": "it_core_news_sm",  # Italian
        "pt": "pt_core_news_sm",  # Portuguese
        "nl": "nl_core_news_sm",  # Dutch
    }
    
    # Acommodate for TITLES
    cleaned_article = article.replace('\n\n', '<DOUBLE_NEWLINE>') # temporarily replace double newlines
    cleaned_article = cleaned_article.replace('\n', '.') # replace single newlines with periods
    cleaned_article = cleaned_article.replace('<DOUBLE_NEWLINE>', ' ').strip() # remove double newlines
    
    # Check if the language is supported
    if language not in language_model_map:
        sentences = universal_sentences_split(cleaned_article)  # Fallback to universal sentence splitting
        return sentences
    else:
    # Load the appropriate spaCy model
        model_name = language_model_map[language]
        nlp = spacy.load(model_name)

        # Process the article and extract sentences
        doc = nlp(cleaned_article)
        sentences = [sent.text for sent in doc.sents]
        return sentences

def sentences_diff(article_sentences, first_embeddings, second_embeddings, sim_threshold):
    """
    Compares sentence embeddings to find semantic differences.
    
    Expected parameters:
    {
        "article_sentences": [array of sentences],
        "first_embeddings": [array of sentence embeddings from first article],
        "second_embeddings": [array of sentence embeddings from second article],
        "sim_threshold": "float - similarity threshold value"
    }
    
    Returns:
    {
        "diff_info": [array of differing sentences],
        "indices": [array of indices where differences occur]
    }
    """
    diff_info = []
    indices = []  # Track the indices of differing sentences
    for i, eng_embedding in enumerate(first_embeddings):
        # Calculate similarity between the current English sentence and all French sentences
        similarities = cosine_similarity([eng_embedding], second_embeddings)[0]

        # Find the best matching sentences
        max_sim = max(similarities)

        if max_sim < sim_threshold:  # Threshold for similarity
            diff_info.append(article_sentences[i])  # This sentence might be missing or extra
            indices.append(i)
            
    return diff_info, indices

def perform_semantic_comparison(request_data):
    """
    Process the JSON request data and perform semantic comparison
    
    Expected JSON format:
    {
        "article_text_blob_1": "string",
        "article_text_blob_2": "string",
        "article_text_blob_1_language": "string",
        "article_text_blob_2_language": "string",
        "comparison_threshold": 0,
        "model_name": "string"
    }
    
        Returns:
    {
        "comparisons": [
            {
                "left_article_array": [sentences from article 1],
                "right_article_array": [sentences from article 2],
                "left_article_missing_info_index": [indices of missing content],
                "right_article_extra_info_index": [indices of extra content]
            }
        ]
    }
    """
    # Extract values from request data
    source_article = request_data["article_text_blob_1"]
    target_article = request_data["article_text_blob_2"]
    source_language = request_data["article_text_blob_1_language"]
    target_language = request_data["article_text_blob_2_language"]
    sim_threshold = request_data["comparison_threshold"] or 0.65  # Default to 0.65 if 0
    model_name = request_data["model_name"] or "LaBSE"  # Default to LaBSE if not specified

    # Perform semantic comparison
    source_sentences, target_sentences, missing_info_index, extra_info_index = semantic_compare(
        model_name=model_name,
        og_article=source_article,
        translated_article=target_article,
        source_language=source_language,
        target_language=target_language,
        sim_threshold=sim_threshold
    )

    # Return results in a structured format
    return {
        "comparisons": [
            {
                "left_article_array": source_sentences,
                "right_article_array": target_sentences,
                "left_article_missing_info_index": missing_info_index,
                "right_article_extra_info_index": extra_info_index
            }
        ]
    }


def main(): #testing the code
    # Example test request data
    test_request = {
        "article_text_blob_1": "This is the first sentence.\n\nThis is the second sentence\nThis is the third sentence.",
        "article_text_blob_2": "\n\nCeci est la première phrase\nJe vais bien. Ceci est la deuxième phrase.",
        "article_text_blob_1_language": "en",
        "article_text_blob_2_language": "fr",
        "comparison_threshold": 0.65,
        "model_name": "sentence-transformers/LaBSE"
    }
    
    result = perform_semantic_comparison(test_request)
    print("Comparison Results:", result)


if __name__ == "__main__":
    main()
