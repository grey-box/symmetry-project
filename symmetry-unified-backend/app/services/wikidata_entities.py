"""
Wikidata ids for the links in a Wikipedia article.

Every Wikipedia article is tied to one Wikidata item, and that item is the
same in every language: "Germany" on en.wikipedia and "Alemania" on
es.wikipedia are both Q183.  The links in a paragraph therefore say which
people, places and things it mentions in a way that doesn't depend on
spelling or script.  keyword_proximity uses this to stop flagging a name as
missing when the other article links the same item under another name.

Lookups go to the MediaWiki API of the article's own language
(prop=pageprops&ppprop=wikibase_item), following redirects so "Picasso" and
"Pablo Picasso" give the same id.  One query lists the ids of up to 500 pages
an article links to (generator=links), so a long article such as en "Pablo
Picasso" (about 900 links) needs 2 or 3 requests.  Any titles that query
missed are then looked up 50 at a time.  Wikimedia answers bursts of
requests with 429 Too Many Requests, which is why the batch lookup is not
the first choice.  Results are cached for the life of the process.
"""

import asyncio
import logging
import re
import time

import requests

from app.models.wiki.structure import Article, Section, WikiLink
from app.services.keyword_proximity import (
    _MIN_KEYWORD_LENGTH,
    ParagraphEntities,
    _fold,
    _normalise,
)

logger = logging.getLogger(__name__)

# The API accepts at most 50 titles per query for normal clients.
_TITLES_PER_REQUEST = 50

# Most continuation requests made when listing an article's links (500
# links each).  The longest articles have a few thousand links.
_MAX_LINK_LIST_REQUESTS = 10

# Most 50-title requests made per article for titles the link list missed.
# Keeps a comparison from stalling when Wikimedia starts rate limiting.
_MAX_TITLE_REQUESTS_PER_ARTICLE = 4

# How often a request is retried after 429 / 503, and the longest wait.
_RETRIES = 2
_MAX_RETRY_WAIT_SECONDS = 5.0

# Longest name, in words, that is searched for in paragraph text.
_MAX_NAME_WORDS = 8

# Main (article) namespace.  Links to files, help pages and categories also
# have Wikidata items, but they aren't things a paragraph talks about.
_ARTICLE_NAMESPACE = 0

# (language, title) -> Wikidata id, or None when the page has no item.
# Cleared when it grows past _CACHE_LIMIT so a long session can't fill memory.
_wikidata_id_cache: dict[tuple[str, str], str | None] = {}
_CACHE_LIMIT = 200_000

# "Mercury (planet)" -> "Mercury".  The bracketed part is how Wikipedia
# tells apart pages with the same name; it never appears in running text.
_DISAMBIGUATION_RE = re.compile(r"\s*\([^)]*\)\s*$")


def _post_query_sync(lang: str, params: dict) -> dict:
    """
    Send one action=query request for Wikidata ids, retrying when rate limited.

    POST keeps 50 long non-Latin titles from making the URL too long.
    requests, not httpx: see the note in article_parser.py about 403s.
    """
    data = {
        "action": "query",
        "prop": "pageprops",
        "ppprop": "wikibase_item",
        "redirects": 1,
        "format": "json",
        "formatversion": 2,
        **params,
    }
    for attempt in range(_RETRIES + 1):
        response = requests.post(
            f"https://{lang}.wikipedia.org/w/api.php",
            data=data,
            headers={"User-Agent": "SymmetryUnified/1.0"},
            timeout=10.0,
        )
        if response.status_code in (429, 503) and attempt < _RETRIES:
            time.sleep(_retry_wait(response, attempt))
            continue
        response.raise_for_status()
        return response.json()
    raise RuntimeError("unreachable")


def _retry_wait(response: requests.Response, attempt: int) -> float:
    """Seconds to wait before retrying: Retry-After if given, else 1, 2, ..."""
    try:
        wait = float(response.headers.get("Retry-After", ""))
    except ValueError:
        wait = float(attempt + 1)
    return min(max(wait, 0.0), _MAX_RETRY_WAIT_SECONDS)


def _page_ids(pages: list[dict]) -> dict[str, str | None]:
    """Page title -> Wikidata id for the pages in an API response."""
    ids: dict[str, str | None] = {}
    for page in pages:
        if page.get("ns") != _ARTICLE_NAMESPACE:
            entity_id = None
        else:
            entity_id = page.get("pageprops", {}).get("wikibase_item")
        ids[page.get("title", "")] = entity_id
    return ids


def _ids_from_response(titles: list[str], data: dict) -> dict[str, str | None]:
    """
    Map each requested title to its Wikidata id using one API response.

    The API answers under the final page title, so each requested title is
    followed through the "normalized" step (first letter upper-cased,
    underscores to spaces) and then the "redirects" step.
    """
    query = data.get("query", {})
    renamed = {entry["from"]: entry["to"] for entry in query.get("normalized", [])}
    redirected = {entry["from"]: entry["to"] for entry in query.get("redirects", [])}

    id_by_page_title = _page_ids(query.get("pages", []))

    result: dict[str, str | None] = {}
    for title in titles:
        final_title = renamed.get(title, title)
        final_title = redirected.get(final_title, final_title)
        result[title] = id_by_page_title.get(final_title)
    return result


async def lookup_wikidata_ids(
    titles: list[str], lang: str, max_requests: int | None = None
) -> dict[str, str | None]:
    """
    Wikidata id for each Wikipedia title in *lang*, None when it has none.

    Uncached titles are sent in batches of 50, one request at a time to stay
    polite to the Wikimedia API, and at most *max_requests* batches when
    given.  A failed or skipped batch is logged and left out of the result
    (and the cache), so callers just see fewer ids.
    """
    unique_titles = list(dict.fromkeys(t for t in titles if t))
    missing = [t for t in unique_titles if (lang, t) not in _wikidata_id_cache]

    if len(_wikidata_id_cache) + len(missing) > _CACHE_LIMIT:
        _wikidata_id_cache.clear()
        missing = unique_titles

    if max_requests is not None and len(missing) > max_requests * _TITLES_PER_REQUEST:
        logger.info(
            "Looking up %d of %d %s titles without Wikidata ids",
            max_requests * _TITLES_PER_REQUEST,
            len(missing),
            lang,
        )
        missing = missing[: max_requests * _TITLES_PER_REQUEST]

    for batch_start in range(0, len(missing), _TITLES_PER_REQUEST):
        batch = missing[batch_start : batch_start + _TITLES_PER_REQUEST]
        try:
            data = await asyncio.to_thread(
                _post_query_sync, lang, {"titles": "|".join(batch)}
            )
        except Exception as exc:
            logger.warning(
                "Wikidata id lookup failed for %d %s titles: %s", len(batch), lang, exc
            )
            continue
        for title, entity_id in _ids_from_response(batch, data).items():
            _wikidata_id_cache[(lang, title)] = entity_id

    return {
        t: _wikidata_id_cache[(lang, t)]
        for t in unique_titles
        if (lang, t) in _wikidata_id_cache
    }


async def _cache_linked_page_ids(article_title: str, lang: str) -> None:
    """
    Cache the Wikidata ids of every article *article_title* links to.

    Uses generator=links, which returns up to 500 linked pages per request
    along with the redirects that lead to them, so this is far fewer
    requests than looking the titles up 50 at a time.  Links to files, help
    pages and the like are listed too so they get cached as having no id
    instead of being looked up again one batch at a time.
    """
    params = {
        "generator": "links",
        "titles": article_title,
        "gpllimit": "max",
    }
    pages: list[dict] = []
    redirects: dict[str, str] = {}

    for _ in range(_MAX_LINK_LIST_REQUESTS):
        try:
            data = await asyncio.to_thread(_post_query_sync, lang, params)
        except Exception as exc:
            logger.warning(
                "Listing linked pages of %s:%s failed: %s", lang, article_title, exc
            )
            break
        query = data.get("query", {})
        pages.extend(query.get("pages", []))
        for entry in query.get("redirects", []):
            redirects[entry["from"]] = entry["to"]
        if "continue" not in data:
            break
        params = {**params, **data["continue"]}

    id_by_page_title = _page_ids(pages)
    if len(_wikidata_id_cache) + len(id_by_page_title) > _CACHE_LIMIT:
        _wikidata_id_cache.clear()
    for title, entity_id in id_by_page_title.items():
        _wikidata_id_cache[(lang, title)] = entity_id
    for source, target in redirects.items():
        if target in id_by_page_title:
            _wikidata_id_cache[(lang, source)] = id_by_page_title[target]


async def attach_wikidata_ids(article: Article) -> None:
    """Fill in wikidata_id on every link in *article*, where one exists."""
    titles = [link.title for section in article.sections for link in section.links]
    if not titles:
        return
    if any((article.lang, t) not in _wikidata_id_cache for t in titles):
        await _cache_linked_page_ids(article.title, article.lang)
    # Picks up the article's own id and anything the link list missed (all
    # cache hits otherwise).  The article never links to itself, but its
    # subject is named all through the text ("Moscow" in "Moscow").
    ids = await lookup_wikidata_ids(
        [article.title, *titles],
        article.lang,
        max_requests=_MAX_TITLE_REQUESTS_PER_ARTICLE,
    )
    article.wikidata_id = ids.get(article.title)
    for section in article.sections:
        section.links = [
            link.model_copy(update={"wikidata_id": ids.get(link.title)})
            for link in section.links
        ]


def has_wikidata_ids(article: Article) -> bool:
    return any(link.wikidata_id for s in article.sections for link in s.links)


def _name_key(text: str) -> str:
    """The form names are compared in: normalised, accents removed."""
    return _fold(_normalise(text))


def _names_for_link(link: WikiLink) -> list[str]:
    """
    Names a link's item can go by in the text: the linked words and the
    article title without its bracketed part.
    """
    names = [_name_key(link.text), _name_key(_DISAMBIGUATION_RE.sub("", link.title))]
    return [n for n in names if len(n.replace(" ", "")) >= _MIN_KEYWORD_LENGTH]


def _names_to_ids(links: list[WikiLink]) -> dict[str, str]:
    """
    Map names to ids for *links*, leaving out names that point to more than
    one item ("Barcelona" linked to the city in one place and the football
    club in another), since there is no way to tell which one is meant.
    """
    ids_for_name: dict[str, set[str]] = {}
    for link in links:
        if not link.wikidata_id:
            continue
        for name in _names_for_link(link):
            ids_for_name.setdefault(name, set()).add(link.wikidata_id)
    return {name: ids.pop() for name, ids in ids_for_name.items() if len(ids) == 1}


def article_entity_names(article: Article) -> dict[str, str]:
    """Name -> Wikidata id for every link in the article and its own title."""
    links = [link for s in article.sections for link in s.links]
    if article.wikidata_id:
        links.append(
            WikiLink(
                title=article.title,
                text=article.title,
                start=0,
                wikidata_id=article.wikidata_id,
            )
        )
    return _names_to_ids(links)


def _phrases_in(text: str) -> set[str]:
    """Every run of 1 to _MAX_NAME_WORDS consecutive words in *text*."""
    words = _name_key(text).split()
    phrases: set[str] = set()
    for start in range(len(words)):
        for length in range(1, _MAX_NAME_WORDS + 1):
            if start + length > len(words):
                break
            phrases.add(" ".join(words[start : start + length]))
    return phrases


def paragraph_entities(
    section: Section,
    start: int,
    end: int,
    text: str,
    article_names: dict[str, str],
) -> ParagraphEntities:
    """
    Entities for the paragraph covering clean_content[start:end] of *section*.

    Wikipedia links a name only the first time it appears, so later
    paragraphs that mention "Picasso" usually have no link.  Names linked
    anywhere in the article are therefore also looked for in *text*.
    """
    own_links = [
        link for link in section.links if link.wikidata_id and start <= link.start < end
    ]
    own_names = _names_to_ids(own_links)

    ids = {link.wikidata_id for link in own_links if link.wikidata_id}
    for phrase in _phrases_in(text):
        entity_id = own_names.get(phrase) or article_names.get(phrase)
        if entity_id:
            ids.add(entity_id)

    return ParagraphEntities(
        names={**article_names, **own_names},
        ids=frozenset(ids),
    )
