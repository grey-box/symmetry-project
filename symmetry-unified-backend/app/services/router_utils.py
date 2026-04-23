import logging
from fastapi import HTTPException

from app.services.wiki_utils import parse_wikipedia_url, resolve_title_and_lang
from app.services.article_parser import article_fetcher


async def resolve_and_fetch_article(query: str, default_lang: str = "en"):
    """Resolve a query (URL or title) to title/lang and fetch article with consistent errors."""
    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required.")

    if "://" in query:
        try:
            lang, title = parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title, lang = resolve_title_and_lang(query, default_lang)

    try:
        article = await asyncio.to_thread(article_fetcher, title, lang)
        return article
    except Exception as e:
        logging.exception("Failed to fetch article '%s' (%s): %s", title, lang, str(e))
        raise HTTPException(
            status_code=404,
            detail=f"Failed to fetch article '{title}' ({lang}): {e}",
        )
