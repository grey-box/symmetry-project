import requests
from bs4 import BeautifulSoup
from typing import List
from app.models import Citation, Reference, Section, Article


def article_fetcher(title: str, lang: str) -> Article:
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {
        "action": "parse",
        "page": title,
        "prop": "text",
        "format": "json",
        "disableeditsection": True,
        "disabletoc": True,
    }
    r = requests.get(url, params=params, headers={"User-Agent": "SymmetryUnified/1.0"})
    r.raise_for_status()
    data = r.json()

    html = data.get("parse", {}).get("text", {}).get("*", "")
    soup = BeautifulSoup(html, "html.parser")

    sections = []
    current_title = "Lead section"
    rich_current = ""
    clean_current = ""
    current_citations = []
    current_citation_positions = []

    content_tags = soup.find_all(["h2", "h3", "p"])

    for tag in content_tags:
        if tag.name in ["h2", "h3"]:
            if clean_current.strip():
                section = Section(
                    title=current_title,
                    raw_content=rich_current.strip(),
                    clean_content=clean_current.strip(),
                    citations=current_citations,
                    citation_position=current_citation_positions,
                )
                sections.append(section)

            current_title = tag.get_text(strip=True)
            rich_current = ""
            clean_current = ""
            current_citations = []
            current_citation_positions = []

        elif tag.name == "p":
            char_count = len(clean_current.strip())

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
                        position = char_count + 1 if char_count > 0 else char_count

                        hyperlink = (
                            f"https://{lang}.wikipedia.org{element.get('href', '')}"
                        )
                        current_citations.append(Citation(label=text, url=hyperlink))
                        current_citation_positions.append(f"{text}:{position}")

                        clean_current += " " + text
                        rich_current += " " + text
                        char_count += 1 + len(text)
                        continue

                    else:
                        text = element.get_text(strip=True)
                        if text:
                            clean_current += " " + text
                            rich_current += " " + text
                            char_count += 1 + len(text)

                else:
                    text = str(element).strip()
                    if text:
                        clean_current += " " + text
                        rich_current += " " + text
                        char_count += 1 + len(text)

    if clean_current.strip():
        section = Section(
            title=current_title,
            raw_content=rich_current.strip(),
            clean_content=clean_current.strip(),
            citations=current_citations,
            citation_position=current_citation_positions,
        )
        sections.append(section)

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
        source="action_api",
        sections=sections,
        references=full_references_data,
    )
