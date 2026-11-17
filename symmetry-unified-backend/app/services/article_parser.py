import asyncio
from urllib.parse import unquote

import requests
from bs4 import BeautifulSoup, Tag

from app.models.wiki.structure import Article, Citation, Reference, Section, WikiLink


def _link_title(href: str) -> str:
    """
    Article title from a "/wiki/..." link, or "" if it doesn't point to one.

    "/wiki/Pablo_Picasso#Early_life" becomes "Pablo Picasso".
    """
    if not href.startswith("/wiki/"):
        return ""
    title = href[len("/wiki/") :].split("#", 1)[0]
    return unquote(title).replace("_", " ").strip()


def _nested_links(element, text: str, start: int) -> list[WikiLink]:
    """
    Article links inside *element*, whose text was added at offset *start*.

    Each link's words are searched for in *text* from left to right, so a
    name that appears twice gets the offset of the right occurrence.
    """
    links: list[WikiLink] = []
    if not isinstance(element, Tag):
        # Plain text between tags has no links inside it.
        return links
    search_from = 0
    for anchor in element.find_all("a", href=True):
        link_title = _link_title(anchor["href"])
        anchor_text = anchor.get_text(strip=True)
        if not link_title or not anchor_text:
            continue
        found_at = text.find(anchor_text, search_from)
        if found_at == -1:
            continue
        links.append(
            WikiLink(title=link_title, text=anchor_text, start=start + found_at)
        )
        search_from = found_at + len(anchor_text)
    return links


def _fetch_wikipedia_json_sync(url: str, params: dict) -> dict:
    # Wikimedia's bot-mitigation blocks httpx's TLS/connection fingerprint with a 403
    # ("Please respect our robot policy") even with an identical User-Agent, so this
    # uses `requests` instead, which is not blocked.
    response = requests.get(
        url, params=params, headers={"User-Agent": "SymmetryUnified/1.0 (https://github.com/grey-box/symmetry-project; educational project)"}, timeout=10.0
    )
    response.raise_for_status()
    return response.json()


async def _fetch_wikipedia_json(url: str, params: dict) -> dict:
    return await asyncio.to_thread(_fetch_wikipedia_json_sync, url, params)


def _parse_article_html(html: str, title: str, lang: str, source: str) -> Article:
    """Parse rendered Wikipedia HTML into an Article object."""
    soup = BeautifulSoup(html, "html.parser")

    # Remove styling and executable content before extracting article text.
    # Wikipedia can place CSS inside article markup, which would otherwise
    # appear as normal paragraph text and pollute comparison results.
    for unwanted_tag in soup.find_all(["style", "script", "noscript"]):
        unwanted_tag.decompose()

    sections = []
    current_title = "Lead section"
    rich_current = ""
    clean_current = ""
    current_citations = []
    current_citation_positions = []
    current_links: list[WikiLink] = []

    def add_text(text: str) -> int:
        """Append *text* to the current section and return where it starts."""
        nonlocal clean_current, rich_current
        if clean_current.strip():
            clean_current += " "
            rich_current += " "
        start = len(clean_current)
        clean_current += text
        rich_current += text
        return start

    def finish_section() -> None:
        if not clean_current.strip():
            return
        # clean_content is stripped below, so move link offsets by however
        # much whitespace comes off the front (normally none).
        shift = len(clean_current) - len(clean_current.lstrip())
        sections.append(
            Section(
                title=current_title,
                raw_content=rich_current.strip(),
                clean_content=clean_current.strip(),
                citations=current_citations,
                citation_position=current_citation_positions,
                links=[
                    link.model_copy(update={"start": link.start - shift})
                    for link in current_links
                ],
            )
        )

    content_tags = soup.find_all(["h2", "h3", "p"])

    for tag in content_tags:
        if tag.name in ["h2", "h3"]:
            finish_section()

            current_title = tag.get_text(strip=True)
            rich_current = ""
            clean_current = ""
            current_citations = []
            current_citation_positions = []
            current_links = []

        elif tag.name == "p":
            # Preserve paragraph boundaries between separate <p> tags so that
            # _split_into_paragraphs() (section_comparison.py) can split on them
            # instead of falling back to a word-count chunker whose chunk count
            # varies by article length and rarely lines up across languages.
            if clean_current.strip():
                clean_current += "\n\n"
                rich_current += "\n\n"

            for element in tag.contents:
                if hasattr(element, "name"):
                    if (
                        element.name == "sup"
                        and element.has_attr("class")
                        and "reference" in element["class"]
                    ):
                        label = element.get_text(strip=True)
                        rich_current += f" {label}"
                        continue

                    elif element.name == "a" and element.get("href", "").startswith(
                        "/wiki/"
                    ):
                        text = element.get_text(strip=True)
                        position = len(clean_current.strip())

                        hyperlink = (
                            f"https://{lang}.wikipedia.org{element.get('href', '')}"
                        )
                        current_citations.append(Citation(label=text, url=hyperlink))
                        current_citation_positions.append(f"{text}:{position}")

                        start = add_text(text)
                        link_title = _link_title(element.get("href", ""))
                        if link_title and text:
                            current_links.append(
                                WikiLink(title=link_title, text=text, start=start)
                            )
                        continue

                    else:
                        text = element.get_text(strip=True)
                        if text:
                            start = add_text(text)
                            # Links wrapped in other tags, such as an italic
                            # title "<i><a>Guernica</a></i>" or bold text.
                            current_links.extend(_nested_links(element, text, start))

                else:
                    text = str(element).strip()
                    if text:
                        add_text(text)

    finish_section()

    full_references_data = []
    references_list = soup.select("ol.references > li")

    for ref in references_list:
        ref_id = ref.get("id", None)

        backlinks = ref.select("span.mw-cite-backlink")
        for bl in backlinks:
            bl.decompose()

        ref_text = ref.get_text(" ", strip=True)

        link_tag = ref.find("a", href=lambda href: href and href.startswith("http"))
        link = link_tag["href"] if link_tag else None

        reference = Reference(label=ref_text, id=ref_id, url=link)
        full_references_data.append(reference)

    return Article(
        title=title,
        lang=lang,
        source=source,
        sections=sections,
        references=full_references_data,
    )


async def article_fetcher(title: str, lang: str) -> Article:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "disableeditsection": True,
        "disabletoc": True,
    }
    data = await _fetch_wikipedia_json(url, params)
    html = data.get("parse", {}).get("text", {}).get("*", "")
    return _parse_article_html(html, title, lang, source="action_api")


async def revision_fetcher(revid: int, lang: str) -> Article:
    """Fetch a specific Wikipedia revision by ID and return a parsed Article."""
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "oldid": revid,
        "prop": "text",
        "format": "json",
        "disableeditsection": True,
        "disabletoc": True,
    }
    data = await _fetch_wikipedia_json(url, params)
    html = data.get("parse", {}).get("text", {}).get("*", "")
    title = data.get("parse", {}).get("title", f"revid:{revid}")
    return _parse_article_html(html, title, lang, source=f"revision:{revid}")
