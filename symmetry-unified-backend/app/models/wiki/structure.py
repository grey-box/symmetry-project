
from pydantic import BaseModel, Field


class Citation(BaseModel):
    model_config = {"frozen": True}
    label: str = Field()
    url: str | None = Field(default=None)


class Reference(BaseModel):
    model_config = {"frozen": True}
    label: str = Field(max_length=10000)
    id: str | None = Field(default=None, max_length=10000)
    url: str | None = Field(default=None, max_length=2000)

class WikiLink(BaseModel):
    """A link to another Wikipedia article found in a section's text."""

    # Title of the linked article as written in the link ("Picasso" may be a
    # redirect to "Pablo Picasso"; the Wikidata lookup follows redirects).
    title: str
    # The words shown in the text for this link.
    text: str
    # Character offset of `text` inside the section's clean_content.
    start: int = Field(ge=0)
    # Wikidata item id ("Q5593") once looked up, None if unknown.
    wikidata_id: str | None = None


class Section(BaseModel):
    title: str = Field()
    raw_content: str
    clean_content: str
    citations: list[Citation] | None = None
    citation_position: list[str] | None = None
    # Used internally for entity matching. Excluded from API responses so the
    # structured article endpoints keep their current shape.
    links: list[WikiLink] = Field(default_factory=list, exclude=True)


class Article(BaseModel):
    title: str = Field()
    lang: str = Field()
    source: str = Field()
    sections: list[Section]
    references: list[Reference]
    # Wikidata item of the article itself, once looked up. Internal only.
    wikidata_id: str | None = Field(default=None, exclude=True)
