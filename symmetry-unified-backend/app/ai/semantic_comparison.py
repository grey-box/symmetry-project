from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import spacy

comparison_models = [
    "sentence-transformers/LaBSE",
    "xlm-roberta-base",
    "multi-qa-distilbert-cos-v1",
    "multi-qa-MiniLM-L6-cos-v1",
    "multi-qa-mpnet-base-cos-v1",
]


def semantic_compare(
    original_blob,
    translated_blob,
    source_language,
    target_language,
    sim_threshold,
    model_name,
):
    """
    Performs semantic comparison between two articles in different languages.

    Expected parameters:
    {
        "original_blob": "string - original article text",
        "translated_blob": "string - translated article text",
        "source_language": "string - language code of original article",
        "target_language": "string - language code of translated article",
        "sim_threshold": "float - similarity threshold value",
        "model_name": "string - name of the transformer model to use"
    }

    Returns:
    {
        "original_sentences": [sentences from original article],
        "translated_sentences": [sentences from translated article],
        "missing_info": [sentences missing from translation],
        "extra_info": [sentences added in translation],
        "missing_info_indices": [indices of missing content],
        "extra_info_indices": [indices of extra content],
        "success": [true or false depending on if request was successful]
    }
    """
    success = True

    # Load a multilingual sentence transformer model (LaBSE or similar)
    try:
        if model_name is None:
            model_name = "sentence-transformers/LaBSE"
        model = SentenceTransformer(model_name)
    except Exception as e:
        print(f"Error loading model {model_name}: {e}")
        return {
            "original_sentences": [original_blob],
            "translated_sentences": [translated_blob],
            "missing_info": [],
            "extra_info": [],
            "missing_info_indices": [],
            "extra_info_indices": [],
            "success": False,
        }

    try:
        original_sentences = preprocess_input(original_blob, source_language)
        translated_sentences = preprocess_input(translated_blob, target_language)
    except Exception as e:
        print(f"Error preprocessing input: {e}")
        success = False
        original_sentences = [original_blob]
        translated_sentences = [translated_blob]

    try:
        # encode the sentences
        original_embeddings = model.encode(original_sentences)
        translated_embeddings = model.encode(translated_sentences)

        if sim_threshold is None:
            sim_threshold = 0.75

        missing_info, missing_info_indices = sentences_diff(
            original_sentences,
            original_embeddings,
            translated_embeddings,
            sim_threshold,
        )

        extra_info, extra_info_indices = sentences_diff(
            translated_sentences,
            translated_embeddings,
            original_embeddings,
            sim_threshold,
        )
    except Exception as e:
        print(f"Error during semantic comparison: {e}")
        success = False
        missing_info = []
        extra_info = []
        missing_info_indices = []
        extra_info_indices = []

    return {
        "original_sentences": original_sentences,
        "translated_sentences": translated_sentences,
        "missing_info": missing_info,
        "extra_info": extra_info,
        "missing_info_indices": missing_info_indices,
        "extra_info_indices": extra_info_indices,
        "success": success,
    }


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
    for sentence in text.replace("!", ".").replace("?", ".").split("."):
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

    # Accommodate for TITLES and single newlines as sentence boundaries
    # Preserve double newlines as paragraph breaks
    # Replace single newlines with period+space to treat them as sentence boundaries
    cleaned_article = article.replace("\n\n", "<DOUBLE_NEWLINE>")

    # Single newlines should be treated as sentence boundaries
    # Replace them with '. ' to ensure they're treated as separate sentences
    cleaned_article = cleaned_article.replace("\n", ". ")

    # Restore paragraph breaks as spaces
    cleaned_article = cleaned_article.replace("<DOUBLE_NEWLINE>", " ").strip()

    if language in language_model_map:
        try:
            # Load the appropriate spaCy model
            model_name = language_model_map[language]
            nlp = spacy.load(model_name)

            # Process the article and extract sentences
            doc = nlp(cleaned_article)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            return sentences
        except Exception as e:
            print(f"Warning: Could not load spaCy model for {language}: {e}")
            print("Falling back to universal sentence splitting")

    # Fallback to universal sentence splitting
    sentences = universal_sentences_split(cleaned_article)
    return sentences


def sentences_diff(
    article_sentences, first_embeddings, second_embeddings, sim_threshold
):
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
            diff_info.append(
                article_sentences[i]
            )  # This sentence might be missing or extra
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
    model_name = (
        request_data["model_name"] or "sentence-transformers/LaBSE"
    )  # Default to LaBSE if not specified

    # Perform semantic comparison
    result = semantic_compare(
        source_article,
        target_article,
        source_language,
        target_language,
        sim_threshold,
        model_name,
    )

    # Return results in a structured format
    return {
        "comparisons": [
            {
                "left_article_array": result["original_sentences"],
                "right_article_array": result["translated_sentences"],
                "left_article_missing_info_index": result["missing_info_indices"],
                "right_article_extra_info_index": result["extra_info_indices"],
                "missing_info": result["missing_info"],
                "extra_info": result["extra_info"],
                "success": result["success"],
            }
        ]
    }


def main():  # testing the code
    # Example test request data
    test_request = {
        "article_text_blob_1": "This is the first sentence.\n\nThis is the second sentence\nThis is the third sentence.",
        "article_text_blob_2": "\n\nCeci est la première phrase\nJe vais bien. Ceci est la deuxième phrase.",
        "article_text_blob_1_language": "en",
        "article_text_blob_2_language": "fr",
        "comparison_threshold": 0.65,
        "model_name": "sentence-transformers/LaBSE",
    }

    result = perform_semantic_comparison(test_request)
    print("Comparison Results:", result)


if __name__ == "__main__":
    main()
