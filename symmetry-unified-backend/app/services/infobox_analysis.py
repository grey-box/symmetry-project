from bs4 import BeautifulSoup
from fastapi import HTTPException
from starlette import status
from app.models import InfoBoxResponse
from app.services.wiki_utils import page_exists
import requests


def analyze_infobox(page_title: str, language: str) -> InfoBoxResponse:
    if page_exists(page_title, language):
        api_url = f"https://{language}.wikipedia.org/w/api.php"
        params = {
            "action": "parse",
            "page": page_title,
            "format": "json",
            "prop": "text",
        }
        headers = {"User-Agent": "SymmetryUnified/1.0"}
        try:
            response = requests.get(api_url, params=params, headers=headers)
            response.raise_for_status()

            data_json = response.json()
            html = data_json["parse"]["text"]["*"]

            soup = BeautifulSoup(html, "html.parser")
            info_box = soup.find("table", {"class": "infobox"})

            if not info_box:
                return InfoBoxResponse(total_attributes=0, individual_infobox_data=[])

            result = []
            rows = info_box.find_all("tr")

            for row in rows:
                header = row.find("th")
                cell = row.find("td")
                if header and cell:
                    key = header.get_text(" ", strip=True)
                    value = cell.get_text(" ", strip=True)
                    result.append({"attribute": key, "value": value})

            return InfoBoxResponse(
                total_attributes=len(result), individual_infobox_data=result
            )

        except (ValueError, KeyError) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )

    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Page not found!"
        )
