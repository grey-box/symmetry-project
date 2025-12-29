from fastapi import APIRouter, HTTPException, Path
from starlette import status
from app.models import (
    FinalAnalysisResponse,
    MultiLanguageScoreResponse,
    AnalysisResultsResponse,
)
from app.services import (
    table_analysis,
    header_analysis,
    infobox_analysis,
    citation_analysis,
    image_analysis,
    wiki_utils,
)
from pydantic import BaseModel, Field

router = APIRouter(
    prefix="/operations",
    tags=["Structural Analysis"],
)

LANGUAGES = {
    "en": "English",
    "es": "Spanish (Español)",
    "fr": "French (Français)",
    "de": "German (Deutsch)",
    "pt": "Portuguese (Português)",
    "ar": "Arabic (العربية)",
}


def calculate_single_score(article_response: FinalAnalysisResponse) -> float:
    total_tables = article_response.table_analysis.number_of_tables
    total_infobox_attrs = article_response.info_box.total_attributes
    total_citations = article_response.citations.total_citations
    total_headers = article_response.header_analysis.total_count
    total_images = article_response.total_images

    score = (
        (0.5 * total_citations)
        + (0.3 * total_tables)
        + (0.10 * total_infobox_attrs)
        + (0.05 * total_headers)
        + (0.05 * total_images)
    )
    return score


def analyze_single_article(title: str, language: str) -> FinalAnalysisResponse:
    try:
        table_analysis_data = table_analysis.analyze_tables(title, language)
        header_counter = header_analysis.count_html_headers(title, language)
        infobox_analysis_data = infobox_analysis.analyze_infobox(title, language)
        citation_analysis_data = citation_analysis.extract_citation_from_wikitext(
            title, language
        )
        image_count = image_analysis.get_image_count(title, language)

        return FinalAnalysisResponse(
            title=title,
            table_analysis=table_analysis_data,
            header_analysis=header_counter,
            info_box=infobox_analysis_data,
            citations=citation_analysis_data,
            total_images=image_count,
        )

    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Structural analysis error for {title} ({language}): {str(e)}",
        )


@router.get(
    "/{source_language}/{title}",
    status_code=status.HTTP_200_OK,
    response_model=AnalysisResultsResponse,
)
async def get_results(title: str, source_language: str = Path(min_length=1)):
    """
    Analyzes the structural quality score for the given article across all 6 supported languages.
    """

    all_scores = []
    normalized_title = title.replace(" ", "_")
    target_languages = list(LANGUAGES.keys())

    for lang_code in target_languages:
        current_title = ""

        if lang_code == source_language:
            current_title = normalized_title
        else:
            current_title = wiki_utils.get_translation(
                normalized_title, source_language, lang_code
            )

        if not current_title:
            all_scores.append(
                {
                    "lang_code": lang_code,
                    "lang_name": LANGUAGES[lang_code],
                    "title": None,
                    "score": -1,
                    "is_user_language": lang_code == source_language,
                    "is_authority_article": False,
                    "error": "Translation or article not available.",
                }
            )
            continue

        try:
            article_response = analyze_single_article(current_title, lang_code)
            score = calculate_single_score(article_response)

            all_scores.append(
                {
                    "lang_code": lang_code,
                    "lang_name": LANGUAGES[lang_code],
                    "title": current_title,
                    "score": round(score, 3),
                    "is_user_language": lang_code == source_language,
                    "is_authority_article": False,
                }
            )

        except HTTPException as e:
            all_scores.append(
                {
                    "lang_code": lang_code,
                    "lang_name": LANGUAGES[lang_code],
                    "title": current_title,
                    "score": -1,
                    "is_user_language": lang_code == source_language,
                    "is_authority_article": False,
                    "error": e.detail,
                }
            )
        except Exception as e:
            all_scores.append(
                {
                    "lang_code": lang_code,
                    "lang_name": LANGUAGES[lang_code],
                    "title": current_title,
                    "score": -1,
                    "is_user_language": lang_code == source_language,
                    "is_authority_article": False,
                    "error": f"Internal Error during analysis: {str(e)}",
                }
            )
    valid_scores = [d["score"] for d in all_scores if d.get("score", -1) >= 0]
    max_score = max(valid_scores) if valid_scores else -float("inf")

    for item in all_scores:
        is_authority = (item.get("score", -1) >= 0) and (item.get("score") == max_score)
        item["is_authority_article"] = is_authority
    sorted_scores = sorted(
        all_scores, key=lambda x: x.get("score", -float("inf")), reverse=True
    )

    return AnalysisResultsResponse(
        article=title.replace("_", " "),
        source_language_code=source_language,
        scores_by_language=sorted_scores,
    )
