import re
from typing import List, Optional

import requests

from app.models.revision import Revision
from app.services.revision_store import (
    load_revision_snapshot,
    save_revision_snapshot,
)

USER_AGENT = "SymmetryUnified/1.0"


def clean_revision_content(content: Optional[str]) -> str:
    if not content:
        return ""

    content = re.sub(r"\{\{.*?\}\}", "", content, flags=re.DOTALL)
    content = re.sub(r"<!--.*?-->", "", content, flags=re.DOTALL)
    content = re.sub(r"\[\[File:.*?\]\]", "", content, flags=re.DOTALL)
    content = re.sub(r"\[\[|\]\]", "", content)
    content = re.sub(r"\s+", " ", content)

    return content.strip()


def revision_fetcher(title: str, lang: str, limit: int = 10) -> List[Revision]:
    url = f"https://{lang}.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "prop": "revisions",
        "titles": title,
        "rvlimit": limit,
        "rvprop": "ids|timestamp|user|comment|content",
        "rvslots": "main",
        "format": "json",
        "formatversion": 2,
    }

    response = requests.get(url, params=params, headers={"User-Agent": USER_AGENT})
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", [])
    if not pages:
        return []

    revisions_data = pages[0].get("revisions", [])
    revisions: List[Revision] = []

    for rev in revisions_data:
        revid = rev.get("revid")

        cached = load_revision_snapshot(title, lang, revid)
        if cached:
            revisions.append(cached)
            continue

        content: Optional[str] = None

        slots = rev.get("slots", {})
        if isinstance(slots, dict) and "main" in slots:
            content = slots["main"].get("content")

        if content is None:
            content = rev.get("*")

        cleaned_content = clean_revision_content(content)

        revision = Revision(
            revid=revid,
            parentid=rev.get("parentid"),
            timestamp=rev.get("timestamp"),
            user=rev.get("user"),
            comment=rev.get("comment"),
            content=cleaned_content,
            sections=None,
        )

        save_revision_snapshot(title, lang, revision)
        revisions.append(revision)

    return revisions


def compare_revisions(rev1: Revision, rev2: Revision) -> dict:
    text1 = rev1.content or ""
    text2 = rev2.content or ""

    words1 = set(text1.split())
    words2 = set(text2.split())

    added = words2 - words1
    removed = words1 - words2

    return {
        "revid_1": rev1.revid,
        "revid_2": rev2.revid,
        "added_words": list(added)[:20],
        "removed_words": list(removed)[:20],
    }