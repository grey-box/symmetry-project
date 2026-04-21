from typing import List
import logging

from app.models.wiki.structure import Section
from app.models.wiki.responses import StructuredArticleResponse
from app.ai.translation import translate


def translate_article(
    article, source_lang: str, target_lang: str
) -> StructuredArticleResponse:
    """
    Translates an Article object and builds a StructuredArticleResponse.
    """

    translated_sections: List[Section] = []

    for section in article.sections:
        translated_sections.append(
            Section(
                title=translate(section.title, source_lang, target_lang),
                raw_content=translate(section.raw_content, source_lang, target_lang),
                clean_content=translate(
                    section.clean_content, source_lang, target_lang
                ),
                citations=section.citations,
                citation_position=section.citation_position,
            )
        )

    total_citations = sum(
        len(section.citations or []) for section in translated_sections
    )

    return StructuredArticleResponse(
        title=translate(article.title, source_lang, target_lang),
        lang=target_lang,
        source=f"wikipedia+model({source_lang}->{target_lang})",
        sections=translated_sections,
        references=article.references,
        total_sections=len(translated_sections),
        total_citations=total_citations,
        total_references=len(article.references),
    )
