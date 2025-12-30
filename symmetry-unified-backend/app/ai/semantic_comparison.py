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
    model_name,
    og_article,
    translated_article,
    source_language,
    target_language,
    sim_threshold,
):  # main function
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
    # Load a multilingual sentence transformer model (LaBSE or cmlm)
    match model_name:
        case "sentence-transformers/LaBSE":
            model = SentenceTransformer("sentence-transformers/LaBSE")
        case "xlm-roberta-base":
            model = SentenceTransformer("xlm-roberta-base")
        case "multi-qa-distilbert-cos-v1":
            model = SentenceTransformer("multi-qa-distilbert-cos-v1")
        case "multi-qa-MiniLM-L6-cos-v1":
            model = SentenceTransformer("multi-qa-MiniLM-L6-cos-v1")
        case "multi-qa-mpnet-base-cos-v1":
            model = SentenceTransformer("multi-qa-mpnet-base-cos-v1")
        case _:
            model = SentenceTransformer("sentence-transformers/LaBSE")

    try:
        if not model_name:
            model_name = DEFAULT_MODEL

        if not hasattr(semantic_compare, "_cache"):
            semantic_compare._cache = {}

        if model_name in semantic_compare._cache:
            model = semantic_compare._cache[model_name]
        else:
            model = SentenceTransformer(model_name)
            semantic_compare._cache[model_name] = model

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
        original_sentences = preprocess_input(original_blob, source_language) or []
        translated_sentences = preprocess_input(translated_blob, target_language) or []
        if not original_sentences or not translated_sentences:
            return {
                "original_sentences": [],
                "translated_sentences": [],
                "missing_info": [],
                "extra_info": [],
                "missing_info_indices": [],
                "extra_info_indices": [],
                "success": False,
            }
    except Exception as e:
        print(f"Error preprocessing input: {e}")
        success = False
        original_sentences = [original_blob]
        translated_sentences = [translated_blob]

    try:
        original_embeddings = model.encode(original_sentences)
        translated_embeddings = model.encode(translated_sentences)

        if sim_threshold is None:
            sim_threshold = _DEFAULT_SIMILARITY_THRESHOLD

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

    missing_info, missing_info_index = sentences_diff(
        og_article_sentences, og_embeddings, translated_embeddings, sim_threshold
    )
    extra_info, extra_info_index = sentences_diff(
        translated_article_sentences,
        translated_embeddings,
        og_embeddings,
        sim_threshold,
    )
    return (
        og_article_sentences,
        translated_article_sentences,
        missing_info_index,
        extra_info_index,
    )


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
    if not article:
        return []

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
    cleaned_article = article.replace(
        "\n\n", "<DOUBLE_NEWLINE>"
    )  # temporarily replace double newlines
    cleaned_article = cleaned_article.replace(
        "\n", "."
    )  # replace single newlines with periods
    cleaned_article = cleaned_article.replace(
        "<DOUBLE_NEWLINE>", " "
    ).strip()  # remove double newlines

    # Check if the language is supported
    if language not in language_model_map:
        sentences = universal_sentences_split(
            cleaned_article
        )  # Fallback to universal sentence splitting
        return sentences
    else:
        # Load the appropriate spaCy model
        model_name = language_model_map[language]
        try:
            nlp = spacy.load(model_name)
        except OSError:
            import subprocess
            import logging

            logging.warning(f"Model '{model_name}' not found. Installing...")
            subprocess.run(
                ["python", "-m", "spacy", "download", model_name], check=True
            )
            nlp = spacy.load(model_name)

    cleaned_article = article.replace("\n\n", "<DOUBLE_NEWLINE>")


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
        unmatched_sentences: Sentences below the similarity threshold.
        unmatched_indices: Their indices in the source article.
    """
    unmatched_sentences = []
    unmatched_indices = []
    for i, embedding in enumerate(source_embeddings):
        similarities = cosine_similarity([embedding], reference_embeddings)[0]
        best_similarity = max(similarities)

        if best_similarity < similarity_threshold:
            unmatched_sentences.append(article_sentences[i])
            unmatched_indices.append(i)

    return unmatched_sentences, unmatched_indices

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
        "original_article_content": "string",
        "translated_article_content": "string",
        "original_language": "string",
        "translated_language": "string",
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
        request_data["model_name"] or "LaBSE"
    )  # Default to LaBSE if not specified

    # Perform semantic comparison
    source_sentences, target_sentences, missing_info_index, extra_info_index = (
        semantic_compare(
            model_name=model_name,
            og_article=source_article,
            translated_article=target_article,
            source_language=source_language,
            target_language=target_language,
            sim_threshold=sim_threshold,
        )
    )

    # Return results in a structured format
    return {
        "comparisons": [
            {
                "left_article_array": source_sentences,
                "right_article_array": target_sentences,
                "left_article_missing_info_index": missing_info_index,
                "right_article_extra_info_index": extra_info_index,
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
