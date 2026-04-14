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


async def validate_url(url: str) -> tuple[str, str]:
    """Validate a Wikipedia URL and return (lang, title).

    Raises HTTPException on invalid input so callers can use it directly
    in request handling. This is a compatibility wrapper: core logic lives
    in `app.services.wiki_utils.parse_wikipedia_url`.
    """
    try:
        # run the sync parser off the event loop to avoid blocking
        lang, title = await asyncio.to_thread(parse_wikipedia_url, url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not validate_language_code(lang):
        raise HTTPException(status_code=400, detail="Language code invalid")

    return lang, title


def _extract_wiki_title(path: str) -> str:
    """Extract a human-friendly title from a /wiki/... path or URL path.

    Examples:
    - /wiki/Test_Article?action=edit -> "Test Article"
    - /wiki/Test_Article#Section -> "Test Article"
    """
    if not path:
        return ""

    # If a full URL was provided, take the path portion
    try:
        parsed = urlparse(path)
        path_part = parsed.path or path
    except Exception:
        path_part = path

    if path_part.startswith("/wiki/"):
        title_part = path_part[len("/wiki/") :]
    else:
        title_part = path_part

    # strip fragment and query
    title_part = title_part.split("#")[0].split("?")[0]

    return unquote(title_part.replace("_", " "))


# validate_url and _extract_wiki_title moved from previous location into this
# router as compatibility wrappers around app.services.wiki_utils
