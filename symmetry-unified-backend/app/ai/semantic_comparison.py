from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import spacy
import os
import sys
import logging

try:
    from app.services.chunking import chunk_text
except ModuleNotFoundError:
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    from app.services.chunking import chunk_text

from app.ai.model_registry import COMPARISON_MODELS, DEFAULT_MODEL
from app.core.settings import SIMILARITY_THRESHOLD as _DEFAULT_SIMILARITY_THRESHOLD
try:
    # Optional: use the similarity_prototype pipeline when requested
    # Make sure the similarity_prototype package directory is on sys.path so
    # its internal top-level imports like `Phase_1` resolve correctly.
    sp_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "similarity_prototype"))
    if os.path.isdir(sp_path) and sp_path not in sys.path:
        sys.path.insert(0, sp_path)
    from app.services.similarity_prototype.article_comparator import ArticleComparator
except Exception:
    ArticleComparator = None

logger = logging.getLogger(__name__)


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

    cleaned_article = article.replace("\n\n", "<DOUBLE_NEWLINE>")

    cleaned_article = cleaned_article.replace("\n", ". ")

    cleaned_article = cleaned_article.replace("<DOUBLE_NEWLINE>", " ").strip()

    if len(cleaned_article) > 3500:
        logger.info(
            "Using chunking for large input (chars=%d, chunk_size=%d, overlap=%d)",
            len(cleaned_article),
            450,
            60,
        )
        out = chunk_text(cleaned_article, chunk_size=450, overlap=60)
        logger.info("Chunking produced %d chunks", len(out))
        return [x for x in out if isinstance(x, str) and x.strip()]

    if language in language_model_map:
        try:
            model_name = language_model_map[language]
            nlp = spacy.load(model_name)

            doc = nlp(cleaned_article)
            sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
            return sentences
        except Exception as e:
            print(f"Warning: Could not load spaCy model for {language}: {e}")
            print("Falling back to universal sentence splitting")

    sentences = universal_sentences_split(cleaned_article)
    return [s for s in sentences if isinstance(s, str) and s.strip()]


def sentences_diff(
    article_sentences, source_embeddings, reference_embeddings, similarity_threshold
):
    """
    Find sentences in source that have no close semantic match in the reference.

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
    # extract values from request data
    source_article = request_data["original_article_content"]
    target_article = request_data["translated_article_content"]
    source_language = request_data["original_language"]
    target_language = request_data["translated_language"]
    sim_threshold = request_data.get("comparison_threshold", _DEFAULT_SIMILARITY_THRESHOLD)
    model_name = request_data.get("model_name", DEFAULT_MODEL)

    # perform semantic comparison
    # If the special prototype workflow is requested, route through the
    # similarity_prototype ArticleComparator which returns sentence-pair
    # scores and richer detail. This path expects plain text blobs (not URLs)
    # and will split/clean sentences using the existing preprocess_input.
    if model_name == "similarity_prototype" and ArticleComparator is not None:
        try:
            from app.ai.translations import translate as _translate

            # Prototype NLP tools (TF-IDF vocabulary, WordNet, spaCy en_core_web_sm)
            # are English-only.  Translate both sides to English automatically so
            # the three-phase pipeline operates on a common language.
            if source_language != "en":
                logger.info(
                    "similarity_prototype: translating source (%s→en)", source_language
                )
                source_article = _translate(source_article, source_language, "en")
            if target_language != "en":
                logger.info(
                    "similarity_prototype: translating target (%s→en)", target_language
                )
                target_article = _translate(target_article, target_language, "en")

            comparator = ArticleComparator()

            # Preprocess as English now that both blobs have been translated
            original_sentences = preprocess_input(source_article, "en") or []
            translated_sentences = preprocess_input(target_article, "en") or []

            # Clean and filter using the comparator's gates
            left = [comparator.clean_sentence(s) for s in original_sentences]
            left = [s for s in left if comparator.is_valid_sentence(s)]
            right = [comparator.clean_sentence(s) for s in translated_sentences]
            right = [s for s in right if comparator.is_valid_sentence(s)]

            if not left or not right:
                return {"comparisons": []}

            matrix = comparator.build_score_matrix(left, right)

            ab_scores = comparator.best_match_scores(matrix, direction="AB")
            ba_scores = comparator.best_match_scores(matrix, direction="BA")

            # Final symmetric score (for convenience)
            ab_avg = sum(ab_scores) / len(ab_scores) if ab_scores else 0.0
            ba_avg = sum(ba_scores) / len(ba_scores) if ba_scores else 0.0
            final_score = round((ab_avg + ba_avg) / 2, 4)

            # Build a list of all scored pairs and top matches
            pairs = []
            for i in range(len(left)):
                for j in range(len(right)):
                    pairs.append({
                        "score": matrix[i][j],
                        "sentence_a": left[i],
                        "sentence_b": right[j],
                    })
            pairs.sort(key=lambda x: x["score"], reverse=True)
            top_matches = pairs[:20]

            # per-sentence best matches (A->B and B->A)
            best_ab = []
            for i, s in enumerate(left):
                best_j = max(range(len(right)), key=lambda j: matrix[i][j])
                best_ab.append({
                    "sentence": s,
                    "best_match": right[best_j],
                    "score": matrix[i][best_j],
                })

            best_ba = []
            for j, s in enumerate(right):
                best_i = max(range(len(left)), key=lambda i: matrix[i][j])
                best_ba.append({
                    "sentence": s,
                    "best_match": left[best_i],
                    "score": matrix[best_i][j],
                })

            return {
                "comparisons": [
                    {
                        "left_article_array": left,
                        "right_article_array": right,
                        "left_article_missing_info_index": [i for i, sc in enumerate(ab_scores) if sc < sim_threshold],
                        "right_article_extra_info_index": [i for i, sc in enumerate(ba_scores) if sc < sim_threshold],
                        "success": True,
                        "score": final_score,
                        "details": {
                            "top_matches": top_matches,
                            "best_matches_ab": best_ab,
                            "best_matches_ba": best_ba,
                        },
                    }
                ]
            }
        except Exception as e:
            logger.exception("similarity_prototype comparison failed: %s", e)
            return {"comparisons": []}

    # perform the regular transformer-based semantic comparison
    # We re-run the core steps here so we can also expose per-sentence
    # similarity scores (matrix / best-match) in the returned payload.
    try:
        # Load or reuse a cached model from semantic_compare if available
        if hasattr(semantic_compare, "_cache") and model_name in semantic_compare._cache:
            model = semantic_compare._cache[model_name]
        else:
            model = SentenceTransformer(model_name)
            # populate cache for later calls
            if not hasattr(semantic_compare, "_cache"):
                semantic_compare._cache = {}
            semantic_compare._cache[model_name] = model
    except Exception as e:
        logger.exception("Error loading model %s: %s", model_name, e)
        return {"comparisons": []}

    # Preprocess / split input into sentences
    left = preprocess_input(source_article, source_language) or []
    right = preprocess_input(target_article, target_language) or []

    if not left or not right:
        return {"comparisons": []}

    try:
        left_emb = model.encode(left)
        right_emb = model.encode(right)

        # similarity matrix: rows=left, cols=right
        sim_matrix = cosine_similarity(left_emb, right_emb)

        # Compute missing/extra using existing helper
        missing_info, missing_idx = sentences_diff(left, left_emb, right_emb, sim_threshold)
        extra_info, extra_idx = sentences_diff(right, right_emb, left_emb, sim_threshold)

        # Build pair list and top matches
        pairs = []
        for i in range(len(left)):
            for j in range(len(right)):
                pairs.append({
                    "score": float(round(float(sim_matrix[i][j]), 4)),
                    "sentence_a": left[i],
                    "sentence_b": right[j],
                })
        pairs.sort(key=lambda x: x["score"], reverse=True)
        top_matches = pairs[:min(len(pairs), 50)]

        # best match per sentence A->B
        best_ab = []
        for i, s in enumerate(left):
            best_j = int(sim_matrix[i].argmax())
            best_ab.append({
                "sentence": s,
                "best_match": right[best_j],
                "score": float(round(float(sim_matrix[i][best_j]), 4)),
            })

        # best match per sentence B->A
        best_ba = []
        for j, s in enumerate(right):
            best_i = int(sim_matrix[:, j].argmax())
            best_ba.append({
                "sentence": s,
                "best_match": left[best_i],
                "score": float(round(float(sim_matrix[best_i][j]), 4)),
            })

        final_success = True
    except Exception as e:
        logger.exception("Error during transformer comparison: %s", e)
        missing_info = []
        extra_info = []
        missing_idx = []
        extra_idx = []
        top_matches = []
        best_ab = []
        best_ba = []
        pairs = []
        final_success = False

    return {
        "comparisons": [
            {
                "left_article_array": left,
                "right_article_array": right,
                "left_article_missing_info_index": missing_idx,
                "right_article_extra_info_index": extra_idx,
                "missing_info": missing_info,
                "extra_info": extra_info,
                "success": final_success,
                "score": round((sum([b["score"] for b in best_ab]) / len(best_ab) if best_ab else 0.0 +
                                sum([b["score"] for b in best_ba]) / len(best_ba) if best_ba else 0.0) / 2, 4),
                "details": {
                    "top_matches": top_matches,
                    "best_matches_ab": best_ab,
                    "best_matches_ba": best_ba,
                    "pairs": pairs,
                },
            }
        ]
    }
