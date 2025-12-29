import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
from app.main import app


@pytest.fixture(scope="session")
def client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_wikipedia_page():
    """Mock Wikipedia page object"""
    page = Mock()
    page.exists.return_value = True
    page.text = "Test article content"
    page.langlinks = {"fr": "Test_Article", "es": "Artículo_de_prueba"}
    return page


@pytest.fixture
def mock_wikipediaapi():
    """Mock wikipediaapi.Wikipedia"""
    wiki = Mock()
    page = Mock()
    page.exists.return_value = True
    page.text = "Test article content"
    page.langlinks = {"fr": "Test_Article", "es": "Artículo_de_prueba"}
    wiki.page.return_value = page
    return wiki


@pytest.fixture
def mock_wikipediaapi_fresh():
    """Fresh mock wikipediaapi.Wikipedia for each test"""
    wiki = Mock()
    page = Mock()
    page.exists.return_value = True
    page.text = "Test article content"
    page.langlinks = {"fr": "Test_Article", "es": "Artículo_de_prueba"}
    wiki.page.return_value = page
    return wiki


@pytest.fixture
def sample_obama_text_a():
    """Sample text from Obama article A"""
    return """Barack Hussein Obama II is an American politician who served as the 44th president of United States from 2009 to 2017.
Obama previously served as a U.S. senator representing Illinois from 2005 to 2008 and as an Illinois state senator from 1997 to 2004.
Obama was born in Honolulu, Hawaii. 
He graduated from Columbia University in 1983 with a Bachelor of Arts degree in political science and later worked as a community organizer in Chicago.
In 1988, Obama enrolled in Harvard Law School, where he was the first black president of the Harvard Law Review. 
In the 2008 presidential election, after a close primary campaign against Hillary Clinton, he was nominated by the Democratic Party for president. 
Obama selected Joe Biden as his running mate and defeated Republican nominee John McCain and his running mate Sarah Palin."""


@pytest.fixture
def sample_obama_text_b():
    """Sample text from Obama article B"""
    return """Barack Hussein Obama II is an American politician who served as the 44th president of United States from 2009 to 2017.
A member of the Democratic Party, he was the first African-American president in American history.
He graduated from Columbia University in 1983 with a Bachelor of Arts degree in political science and later worked as a community organizer in Chicago.
In 1988, Obama enrolled in Harvard Law School, where he was the first black president of the Harvard Law Review. 
He became a civil rights attorney and an academic, teaching constitutional law at the University of Chicago Law School from 1992 to 2004.
In 1996, Obama was elected to represent the 13th district in the Illinois Senate, a position he held until 2004, when he successfully ran for the U.S. Senate. 
In the 2008 presidential election, after a close primary campaign against Hillary Clinton, he was nominated by the Democratic Party for president."""


@pytest.fixture
def valid_compare_request():
    """Valid comparison request payload"""
    return {
        "article_text_blob_1": "First article text",
        "article_text_blob_2": "Second article text",
        "article_text_blob_1_language": "en",
        "article_text_blob_2_language": "en",
        "comparison_threshold": 0.65,
        "model_name": "sentence-transformers/LaBSE",
    }


@pytest.fixture
def valid_llm_compare_request():
    """Valid LLM comparison request payload"""
    return {
        "text_a": "First text to compare",
        "text_b": "Second text to compare",
    }


@pytest.fixture
def valid_semantic_compare_request():
    """Valid semantic comparison request payload"""
    return {
        "text_a": "First text to compare",
        "text_b": "Second text to compare",
        "similarity_threshold": 0.75,
        "model_name": "sentence-transformers/LaBSE",
    }


@pytest.fixture
def mock_article_parser():
    """Mock article parser service"""
    from app.models import Section

    def article_fetcher(title="Test Article", lang="en"):
        article = Mock()
        article.title = "Test Article"
        article.lang = lang
        article.source = "wikipedia"
        article.sections = [
            Section(
                title="Introduction",
                raw_content="Raw content",
                clean_content="Clean content",
                citations=[],
                citation_position=[],
            )
        ]
        article.references = []
        return article

    return article_fetcher


@pytest.fixture
def mock_structural_analysis_data():
    """Mock structural analysis data"""
    from app.models import (
        TableResponse,
        HeaderCount,
        InfoBoxResponse,
        CitationAnalysisResponse,
    )

    return {
        "table_analysis": TableResponse(
            number_of_tables=2,
            individual_table_information=[
                {"table_index": 0, "number_of_rows": 3, "number_of_columns": 4}
            ],
            language="en",
        ),
        "header_analysis": HeaderCount(
            h1_count=1,
            h2_count=5,
            h3_count=10,
            h4_count=0,
            h5_count=0,
            h6_count=0,
        ),
        "info_box": InfoBoxResponse(
            total_attributes=10,
            individual_infobox_data=[
                {"attribute_name": "Name", "attribute_value": "Test"}
            ],
        ),
        "citations": CitationAnalysisResponse(
            citations_with_doi=5,
            citations_with_isbn=2,
            see_also_links=3,
            external_links=10,
            page_title="Test Article",
            language="en",
            total_citations=20,
        ),
    }


@pytest.fixture
def mock_cache():
    """Mock cache service"""
    cache = {}

    def get_cached_article(key):
        if key in cache:
            return cache[key]
        return (None, None)

    def set_cached_article(key, content, languages):
        cache[key] = (content, languages)

    mock = Mock()
    mock.get_cached_article = get_cached_article
    mock.set_cached_article = set_cached_article
    mock.cache = cache
    return mock
