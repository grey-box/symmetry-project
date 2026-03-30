"""
Configuration inspection endpoint.

Exposes current runtime threshold values so operators and the frontend
can verify which settings are active without restarting the server.
"""

from fastapi import APIRouter

from app.core import settings

router = APIRouter(prefix="/config", tags=["config"])


@router.get(
    "/thresholds",
    summary="Get current threshold configuration",
    description=(
        "Returns all configurable similarity and language-family thresholds "
        "currently active in the backend. Values reflect environment variables "
        "or the defaults defined in app/core/settings.py."
    ),
)
async def get_thresholds() -> dict:
    return {
        "similarity_threshold": settings.SIMILARITY_THRESHOLD,
        "levenshtein_disambiguation_margin": settings.LEVENSHTEIN_DISAMBIGUATION_MARGIN,
        "family_thresholds": {
            "same_family": settings.FAMILY_THRESHOLD_SAME,
            "ie_branches": settings.FAMILY_THRESHOLD_IE_BRANCHES,
            "unrelated": settings.FAMILY_THRESHOLD_UNRELATED,
            "unknown": settings.FAMILY_THRESHOLD_UNKNOWN,
        },
        "band_thresholds": {
            "same_family": {
                "very_close": settings.BAND_SAME_FAMILY[0],
                "same_branch": settings.BAND_SAME_FAMILY[1],
                "same_family_distant": settings.BAND_SAME_FAMILY[2],
                "unrelated": settings.BAND_SAME_FAMILY[3],
            },
            "ie_branches": {
                "very_close": settings.BAND_IE_BRANCHES[0],
                "same_branch": settings.BAND_IE_BRANCHES[1],
                "same_family_distant": settings.BAND_IE_BRANCHES[2],
                "unrelated": settings.BAND_IE_BRANCHES[3],
            },
            "different_families": {
                "very_close": settings.BAND_DIFFERENT_FAMILIES[0],
                "same_branch": settings.BAND_DIFFERENT_FAMILIES[1],
                "same_family_distant": settings.BAND_DIFFERENT_FAMILIES[2],
                "unrelated": settings.BAND_DIFFERENT_FAMILIES[3],
            },
            "unknown": {
                "very_close": settings.BAND_UNKNOWN[0],
                "same_branch": settings.BAND_UNKNOWN[1],
                "same_family_distant": settings.BAND_UNKNOWN[2],
                "unrelated": settings.BAND_UNKNOWN[3],
            },
        },
    }
