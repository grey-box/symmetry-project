import logging
from urllib.parse import urlparse, unquote
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


def _extract_wiki_title(path: str) -> str:
    """Extract and normalize a Wikipedia title from a /wiki/... URL path."""
    if not path.startswith("/wiki/"):
        return ""

    title = path[len("/wiki/") :]
    title = title.split("#", 1)[0]
    title = title.split("?", 1)[0]
    title = unquote(title.replace("_", " ")).strip()
    return title


async def validate_url(url: str) -> tuple[str, str]:
    """Validate a Wikipedia URL and return (language, article title)."""
    parsed = urlparse(url)

    if not parsed.netloc.endswith(".wikipedia.org"):
        raise HTTPException(status_code=400, detail="URL must use a Wikipedia domain.")

    lang = parsed.netloc.split(".")[0]
    if not validate_language_code(lang):
        raise HTTPException(status_code=400, detail=f"Invalid language code '{lang}'.")

    title = _extract_wiki_title(parsed.path)
    if not title:
        raise HTTPException(status_code=400, detail="Invalid Wikipedia URL provided.")

    return lang, title


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
        lang, title = await validate_url(query)
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
