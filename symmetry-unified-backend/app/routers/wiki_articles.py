import logging
import asyncio
import urllib.request
from urllib.parse import urlparse
from urllib.error import URLError
from typing import Dict, Optional, Annotated

import wikipediaapi
from fastapi import APIRouter, Query, HTTPException, Request

from app.models import SourceArticleResponse
from app.services.cache import get_cached_article, set_cached_article

router = APIRouter(prefix="/symmetry/v1/wiki", tags=["wiki"])

language_cache: Dict[str, bool] = {}


@router.get("/articles", response_model=SourceArticleResponse)
async def get_article(
    request: Request,
    query: Annotated[
        Optional[str],
        Query(description="Either a full Wikipedia URL or a keyword/title"),
    ] = None,
    lang: Annotated[Optional[str], Query(description="Article language code")] = None,
):
    logging.info("Calling get Wikipedia article endpoint (query='%s')", query)

    if not query:
        raise HTTPException(status_code=400, detail="Invalid Wikipedia URL provided.")

    title: Optional[str]

    if "://" in query:
        try:
            lang, title = await validate_url(query)
        except HTTPException as e:
            raise e
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid URL format provided.")
    else:
        title = query

    if not lang:
        lang = "en"

    await validate_language_code(lang)

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
    parsed_url = urlparse(url)

    if not parsed_url.netloc.endswith(".wikipedia.org"):
        logging.info("Invalid domain '%s'", parsed_url.netloc)
        raise HTTPException(
            status_code=400,
            detail="Invalid Wikipedia URL format: Not Wikipedia or no language subdomain.",
        )

    split_url = parsed_url.netloc.split(".")

    if len(split_url) != 3:
        logging.info("Invalid subdomain '%s'", parsed_url.netloc)
        raise HTTPException(
            status_code=400,
            detail="Invalid Wikipedia URL format: Incorrect subdomain format.",
        )

    lang = split_url[0]
    if not lang.isalpha() or len(lang) > 2:
        logging.info("Invalid language code '%s'", lang)
        raise HTTPException(status_code=400, detail="Invalid language code in URL.")

    await validate_language_code(lang)

    if not parsed_url.path.startswith("/wiki/"):
        logging.debug("Invalid wiki article path '%s'", parsed_url.path)
        raise HTTPException(
            status_code=400,
            detail="Invalid Wikipedia URL format: Invalid article path.",
        )

    title = _extract_wiki_title(parsed_url.path)

    if len(title) == 0:
        logging.debug("Empty wiki article title")
        raise HTTPException(
            status_code=400,
            detail="Invalid Wikipedia URL format: No article specified.",
        )

    return lang, title


def _extract_wiki_title(url: str) -> str:
    title = url[6:]

    for index, c in enumerate(title):
        if c == "#" or c == "?":
            title = title[0:index]
            break

    return title.replace("_", " ")


async def validate_language_code(language_code: str):
    if language_code in language_cache:
        logging.info(f"Using cached validation for language code: {language_code}")
        return language_cache[language_code]

    url = f"https://{language_code}.wikipedia.org/wiki/Main_Page"

    try:
        response = await asyncio.to_thread(urllib.request.urlopen, url)

        if response.status == 200:
            logging.info(f"Valid language code: {language_code}")
            language_cache[language_code] = True
            return True
        else:
            language_cache[language_code] = False
            raise HTTPException(
                status_code=400, detail=f"Invalid language code '{language_code}'."
            )

    except URLError:
        language_cache[language_code] = False
        raise HTTPException(
            status_code=400, detail=f"Invalid language code '{language_code}'."
        )
    except Exception as e:
        language_cache[language_code] = False
        raise HTTPException(
            status_code=500,
            detail=f"Error occurred during language code validation: {str(e)}",
        )
