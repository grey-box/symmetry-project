from typing import Optional
import requests
from urllib.parse import urlparse, unquote


def parse_wikipedia_url(url: str) -> tuple[str, str]:
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
        title, lang = None, None
        parsed = urlparse(query)
        if parsed and parsed.path.startswith("/wiki/"):
            lang = parsed.netloc.split(".")[0]
            title = unquote(parsed.path.split("/wiki/")[-1].replace("_", " "))
            return title, lang
        raise ValueError(f"Invalid Wikipedia URL: {query}")
    return query, default_lang


# Language validation moved here to centralize checks across routers
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




def page_exists(title: str, source_language: str = "en") -> bool:
    api_url = f"https://{source_language}.wikipedia.org/w/api.php"
    params = {"action": "query", "page": title, "format": "json"}
    headers = {"User-Agent": "SymmetryUnified/1.0"}
    response = requests.get(api_url, params=params, headers=headers)
    data = response.json()
    pages = data.get("query", {}).get("pages", {})
    return "-1" not in pages


def get_translation(
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

    response = requests.get(url, params=params, headers=headers)
    data = response.json()
    pages = data.get("query", {}).get("pages", {})

    for page in pages.values():
        for link in page.get("langlinks", []):
            if link["lang"] == target_language:
                return link["*"]

    return None
