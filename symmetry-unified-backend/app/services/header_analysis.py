from bs4 import BeautifulSoup
from fastapi import HTTPException
from starlette import status
from app.models import HeaderCount
from app.services.wiki_utils import page_exists
import requests


def count_html_headers(page_title: str, target_language: str) -> HeaderCount:
    if page_exists(page_title, target_language):
        api_url = f"https://{target_language}.wikipedia.org/w/api.php"
        params = {
            "action": "parse",
            "page": page_title,
            "format": "json",
            "prop": "text",
        }
        headers = {"User-Agent": "SymmetryUnified/1.0"}

        header_dict = {
            "h1": 0,
            "h2": 0,
            "h3": 0,
            "h4": 0,
            "h5": 0,
            "h6": 0,
        }

        try:
            response = requests.get(api_url, headers=headers, params=params)
            response.raise_for_status()

            data = response.json()

            if "error" in data:
                error_message = data["error"].get("info", "Unknown API error")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail=error_message
                )
            else:
                html_headers = data["parse"]["text"]["*"]
                soup = BeautifulSoup(html_headers, "html.parser")

                header_tags = ("h1", "h2", "h3", "h4", "h5", "h6")
                total_count = 0

                for tag in header_tags:
                    count = len(soup.find_all(tag))
                    header_dict[tag] = count
                    total_count += count

                return HeaderCount(
                    total_count=total_count,
                    h1_count=header_dict["h1"],
                    h2_count=header_dict["h2"],
                    h3_count=header_dict["h3"],
                    h4_count=header_dict["h4"],
                    h5_count=header_dict["h5"],
                    h6_count=header_dict["h6"],
                )
        except requests.exceptions.RequestException as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
        except (KeyError, ValueError) as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="The page does not exist!"
        )
