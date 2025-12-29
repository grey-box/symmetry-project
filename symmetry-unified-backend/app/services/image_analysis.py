import requests
from fastapi import HTTPException
from starlette import status


def get_image_count(page_title: str, language: str) -> int:
    API_URL = f"https://{language}.wikipedia.org/w/api.php"

    params = {
        "action": "query",
        "titles": page_title,
        "prop": "images",
        "imlimit": "max",
        "format": "json",
    }

    headers = {"User-Agent": "SymmetryUnified/1.0"}

    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        pages = data.get("query", {}).get("pages", {})

        page_id = next(iter(pages))
        page_data = pages.get(page_id, {})

        if page_id == "-1" or "missing" in page_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page '{page_title}' not found in {language} Wikipedia.",
            )

        images = page_data.get("images", [])
        return len(images)

    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"API request failed: {e}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {e}",
        )
