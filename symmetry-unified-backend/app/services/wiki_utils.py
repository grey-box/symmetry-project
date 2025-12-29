from typing import Optional
import requests


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
