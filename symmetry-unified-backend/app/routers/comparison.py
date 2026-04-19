import logging
import re

from fastapi import APIRouter, HTTPException, Query

from app.models import (
    CompareRequest,
    CompareResponse,
    ArticleComparisonResponse,
    SemanticCompareRequest,
    ChunkedTranslateRequest,
    TranslateArticleResponse,
    MissingInfo,
    ExtraInfo,
    SentenceDiff,
)
from app.models.server_model import ServerModel
from app.ai.model_registry import COMPARISON_MODELS

try:
    from app.ai.semantic_comparison import perform_semantic_comparison
except Exception:
    perform_semantic_comparison = None

router = APIRouter(prefix="/symmetry/v1", tags=["comparison"])


@router.post("/articles/compare", response_model=CompareResponse)
def compare_articles(payload: CompareRequest):
    """
    Compare original and translated article content using semantic similarity.
    """

    if perform_semantic_comparison is None:
        return CompareResponse(
            missing_info=[],
            extra_info=[],
            error_message="Semantic comparison service is unavailable.",
            model_name=payload.model_name,
            similarity_threshold=payload.similarity_threshold,
        )

    request_data = {
        "original_article_content": payload.original_article_content,
        "translated_article_content": payload.translated_article_content,
        "original_language": payload.original_language,
        "translated_language": payload.translated_language,
        "comparison_threshold": payload.similarity_threshold,
        "model_name": payload.model_name,
    }

    result = perform_semantic_comparison(request_data)

    if not result or "comparisons" not in result or not result["comparisons"]:
        return CompareResponse(
            missing_info=[],
            extra_info=[],
            error_message="Comparison failed or returned no results.",
            model_name=payload.model_name,
            similarity_threshold=payload.similarity_threshold,
        )

    # Map the index lists returned by the comparison engine to actual
    # sentence strings for the top-level response so clients can consume
    # a friendly list of missing/extra sentences directly.
    comp = result["comparisons"][0]
    left_array = comp.get("left_article_array", [])
    right_array = comp.get("right_article_array", [])

    left_missing_idx = comp.get("left_article_missing_info_index", [])
    right_extra_idx = comp.get("right_article_extra_info_index", [])

    missing_info = [
        SentenceDiff(sentence=left_array[i], index=i)
        for i in left_missing_idx
        if 0 <= i < len(left_array)
    ]

    extra_info = [
        SentenceDiff(sentence=right_array[i], index=i)
        for i in right_extra_idx
        if 0 <= i < len(right_array)
    ]

    return CompareResponse(
        missing_info=missing_info,
        extra_info=extra_info,
        error_message=None,
        model_name=payload.model_name,
        similarity_threshold=payload.similarity_threshold,
        comparisons=result.get("comparisons"),
    )


@router.get(
    "/comparison/semantic",
    response_model=ArticleComparisonResponse,
    summary="Semantic Comparison (GET)",
    description="Performs semantic comparison between two texts using sentence embeddings. Returns sentences that are missing or extra based on similarity threshold.",
)
def compare_articles_semantic(
    original_article_content: str = Query(..., description="Original article text"),
    translated_article_content: str = Query(..., description="Translated article text"),
    similarity_threshold: float = Query(
        0.75,
        ge=0,
        le=1,
        description="Similarity threshold between 0 and 1. Sentences below this threshold are considered different",
    ),
    model_name: str = Query(
        "sentence-transformers/LaBSE",
        description="Name of the sentence transformer model to use",
    ),
):
    global perform_semantic_comparison
    logging.info("Calling semantic comparison endpoint.")

    if similarity_threshold < 0 or similarity_threshold > 1:
        logging.info(
            "Provided similarity threshold is out of the defined valid range [0,1]"
        )
        raise HTTPException(
            status_code=400,
            detail="Provided similarity threshold is out of the defined valid range [0,1]",
        )

    if model_name not in COMPARISON_MODELS:
        logging.info(f"Invalid model selected. {model_name} does not exist.")
        raise HTTPException(
            status_code=404,
            detail=f"Invalid model selected. {model_name} does not exist.",
        )

    if original_article_content is None or translated_article_content is None:
        logging.info("Invalid input provided to semantic comparison.")
        raise HTTPException(
            status_code=400,
            detail="Either original_article_content or translated_article_content (or both) was found to be None.",
        )

    if perform_semantic_comparison is None:
        return ArticleComparisonResponse(
            missing_info=[],
            extra_info=[],
            model_name=model_name,
            similarity_threshold=similarity_threshold,
        )

    result = perform_semantic_comparison(
        {
            "original_article_content": original_article_content,
            "translated_article_content": translated_article_content,
            "original_language": "en",
            "translated_language": "en",
            "comparison_threshold": similarity_threshold,
            "model_name": model_name,
        }
    )

    return ArticleComparisonResponse(
        missing_info=[
            MissingInfo(
                sentence=result["comparisons"][0]["left_article_array"][idx], index=idx
            )
            for idx in result["comparisons"][0]["left_article_missing_info_index"]
        ],
        extra_info=[
            ExtraInfo(
                sentence=result["comparisons"][0]["right_article_array"][idx], index=idx
            )
            for idx in result["comparisons"][0]["right_article_extra_info_index"]
        ],
        model_name=model_name,
        similarity_threshold=similarity_threshold,
    )


@router.post(
    "/comparison/semantic",
    response_model=ArticleComparisonResponse,
    summary="Semantic Comparison (POST)",
    description="Performs semantic comparison between two texts using sentence embeddings via POST request. Returns sentences that are missing or extra based on similarity threshold.",
)
def compare_articles_semantic_post(payload: SemanticCompareRequest):
    logging.info("Calling semantic comparison endpoint (POST).")

    if payload.similarity_threshold < 0 or payload.similarity_threshold > 1:
        logging.info(
            "Provided similarity threshold is out of the defined valid range [0,1]"
        )
        raise HTTPException(
            status_code=400,
            detail="Provided similarity threshold is out of the defined valid range [0,1]",
        )

    if payload.model_name not in COMPARISON_MODELS:
        logging.info(f"Invalid model selected. {payload.model_name} does not exist.")
        raise HTTPException(
            status_code=404,
            detail=f"Invalid model selected. {payload.model_name} does not exist.",
        )

    if perform_semantic_comparison is None:
        return ArticleComparisonResponse(
            missing_info=[],
            extra_info=[],
            model_name=payload.model_name,
            similarity_threshold=payload.similarity_threshold,
        )

    request_data = {
        "original_article_content": payload.original_article_content,
        "translated_article_content": payload.translated_article_content,
        "original_language": "en",
        "translated_language": "en",
        "comparison_threshold": payload.similarity_threshold,
        "model_name": payload.model_name,
    }

    result = perform_semantic_comparison(request_data)

    if result and result.get("comparisons"):
        comp = result["comparisons"][0]
        missing_items = [
            comp["left_article_array"][i]
            for i in comp["left_article_missing_info_index"]
        ]
        extra_items = [
            comp["right_article_array"][i]
            for i in comp["right_article_extra_info_index"]
        ]

        return ArticleComparisonResponse(
            missing_info=[
                MissingInfo(sentence=item, index=-1) for item in missing_items
            ],
            extra_info=[ExtraInfo(sentence=item, index=-1) for item in extra_items],
            model_name=payload.model_name,
            similarity_threshold=payload.similarity_threshold,
        )

    return ArticleComparisonResponse(
        missing_info=[],
        extra_info=[],
        model_name=payload.model_name,
        similarity_threshold=payload.similarity_threshold,
    )


@router.get(
    "/wiki_translate/source_article",
    response_model=dict,
    summary="Translate Wikipedia Article",
    description="Finds and retrieves a translated version of a Wikipedia article in the target language.",
)
def translate_article(
    url: str = Query(None, description="Full Wikipedia URL of the source article"),
    title: str = Query(
        None, description="Title of the source article (alternative to URL)"
    ),
    language: str = Query(
        ..., description="Target language code (e.g., 'fr', 'es', 'de')"
    ),
):
    import wikipediaapi
    from app.services.wiki_utils import get_translation
    from urllib.parse import unquote

    logging.info(
        f"Calling translate article endpoint for title: {title}, url: {url} and language: {language}"
    )

    source_lang = "en"
    if url:
        match = re.search(r"/wiki/([^#?]*)", url)
        if match:
            title = match.group(1).replace("_", " ")
            title = unquote(title)

            lang_match = re.search(r"https?://([a-z]{2})\.wikipedia\.org", url)
            if lang_match:
                source_lang = lang_match.group(1)
        else:
            logging.info("Invalid Wikipedia URL provided.")
            raise HTTPException(
                status_code=400, detail="Invalid Wikipedia URL provided."
            )

    if not title:
        logging.info("Either 'url' or 'title' must be provided.")
        raise HTTPException(
            status_code=400, detail="Either 'url' or 'title' must be provided."
        )

    if not language:
        logging.info("Target language must be provided.")
        raise HTTPException(status_code=400, detail="Target language must be provided.")

    logging.info(f"Finding translated title from {source_lang}:{title} to {language}")
    translated_title = get_translation(title, source_lang, language)

    if not translated_title:
        logging.info(f"Translation not available for the selected language: {language}")
        raise HTTPException(
            status_code=404,
            detail="Translation not available for the selected language.",
        )

    logging.info(f"Found translated title: {translated_title}")

    translated_wiki = wikipediaapi.Wikipedia(
        user_agent="SymmetryUnified/1.0 (contact@grey-box.ca)", language=language
    )
    translated_page = translated_wiki.page(translated_title)

    if not translated_page.exists():
        logging.info("Translated article not found.")
        raise HTTPException(status_code=404, detail="Translated article not found.")

    translated_content = translated_page.text if translated_page.text else ""

    return {"translatedArticle": translated_content}


@router.get(
    "/translate_text",
    response_model=dict,
    summary="Translate Text",
    description="Translates text from source language to target language using configured translation model.",
)
def translate_text_endpoint(
    source_language: str = Query(..., description="Source language code (e.g., 'en')"),
    target_language: str = Query(..., description="Target language code (e.g., 'fr')"),
    text: str = Query(..., description="Text to translate"),
):
    server = ServerModel()

    try:
        translated_text = server.text_translate(text, source_language, target_language)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Translation failed: {exc}")

    return {"translatedArticle": translated_text}


@router.post(
    "/wiki_translate/chunked_text",
    response_model=TranslateArticleResponse,
    summary="Translate Text (Chunked)",
    description="Translates long text using the chunked translation pipeline.",
)
def translate_chunked_text_endpoint(payload: ChunkedTranslateRequest):
    try:
        from app.ai.translations import translate as chunked_translate

        logging.info(
            "Chunked translation request (source='%s', target='%s', chars=%d)",
            payload.source_language,
            payload.target_language,
            len(payload.text or ""),
        )
        translated = chunked_translate(
            payload.text,
            payload.source_language,
            payload.target_language,
        )
        return {"translatedArticle": translated}
    except ImportError as e:
        logging.exception("Chunked translation dependency error: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing translation dependency. Install sentencepiece in the backend venv "
                "and restart the backend."
            ),
        )
    except ValueError as e:
        logging.exception("Chunked translation validation error: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Chunked translation failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


# ---------------------------------------------------------------------------
# Section-level structured comparison
# ---------------------------------------------------------------------------

from app.models.section_comparison import (
    SectionCompareRequest,
    SectionCompareResponse,
)
from app.services.article_parser import article_fetcher
from app.services.section_comparison import compare_article_sections


def _resolve_title_and_lang(query: str, default_lang: str) -> tuple[str, str]:
    """Extract Wikipedia title and language from a URL or plain title string."""
    if "://" in query:
        match = re.search(r"https?://([a-z]{2,3})\.wikipedia\.org/wiki/([^#?]*)", query)
        if match:
            from urllib.parse import unquote

            lang = match.group(1)
            title = unquote(match.group(2).replace("_", " "))
            return title, lang
        raise ValueError(f"Invalid Wikipedia URL: {query}")
    return query, default_lang


@router.post(
    "/articles/compare-sections",
    response_model=SectionCompareResponse,
    summary="Section-Level Article Comparison",
    description=(
        "Compares two Wikipedia articles section-by-section and paragraph-by-paragraph "
        "using semantic embeddings. Returns a structured diff showing matched, missing, "
        "and added sections/paragraphs. Uses Levenshtein distance for disambiguation "
        "when semantic similarity scores are close."
    ),
)
def compare_article_sections_endpoint(payload: SectionCompareRequest):
    """Compare two Wikipedia articles at the section and paragraph level."""

    try:
        source_title, source_lang = _resolve_title_and_lang(
            payload.source_query, payload.source_lang
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        target_title, target_lang = _resolve_title_and_lang(
            payload.target_query, payload.target_lang
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        source_article = article_fetcher(source_title, source_lang)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to fetch source article '{source_title}' ({source_lang}): {e}",
        )

    try:
        target_article = article_fetcher(target_title, target_lang)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to fetch target article '{target_title}' ({target_lang}): {e}",
        )

    return compare_article_sections(
        source_article=source_article,
        target_article=target_article,
        similarity_threshold=payload.similarity_threshold,
        model_name=payload.model_name,
    )


@router.post(
    "/wiki_translate/chunked_text",
    response_model=TranslateArticleResponse,
    summary="Translate Text (Chunked)",
    description="Translates long text using the chunked translation pipeline.",
)
def translate_chunked_text_endpoint(payload: ChunkedTranslateRequest):
    from app.ai.translations import translate as chunked_translate

    try:
        logging.info(
            "Chunked translation request (source='%s', target='%s', chars=%d)",
            payload.source_language,
            payload.target_language,
            len(payload.text or ""),
        )
        translated = chunked_translate(
            payload.text,
            payload.source_language,
            payload.target_language,
        )
        return {"translatedArticle": translated}
    except ImportError as e:
        logging.exception("Chunked translation dependency error: %s", str(e))
        raise HTTPException(
            status_code=500,
            detail=(
                "Missing translation dependency. Install sentencepiece in the backend venv "
                "and restart the backend."
            ),
        )
    except ValueError as e:
        logging.exception("Chunked translation validation error: %s", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logging.exception("Chunked translation failed: %s", str(e))
        raise HTTPException(status_code=500, detail=f"Translation failed: {str(e)}")


# ---------------------------------------------------------------------------
# Section-level structured comparison
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

from app.models.section_comparison import (
    SectionCompareRequest,
    SectionCompareResponse,
)
from app.services.article_parser import article_fetcher
from app.services.section_comparison import compare_article_sections


def _resolve_title_and_lang(query: str, default_lang: str) -> tuple[str, str]:
    """Extract Wikipedia title and language from a URL or plain title string."""
    if "://" in query:
        match = re.search(r"https?://([a-z]{2,3})\.wikipedia\.org/wiki/([^#?]*)", query)
        if match:
            from urllib.parse import unquote

            lang = match.group(1)
            title = unquote(match.group(2).replace("_", " "))
            return title, lang
        raise ValueError(f"Invalid Wikipedia URL: {query}")
    return query, default_lang


@router.post(
    "/articles/compare-sections",
    response_model=SectionCompareResponse,
    summary="Section-Level Article Comparison",
    description=(
        "Compares two Wikipedia articles section-by-section and paragraph-by-paragraph "
        "using semantic embeddings. Returns a structured diff showing matched, missing, "
        "and added sections/paragraphs. Uses Levenshtein distance for disambiguation "
        "when semantic similarity scores are close."
    ),
)
def compare_article_sections_endpoint(payload: SectionCompareRequest):
    """Compare two Wikipedia articles at the section and paragraph level."""

    try:
        source_title, source_lang = _resolve_title_and_lang(
            payload.source_query, payload.source_lang
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        target_title, target_lang = _resolve_title_and_lang(
            payload.target_query, payload.target_lang
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        source_article = article_fetcher(source_title, source_lang)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to fetch source article '{source_title}' ({source_lang}): {e}",
        )

    try:
        target_article = article_fetcher(target_title, target_lang)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to fetch target article '{target_title}' ({target_lang}): {e}",
        )

    return compare_article_sections(
        source_article=source_article,
        target_article=target_article,
        similarity_threshold=payload.similarity_threshold,
        model_name=payload.model_name,
    )
