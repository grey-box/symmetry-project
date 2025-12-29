from pydantic import BaseModel, Field, computed_field
from typing import List, Optional


class TableInfo(BaseModel):
    table_index: int = Field(ge=0)
    number_of_rows: int = Field(ge=0)
    number_of_columns: int = Field(ge=0)


class TableResponse(BaseModel):
    number_of_tables: int = Field(description="Number of tables in the article", ge=0)
    individual_table_information: List[TableInfo] = Field(
        description="Individual table information"
    )
    language: str = Field(description="Article language", min_length=1, max_length=10)


class HeaderCount(BaseModel):
    h1_count: int = Field(ge=0, description="Header 1's count")
    h2_count: int = Field(ge=0, description="Header 2's count")
    h3_count: int = Field(ge=0, description="Header 3's count")
    h4_count: int = Field(ge=0, description="Header 4's count")
    h5_count: int = Field(ge=0, description="Header 5's count")
    h6_count: int = Field(ge=0, description="Header 6's count")

    @computed_field
    @property
    def total_count(self) -> int:
        return (
            self.h1_count
            + self.h2_count
            + self.h3_count
            + self.h4_count
            + self.h5_count
            + self.h6_count
        )


class InfoBoxAttribute(BaseModel):
    attribute_name: str = Field(max_length=200)
    attribute_value: str


class InfoBoxResponse(BaseModel):
    total_attributes: int = Field(
        ge=0, description="Total number of attributes in the infobox"
    )
    individual_infobox_data: List[InfoBoxAttribute] = Field(
        description="Individual infobox data"
    )


class CitationAnalysisResponse(BaseModel):
    citations_with_doi: int = Field(
        description="Count of citations containing DOI", ge=0
    )
    citations_with_isbn: int = Field(
        description="Count of citations containing ISBN", ge=0
    )
    see_also_links: int = Field(description="Count of see-also links", ge=0)
    external_links: int = Field(description="Count of external links", ge=0)
    page_title: str = Field(description="Page title", min_length=1, max_length=500)
    language: str = Field(description="Language", min_length=1, max_length=10)
    total_citations: int = Field(description="Total number of citations", ge=0)


class FinalAnalysisResponse(BaseModel):
    title: str = Field(max_length=500)
    table_analysis: TableResponse
    header_analysis: HeaderCount
    info_box: InfoBoxResponse
    citations: CitationAnalysisResponse
    total_images: int = Field(ge=0)


class MultiLanguageScoreResponse(BaseModel):
    lang_code: str = Field(max_length=10)
    lang_name: str = Field(max_length=100)
    title: Optional[str] = Field(default=None, max_length=500)
    score: float = Field(ge=-1.0)
    is_user_language: bool
    is_authority_article: bool
    error: Optional[str] = Field(default=None, max_length=500)


class AnalysisResultsResponse(BaseModel):
    article: str = Field(min_length=1)
    source_language_code: str = Field(min_length=1, max_length=10)
    scores_by_language: List[MultiLanguageScoreResponse]
