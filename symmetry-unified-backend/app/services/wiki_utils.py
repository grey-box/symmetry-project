from datetime import datetime
from typing import Dict, List, Optional
from urllib.parse import urlparse, unquote

import httpx


# ---------------------------------------------------------------------------
# Sync URL / language helpers (used by routers and router_utils)
# ---------------------------------------------------------------------------


def parse_wikipedia_url(url: str) -> tuple[str, str]:
    """Parse a Wikipedia URL and return (lang, title). Raises ValueError on bad input."""
    parsed_url = urlparse(url)

    if not parsed_url.netloc.endswith(".wikipedia.org"):
        raise ValueError("Invalid domain - must be Wikipedia")

    parts = parsed_url.netloc.split(".")
    if len(parts) != 3:
        raise ValueError("Invalid URL format")

    lang = parts[0]
    if not lang.isalpha() or len(lang) > 2:
        raise ValueError("Invalid language code")

    if not parsed_url.path.startswith("/wiki/"):
        raise ValueError("Invalid article path")

    title = parsed_url.path[6:].replace("_", " ")

    if not title:
        raise ValueError("Empty article title")

    return lang, unquote(title)


def resolve_title_and_lang(query: str, default_lang: str) -> tuple[str, str]:
    """Extract Wikipedia title and language from a URL or plain title string."""
    if "://" in query:
        parsed = urlparse(query)
        if parsed and parsed.path.startswith("/wiki/"):
            lang = parsed.netloc.split(".")[0]
            title = unquote(parsed.path.split("/wiki/")[-1].replace("_", " "))
            return title, lang
        raise ValueError(f"Invalid Wikipedia URL: {query}")
    return query.replace("_", " "), default_lang


# Language validation cache
_language_cache: Dict[str, bool] = {}


def validate_language_code(language_code: str) -> bool:
    if language_code in _language_cache:
        return _language_cache[language_code]

    try:
        import pycountry

        VALID_LANGUAGE_CODES = {
            lang.alpha_2
            for lang in pycountry.languages
            if hasattr(lang, "alpha_2") and lang.alpha_2
        } | {
            lang.alpha_3
            for lang in pycountry.languages
            if hasattr(lang, "alpha_3") and lang.alpha_3
        }
    except Exception:
        VALID_LANGUAGE_CODES = set()

    is_valid = language_code in VALID_LANGUAGE_CODES
    _language_cache[language_code] = is_valid
    return is_valid


# ---------------------------------------------------------------------------
# Async Wikipedia API helpers
# ---------------------------------------------------------------------------


async def page_exists(title: str, source_language: str = "en") -> bool:
    api_url = f"https://{source_language}.wikipedia.org/w/api.php"
    params = {"action": "query", "page": title, "format": "json"}
    headers = {"User-Agent": "SymmetryUnified/1.0"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(api_url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
    pages = data.get("query", {}).get("pages", {})
    return "-1" not in pages


async def get_translation(
    source_title: str, source_language: str, target_language: str
) -> Optional[str]:
    url = f"https://{source_language}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": source_title,
        "prop": "langlinks",
        "lllimit": "500",
        "format": "json",
    }
    headers = {"User-Agent": "SymmetryUnified/1.0"}

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params, headers=headers)
        response.raise_for_status()
        data = response.json()
    pages = data.get("query", {}).get("pages", {})

    for page in pages.values():
        for link in page.get("langlinks", []):
            if link["lang"] == target_language:
                return link["*"]

    return None


async def get_latest_revision_timestamp(title: str, lang: str) -> Optional[datetime]:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvlimit": 1,
        "rvprop": "timestamp",
        "format": "json",
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(
            url, params=params, headers={"User-Agent": "SymmetryUnified/1.0"}
        )
        response.raise_for_status()
        data = response.json()
    pages = data.get("query", {}).get("pages", {})
    if not pages or "-1" in pages:
        return None
    page = next(iter(pages.values()))
    revisions = page.get("revisions", [])
    if not revisions:
        return None
    ts = revisions[0].get("timestamp", "")
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


async def detect_language_lag(
    title: str, source_lang: str, target_langs: List[str]
) -> "List[LagReport]":
    from app.models.revision import LagReport

    source_ts = await get_latest_revision_timestamp(title, source_lang)
    reports: List[LagReport] = []

    for lang in target_langs:
        translated_title = await get_translation(title, source_lang, lang)

        if translated_title is None:
            reports.append(
                LagReport(
                    lang=lang,
                    title=None,
                    source_last_updated=source_ts,
                    target_last_updated=None,
                    days_behind=None,
                    is_lagging=True,
                )
            )
            continue

        target_ts = await get_latest_revision_timestamp(translated_title, lang)

        if source_ts is None or target_ts is None:
            reports.append(
                LagReport(
                    lang=lang,
                    title=translated_title,
                    source_last_updated=source_ts,
                    target_last_updated=target_ts,
                    days_behind=None,
                    is_lagging=True,
                )
            )
            continue

        days_behind = (source_ts - target_ts).total_seconds() / 86400
        reports.append(
            LagReport(
                lang=lang,
                title=translated_title,
                source_last_updated=source_ts,
                target_last_updated=target_ts,
                days_behind=round(days_behind, 2),
                is_lagging=days_behind > 0,
            )
        )

    return reports
