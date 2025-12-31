import logging
from typing import Dict, Optional, List
from urllib.parse import urlparse

from fastapi import APIRouter, Query, HTTPException

from app.models import (
    StructuredArticleResponse,
    StructuredSectionResponse,
    StructuredCitationResponse,
    StructuredReferenceResponse,
)
from app.services.article_parser import article_fetcher

router = APIRouter(prefix="/symmetry/v1/wiki", tags=["structured-wiki"])

structured_cache: Dict[str, Dict] = {}


@router.get(
    "/structured-article",
    response_model=StructuredArticleResponse,
    summary="Get Structured Wikipedia Article",
    description="Parses a Wikipedia article into structured data including sections, citations, and references. Provides metadata like section counts and citation statistics.",
)
async def get_structured_article(
    query: Optional[str] = Query(
        None,
        description="Either a full Wikipedia URL (e.g., https://en.wikipedia.org/wiki/Python) or a keyword/title (e.g., 'Python')",
    ),
    lang: Optional[str] = Query(
        None,
        description="Article language code (e.g., 'en', 'fr', 'es'). Defaults to 'en' if not provided",
    ),
):
    logging.info(
        "Calling structured article endpoint (query='%s', lang='%s')", query, lang
    )

    if not query:
        raise HTTPException(status_code=400, detail="Query parameter is required.")

    if "://" in query:
        try:
            lang, title = await parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title = query
        if not lang:
            lang = "en"

    cache_key = f"{lang}.{title}"
    if cache_key in structured_cache:
        logging.info("Returning cached structured article: %s", cache_key)
        return structured_cache[cache_key]

    try:
        article = article_fetcher(title, lang)

        total_citations = sum(
            len(section.citations or []) for section in article.sections
        )
        total_references = len(article.references)

        response = StructuredArticleResponse(
            title=article.title,
            lang=article.lang,
            source=article.source,
            sections=article.sections,
            references=article.references,
            total_sections=len(article.sections),
            total_citations=total_citations,
            total_references=total_references,
        )

        structured_cache[cache_key] = response

        logging.info(
            "Successfully parsed structured article: %s (%d sections, %d citations)",
            title,
            len(article.sections),
            total_citations,
        )

        return response

    except Exception as e:
        logging.error("Error parsing structured article '%s': %s", title, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to parse article: {str(e)}"
        )


@router.get(
    "/structured-section",
    response_model=StructuredSectionResponse,
    summary="Get Specific Article Section",
    description="Retrieves a specific section from a Wikipedia article with metadata including word count, citation count, and citation positions.",
)
async def get_structured_section(
    query: str = Query(
        ...,
        description="Wikipedia article title or URL (e.g., 'Python' or https://en.wikipedia.org/wiki/Python)",
    ),
    lang: Optional[str] = Query(
        None,
        description="Article language code (e.g., 'en', 'fr', 'es'). Defaults to 'en' if not provided",
    ),
    section_title: str = Query(
        ...,
        description="Title of the specific section to retrieve (e.g., 'History', 'Uses')",
    ),
):
    logging.info(
        "Calling structured section endpoint (query='%s', section='%s')",
        query,
        section_title,
    )

    if "://" in query:
        try:
            lang, title = await parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title = query
        if not lang:
            lang = "en"

    try:
        article = article_fetcher(title, lang)

        target_section = None
        for section in article.sections:
            if section.title.lower() == section_title.lower():
                target_section = section
                break

        if not target_section:
            raise HTTPException(
                status_code=404, detail=f"Section '{section_title}' not found."
            )

        word_count = len(target_section.clean_content.split())
        citation_count = len(target_section.citations or [])

        response = StructuredSectionResponse(
            title=target_section.title,
            raw_content=target_section.raw_content,
            clean_content=target_section.clean_content,
            citations=target_section.citations,
            citation_position=target_section.citation_position,
            word_count=word_count,
            citation_count=citation_count,
        )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logging.error(
            "Error parsing section '%s' from article '%s': %s",
            section_title,
            title,
            str(e),
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to parse section: {str(e)}"
        )


@router.get(
    "/citation-analysis",
    response_model=StructuredCitationResponse,
    summary="Analyze Article Citations",
    description="Provides detailed analysis of all citations in a Wikipedia article, including total citations, unique citation targets, and most cited articles.",
)
async def get_citation_analysis(
    query: str = Query(
        ...,
        description="Wikipedia article title or URL (e.g., 'Python' or https://en.wikipedia.org/wiki/Python)",
    ),
    lang: Optional[str] = Query(
        None,
        description="Article language code (e.g., 'en', 'fr', 'es'). Defaults to 'en' if not provided",
    ),
):
    logging.info("Calling citation analysis endpoint (query='%s')", query)

    if "://" in query:
        try:
            lang, title = await parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title = query
        if not lang:
            lang = "en"

    try:
        article = article_fetcher(title, lang)

        all_citations = []
        for section in article.sections:
            if section.citations:
                all_citations.extend(section.citations)

        total_citations = len(all_citations)
        unique_targets = len(set(cit.url for cit in all_citations if cit.url))

        citation_counts = {}
        for citation in all_citations:
            if citation.url:
                citation_counts[citation.url] = citation_counts.get(citation.url, 0) + 1

        url_to_title = {cit.url: cit.label for cit in all_citations if cit.url}
        most_cited = [
            {"title": url_to_title.get(url, "Unknown"), "count": count}
            for url, count in sorted(
                citation_counts.items(), key=lambda x: x[1], reverse=True
            )[:10]
        ]

        response = StructuredCitationResponse(
            citations=all_citations,
            total_citations=total_citations,
            unique_targets=unique_targets,
            most_cited_articles=most_cited,
        )

        return response

    except Exception as e:
        logging.error("Error analyzing citations for '%s': %s", title, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze citations: {str(e)}"
        )


@router.get(
    "/reference-analysis",
    response_model=StructuredReferenceResponse,
    summary="Analyze Article References",
    description="Analyzes reference statistics for a Wikipedia article, including total references, references with URLs, and reference density (references per 1000 words).",
)
async def get_reference_analysis(
    query: str = Query(
        ...,
        description="Wikipedia article title or URL (e.g., 'Python' or https://en.wikipedia.org/wiki/Python)",
    ),
    lang: Optional[str] = Query(
        None,
        description="Article language code (e.g., 'en', 'fr', 'es'). Defaults to 'en' if not provided",
    ),
):
    logging.info("Calling reference analysis endpoint (query='%s')", query)

    if "://" in query:
        try:
            lang, title = await parse_wikipedia_url(query)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Wikipedia URL format.")
    else:
        title = query
        if not lang:
            lang = "en"

    try:
        article = article_fetcher(title, lang)

        total_references = len(article.references)
        references_with_urls = sum(1 for ref in article.references if ref.url)

        total_words = sum(
            len(section.clean_content.split()) for section in article.sections
        )
        reference_density = (
            (total_references / total_words * 1000) if total_words > 0 else 0
        )

        response = StructuredReferenceResponse(
            references=article.references,
            total_references=total_references,
            references_with_urls=references_with_urls,
            reference_density=round(reference_density, 2),
        )

        return response

    except Exception as e:
        logging.error("Error analyzing references for '%s': %s", title, str(e))
        raise HTTPException(
            status_code=500, detail=f"Failed to analyze references: {str(e)}"
        )


async def parse_wikipedia_url(url: str) -> tuple[str, str]:
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

    return lang, title
