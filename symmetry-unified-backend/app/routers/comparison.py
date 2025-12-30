import logging
import re

from fastapi import APIRouter, HTTPException, Query

from app.models import (
    CompareRequest,
    CompareResponse,
    ArticleComparisonResponse,
    SemanticCompareRequest,
    MissingInfo,
    ExtraInfo,
)
from app.models.server_model import ServerModel

try:
    from app.ai.semantic_comparison import perform_semantic_comparison
except Exception:
    perform_semantic_comparison = None

router = APIRouter(prefix="/symmetry/v1", tags=["comparison"])

comparison_models = [
    "sentence-transformers/LaBSE",
    "xlm-roberta-base",
    "multi-qa-distilbert-cos-v1",
    "multi-qa-MiniLM-L6-cos-v1",
    "multi-qa-mpnet-base-cos-v1",
]


@router.post("/articles/compare", response_model=CompareResponse)
def compare_articles(payload: CompareRequest):
    """
    This endpoint requests a comparison of two blobs of text using semantic comparison.
    The request includes the articles, the languages of the articles, the comparison threshold, and model name.
    """
    from app.main import SIMILARITY_THRESHOLD

    # Use threshold from config if not provided in request
    if (
        not hasattr(payload, "comparison_threshold")
        or payload.comparison_threshold is None
    ):
        payload_dict = payload.dict()
        payload_dict["comparison_threshold"] = SIMILARITY_THRESHOLD
    else:
        payload_dict = payload.dict()

    if perform_semantic_comparison is None:
        result = {
            "comparisons": [
                {
                    "left_article_array": [],
                    "right_article_array": [],
                    "left_article_missing_info_index": [],
                    "right_article_extra_info_index": [],
                }
            ]
        }
    else:
        result = perform_semantic_comparison(payload_dict)
    return result


@router.get("/comparison/semantic", response_model=ArticleComparisonResponse)
def compare_articles_semantic(
    text_a: str,
    text_b: str,
    similarity_threshold: float = 0.75,
    model_name: str = "sentence-transformers/LaBSE",
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

    if model_name not in comparison_models:
        logging.info(f"Invalid model selected. {model_name} does not exist.")
        raise HTTPException(
            status_code=404,
            detail=f"Invalid model selected. {model_name} does not exist.",
        )

    if text_a is None or text_b is None:
        logging.info("Invalid input provided to semantic comparison.")
        raise HTTPException(
            status_code=400,
            detail="Either text_a or text_b (or both) was found to be None.",
        )

    if perform_semantic_comparison is None:
        return ArticleComparisonResponse(missing_info=[], extra_info=[])

    result = perform_semantic_comparison(
        {
            "article_text_blob_1": text_a,
            "article_text_blob_2": text_b,
            "article_text_blob_1_language": "en",
            "article_text_blob_2_language": "en",
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
    )


@router.post("/comparison/semantic", response_model=ArticleComparisonResponse)
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

    if payload.model_name not in comparison_models:
        logging.info(f"Invalid model selected. {payload.model_name} does not exist.")
        raise HTTPException(
            status_code=404,
            detail=f"Invalid model selected. {payload.model_name} does not exist.",
        )

    if perform_semantic_comparison is None:
        return ArticleComparisonResponse(missing_info=[], extra_info=[])

    request_data = {
        "article_text_blob_1": payload.text_a,
        "article_text_blob_2": payload.text_b,
        "article_text_blob_1_language": "en",
        "article_text_blob_2_language": "en",
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
            missing_info=[{"sentence": item, "index": -1} for item in missing_items],
            extra_info=[{"sentence": item, "index": -1} for item in extra_items],
        )

    return ArticleComparisonResponse(missing_info=[], extra_info=[])


@router.get("/wiki_translate/source_article", response_model=dict)
def translate_article(url: str = None, title: str = None, language: str = None):
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


@router.get("/translate_text", response_model=dict)
def translate_text_endpoint(
    source_language: str = Query(...),
    target_language: str = Query(...),
    text: str = Query(...),
):
    server = ServerModel()
    return {"response": server.text_translate(text, target_language)}
