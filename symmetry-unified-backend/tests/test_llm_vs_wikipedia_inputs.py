"""Input tests for POST /symmetry/v2/compare/llm-vs-wikipedia.

Task "Write tests for LLM vs Wikipedia": valid input, a bad Wikipedia title or
URL, and empty LLM text. Prashant's acceptance tests
(test_llm_vs_wikipedia_acceptance.py) check one case of each; these tests go
through the variants and check what the server does with them: which status and
error it returns, and whether Wikipedia is contacted at all. A rejected request
must not cause a fetch.

Wikipedia and the engines are replaced by fakes, so these tests run offline.
"""

import pytest

from app.main import app
from app.pipeline import MAX_TEXT_CHARS
from app.routers.api_v2 import get_llm_vs_wikipedia_service
from app.services.llm_vs_wikipedia import LlmVsWikipediaService
from app.services.wikipedia_reference import (
    ArticleNotFoundError,
    ArticleRef,
    WikipediaUnavailableError,
    article_ref,
)
from tests.test_api_v2_llm_vs_wikipedia import (
    PATH,
    FakeReader,
    FakeResolver,
    _check_comparison,
    _check_error,
    _request,
)


@pytest.fixture
def serve():
    def install(reader=None):
        reader = reader or FakeReader()
        service = LlmVsWikipediaService(reader, FakeResolver())
        app.dependency_overrides[get_llm_vs_wikipedia_service] = lambda: service
        return reader

    yield install
    app.dependency_overrides.pop(get_llm_vs_wikipedia_service, None)


# The request used by the other LLM vs Wikipedia tests: the LLM answer is source "a",
# the Wikipedia article (given by URL) is source "b".
def _body(llm=None, wiki=None) -> dict:
    body = _request()
    body["sources"][0].update(llm or {})
    body["sources"][1].update(wiki or {})
    return body


# The Wikipedia source given by title and language instead of a URL.
def _by_title(title, language) -> dict:
    body = _request()
    wiki = body["sources"][1]
    del wiki["url"]
    wiki.update(title=title, language=language)
    return body


# The text of a 422, whether the request model or the service rejected it.
def _messages(response) -> str:
    body = response.json()
    if "detail" in body:
        return " ".join(item["msg"] for item in body["detail"])
    return " ".join(error["message"] for error in body["errors"])


@pytest.mark.unit
class TestValidInput:
    @pytest.mark.parametrize(
        ("url", "language", "title"),
        [
            ("https://en.wikipedia.org/wiki/Eiffel_Tower", "en", "Eiffel Tower"),
            ("http://en.wikipedia.org/wiki/Eiffel_Tower", "en", "Eiffel Tower"),
            ("https://en.m.wikipedia.org/wiki/Eiffel_Tower", "en", "Eiffel Tower"),
            ("https://fr.wikipedia.org/wiki/Tour_Eiffel", "fr", "Tour Eiffel"),
            ("https://en.wikipedia.org/wiki/Z%C3%BCrich", "en", "Zürich"),
            (
                "https://en.wikipedia.org/wiki/Eiffel_Tower?action=raw#History",
                "en",
                "Eiffel Tower",
            ),
        ],
        ids=["https", "http", "mobile", "french", "percent-encoded", "query-fragment"],
    )
    def test_article_url_forms(self, client, serve, url, language, title):
        reader = serve()

        response = client.post(PATH, json=_body(wiki={"url": url}))

        _check_comparison(response)
        assert reader.refs == [ArticleRef(language=language, title=title)]

    @pytest.mark.parametrize(
        ("title", "language", "expected"),
        [
            ("Eiffel Tower", "en", ArticleRef("en", "Eiffel Tower")),
            ("Tour Eiffel", "FR", ArticleRef("fr", "Tour Eiffel")),
            ("  Eiffel Tower  ", " en ", ArticleRef("en", "Eiffel Tower")),
            ("Cantonese", "zh-yue", ArticleRef("zh-yue", "Cantonese")),
        ],
        ids=["plain", "uppercase-language", "padded", "hyphenated-language"],
    )
    def test_article_by_title_and_language(
        self, client, serve, title, language, expected
    ):
        reader = serve()

        response = client.post(PATH, json=_by_title(title, language))

        _check_comparison(response)
        assert reader.refs == [expected]

    def test_answer_in_another_language_than_the_article(self, client, serve):
        serve()
        body = _body(llm={"language": "fr"})

        response = client.post(PATH, json=body)

        assert _check_comparison(response)["sources"][0]["language"] == "fr"

    def test_unknown_answer_language_is_accepted(self, client, serve):
        serve()
        body = _body()
        del body["sources"][0]["language"]

        _check_comparison(client.post(PATH, json=body))


@pytest.mark.unit
class TestBadWikipediaUrl:
    # Only Wikipedia article URLs are accepted: the server never fetches anything else.
    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/wiki/Eiffel_Tower",
            "https://en.wikipedia.org.evil.com/wiki/Eiffel_Tower",
            "https://evilwikipedia.org/wiki/Eiffel_Tower",
            "http://localhost/wiki/Eiffel_Tower",
            "http://169.254.169.254/wiki/Eiffel_Tower",
            "https://user:secret@en.wikipedia.org/wiki/Eiffel_Tower",
            "https://en.wikipedia.org:8080/wiki/Eiffel_Tower",
            "ftp://en.wikipedia.org/wiki/Eiffel_Tower",
            "javascript:alert(1)",
            "en.wikipedia.org/wiki/Eiffel_Tower",
            "/wiki/Eiffel_Tower",
            "https://en.wikipedia.org/",
            "https://en.wikipedia.org/wiki/",
            "https://en.wikipedia.org/w/index.php?title=Eiffel_Tower",
        ],
    )
    def test_url_that_is_not_a_wikipedia_article_is_rejected(self, client, serve, url):
        reader = serve()

        response = client.post(PATH, json=_body(wiki={"url": url}))

        assert response.status_code == 422
        assert "Wikipedia article URL" in _messages(response)
        assert reader.refs == []

    def test_language_that_contradicts_the_url_is_rejected(self, client, serve):
        reader = serve()

        response = client.post(PATH, json=_body(wiki={"language": "fr"}))

        error = _check_error(response, 422)["errors"][0]
        assert error["code"] == "invalid_request"
        assert error["scope"] == "source"
        assert error["source_id"] == "b"
        assert "does not match" in error["message"]
        assert reader.refs == []

    def test_url_and_title_together_are_rejected(self, client, serve):
        reader = serve()

        response = client.post(PATH, json=_body(wiki={"title": "Eiffel Tower"}))

        assert response.status_code == 422
        assert "exactly one of" in _messages(response)
        assert reader.refs == []

    def test_wikipedia_source_without_a_url_or_title_is_rejected(self, client, serve):
        reader = serve()
        body = _body()
        del body["sources"][1]["url"]

        response = client.post(PATH, json=body)

        assert response.status_code == 422
        assert "exactly one of" in _messages(response)
        assert reader.refs == []

    def test_wikipedia_source_with_literal_text_is_rejected(self, client, serve):
        reader = serve()
        body = _body()
        del body["sources"][1]["url"]
        body["sources"][1]["text"] = "The Eiffel Tower is in Paris."

        response = client.post(PATH, json=body)

        error = _check_error(response, 422)["errors"][0]
        assert error["code"] == "invalid_request"
        assert error["source_id"] == "b"
        assert reader.refs == []

    def test_url_on_the_llm_source_is_rejected(self, client, serve):
        reader = serve()
        body = _body()
        del body["sources"][0]["text"]
        body["sources"][0]["url"] = "https://en.wikipedia.org/wiki/Eiffel_Tower"

        response = client.post(PATH, json=body)

        assert response.status_code == 422
        assert "only allowed for kind 'wikipedia'" in _messages(response)
        assert reader.refs == []

    def test_revision_must_be_a_number(self, client, serve):
        reader = serve()

        response = client.post(PATH, json=_body(wiki={"revision_id": "latest"}))

        assert response.status_code == 422
        assert reader.refs == []


@pytest.mark.unit
class TestBadWikipediaTitle:
    @pytest.mark.parametrize("title", ["", " ", "\t\n"], ids=["empty", "space", "tab"])
    def test_blank_title_is_rejected(self, client, serve, title):
        reader = serve()

        response = client.post(PATH, json=_by_title(title, "en"))

        error = _check_error(response, 422)["errors"][0]
        assert error["code"] == "invalid_request"
        assert error["source_id"] == "b"
        assert "title must not be empty" in error["message"]
        assert reader.refs == []

    def test_title_without_a_language_is_rejected(self, client, serve):
        reader = serve()
        body = _by_title("Eiffel Tower", None)
        del body["sources"][1]["language"]

        response = client.post(PATH, json=body)

        error = _check_error(response, 422)["errors"][0]
        assert error["code"] == "invalid_request"
        assert "language is required" in error["message"]
        assert reader.refs == []

    # The language becomes part of the host that is fetched, so it must be a bare code.
    @pytest.mark.parametrize(
        "language",
        [
            "evil.com/x?",
            "a.evil.com/#",
            "en/../x",
            "en wiki",
            "en_US",
            "-en",
            "en-",
            "en.wikipedia.org",
        ],
    )
    def test_language_that_is_not_a_language_code_is_rejected(
        self, client, serve, language
    ):
        reader = serve()

        response = client.post(PATH, json=_by_title("Eiffel Tower", language))

        error = _check_error(response, 422)["errors"][0]
        assert error["code"] == "invalid_request"
        assert "language code" in error["message"]
        assert reader.refs == []

    def test_title_with_no_article_returns_404(self, client, serve):
        serve(FakeReader(raises=ArticleNotFoundError("Wikipedia article not found")))

        response = client.post(PATH, json=_by_title("No Such Article", "en"))

        error = _check_error(response, 404)["errors"][0]
        assert error["code"] == "source_not_found"
        assert error["scope"] == "source"
        assert error["source_id"] == "b"


@pytest.mark.unit
class TestEmptyLlmText:
    @pytest.mark.parametrize(
        "text", ["", " ", "\n\t  \n"], ids=["empty", "space", "mixed"]
    )
    def test_empty_answer_is_rejected_without_reading_wikipedia(
        self, client, serve, text
    ):
        reader = serve()

        response = client.post(PATH, json=_body(llm={"text": text}))

        error = _check_error(response, 422)["errors"][0]
        assert error["code"] == "invalid_request"
        assert error["scope"] == "source"
        assert error["source_id"] == "a"
        assert "must not be empty" in error["message"]
        assert reader.refs == []

    def test_empty_answer_is_still_a_422_when_wikipedia_is_down(self, client, serve):
        serve(
            FakeReader(
                raises=WikipediaUnavailableError("Wikipedia could not be reached")
            )
        )

        response = client.post(PATH, json=_body(llm={"text": "  "}))

        error = _check_error(response, 422)["errors"][0]
        assert error["code"] == "invalid_request"
        assert error["source_id"] == "a"

    @pytest.mark.parametrize("missing", ["null", "absent"])
    def test_answer_without_text_is_rejected(self, client, serve, missing):
        reader = serve()
        body = _body()
        if missing == "null":
            body["sources"][0]["text"] = None
        else:
            del body["sources"][0]["text"]

        response = client.post(PATH, json=body)

        assert response.status_code == 422
        assert "exactly one of" in _messages(response)
        assert reader.refs == []

    def test_answer_over_the_length_limit_is_rejected(self, client, serve):
        reader = serve()

        response = client.post(
            PATH, json=_body(llm={"text": "a" * (MAX_TEXT_CHARS + 1)})
        )

        error = _check_error(response, 422)["errors"][0]
        assert error["code"] == "invalid_request"
        assert error["source_id"] == "a"
        assert "must not exceed" in error["message"]
        assert reader.refs == []


@pytest.mark.unit
class TestSourceSet:
    def test_one_source_is_rejected(self, client, serve):
        reader = serve()
        body = _body()
        body["sources"] = body["sources"][:1]

        response = client.post(PATH, json=body)

        assert response.status_code == 422
        assert "at least 2" in _messages(response)
        assert reader.refs == []

    @pytest.mark.parametrize(
        ("change", "fragment"),
        [
            (
                {"kind": "llm_output", "url": None, "text": "Paris."},
                "exactly one 'llm_output'",
            ),
            (
                {"kind": "text", "url": None, "text": "Paris."},
                "does not accept source kinds",
            ),
            ({"id": "a"}, "source ids must be unique"),
        ],
        ids=["two-llm-answers", "plain-text-source", "duplicate-ids"],
    )
    def test_wrong_sources_are_rejected(self, client, serve, change, fragment):
        reader = serve()

        response = client.post(PATH, json=_body(wiki=change))

        assert response.status_code == 422
        assert fragment in _messages(response)
        assert reader.refs == []

    def test_two_wikipedia_sources_are_rejected(self, client, serve):
        reader = serve()
        body = _body(llm={"kind": "wikipedia", "text": None})
        body["sources"][0]["url"] = "https://en.wikipedia.org/wiki/Paris"
        del body["sources"][0]["text"]

        response = client.post(PATH, json=body)

        assert response.status_code == 422
        assert "exactly one 'llm_output'" in _messages(response)
        assert reader.refs == []


# article_ref is where the title and language of a request are checked.
@pytest.mark.unit
class TestArticleRefInputs:
    def test_title_and_language_are_cleaned(self):
        ref = article_ref(None, "  Eiffel Tower ", " EN ")

        assert ref == ArticleRef(language="en", title="Eiffel Tower")

    @pytest.mark.parametrize("title", ["", "   ", "\n"])
    def test_blank_title_is_rejected(self, title):
        with pytest.raises(ValueError, match="title must not be empty"):
            article_ref(None, title, "en")

    @pytest.mark.parametrize("language", ["evil.com/x?", "en wiki", "-en", "en/"])
    def test_language_with_other_characters_is_rejected(self, language):
        with pytest.raises(ValueError, match="language code"):
            article_ref(None, "Eiffel Tower", language)

    def test_no_url_and_no_title_is_rejected(self):
        with pytest.raises(ValueError, match="needs a url or a title"):
            article_ref(None, None, "en")
