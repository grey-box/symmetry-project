from fastapi import HTTPException
from starlette import status
from bs4 import BeautifulSoup
import requests
from app.models import TableResponse
from app.services.wiki_utils import page_exists


def analyze_tables(page_title: str, target_language: str) -> TableResponse:
    if page_exists(page_title, target_language):
        api_url = f"https://{target_language}.wikipedia.org/w/api.php"

        params = {
            "action": "parse",
            "page": page_title,
            "format": "json",
            "prop": "text",
        }

        headers = {"User-Agent": "SymmetryUnified/1.0"}
        try:
            response = requests.get(api_url, params=params, headers=headers, timeout=10)
            response.raise_for_status()

            data = response.json()
            html = data["parse"]["text"]["*"]

            soup = BeautifulSoup(html, "html.parser")
            tables = soup.find_all("table")
            results = []

            for index, table in enumerate(tables):
                rows = table.find_all("tr")
                row_count = len(rows)
                column_count = 0
                for row in rows:
                    cells = row.find_all(["td", "th"])
                    if len(cells) > 0:
                        column_count = len(cells)
                        break
                results.append(
                    {"Index": index + 1, "Rows": row_count, "Columns": column_count}
                )

            return TableResponse(
                number_of_tables=len(results),
                individual_table_information=results,
                language=target_language,
            )

        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
            )
        except (KeyError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Page not found in language"
        )
