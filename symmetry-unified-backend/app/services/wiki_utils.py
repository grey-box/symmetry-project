from datetime import datetime
from typing import List, Optional

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


def get_latest_revision_timestamp(title: str, lang: str) -> Optional[datetime]:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "query",
        "titles": title,
        "prop": "revisions",
        "rvlimit": 1,
        "rvprop": "timestamp",
        "format": "json",
    }
    response = requests.get(url, params=params, headers={"User-Agent": "SymmetryUnified/1.0"})
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


def detect_language_lag(
    title: str, source_lang: str, target_langs: List[str]
) -> "List[LagReport]":
    from app.models.revision import LagReport

    source_ts = get_latest_revision_timestamp(title, source_lang)
    reports: List[LagReport] = []

    for lang in target_langs:
        translated_title = get_translation(title, source_lang, lang)

        if translated_title is None:
            reports.append(LagReport(
                lang=lang,
                title=None,
                source_last_updated=source_ts,
                target_last_updated=None,
                days_behind=None,
                is_lagging=True,
            ))
            continue

        target_ts = get_latest_revision_timestamp(translated_title, lang)

        if source_ts is None or target_ts is None:
            reports.append(LagReport(
                lang=lang,
                title=translated_title,
                source_last_updated=source_ts,
                target_last_updated=target_ts,
                days_behind=None,
                is_lagging=True,
            ))
            continue

        days_behind = (source_ts - target_ts).total_seconds() / 86400
        reports.append(LagReport(
            lang=lang,
            title=translated_title,
            source_last_updated=source_ts,
            target_last_updated=target_ts,
            days_behind=round(days_behind, 2),
            is_lagging=days_behind > 0,
        ))

    return reports
