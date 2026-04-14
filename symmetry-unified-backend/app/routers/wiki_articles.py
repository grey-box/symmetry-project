import logging
import asyncio
import urllib.request
from urllib.parse import urlparse, unquote
from urllib.error import URLError
from typing import Dict, Optional, Annotated

import wikipediaapi
import pycountry
from fastapi import APIRouter, Query, HTTPException, Request

from app.models.wiki.responses import SourceArticleResponse
from app.services.cache import get_cached_article, set_cached_article
from app.services.wiki_utils import parse_wikipedia_url, validate_language_code

router = APIRouter(prefix="/symmetry/v1/wiki", tags=["wiki"])

language_cache: Dict[str, bool] = {}

VALID_LANGUAGE_CODES = {
    lang.alpha_2
    for lang in pycountry.languages
    if hasattr(lang, "alpha_2") and lang.alpha_2
} | {
    lang.alpha_3
    for lang in pycountry.languages
    if hasattr(lang, "alpha_3") and lang.alpha_3
}


@router.get(
    "/articles",
    response_model=SourceArticleResponse,
    summary="Fetch Wikipedia Article",
    description="Retrieves a Wikipedia article by URL or title. Supports automatic language detection from URL or explicit language parameter. Returns article content and available translations.",
)
async def get_article(
    request: Request,
    query: Annotated[
        Optional[str],
        Query(
            description="Either a full Wikipedia URL (e.g., https://en.wikipedia.org/wiki/Python) or a keyword/title (e.g., 'Python')"
        ),
    ] = None,
    lang: Annotated[
        Optional[str],
        Query(
            description="Article language code (e.g., 'en', 'fr', 'es'). Defaults to 'en' if not provided"
        ),
    ] = None,
):
    logging.info("Calling get Wikipedia article endpoint (query='%s')", query)

    if not query:
        raise HTTPException(status_code=400, detail="Invalid Wikipedia URL provided.")

    title: Optional[str]

    if "://" in query:
        try:
            lang, title = parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid URL format provided.")
    else:
        title = query

    if not lang:
        lang = "en"

    if not validate_language_code(lang):
        raise HTTPException(status_code=400, detail=f"Invalid language code '{lang}'.")

    cached_content, cached_languages = get_cached_article(lang + "." + title)
    if cached_content:
        return {"sourceArticle": cached_content, "articleLanguages": cached_languages}

    wiki_wiki = wikipediaapi.Wikipedia(
        user_agent="SymmetryUnified/1.0 (contact@grey-box.ca)", language=lang
    )

    page = wiki_wiki.page(title)

    if not page.exists():
        raise HTTPException(status_code=404, detail="Article not found.")

    article_content = page.text
    languages = list(page.langlinks.keys()) if page.langlinks else []

    set_cached_article(lang + "." + title, article_content, languages)

    return {"sourceArticle": article_content, "articleLanguages": languages}


# validate_url, _extract_wiki_title and validate_language_code moved to app.services.wiki_utils
