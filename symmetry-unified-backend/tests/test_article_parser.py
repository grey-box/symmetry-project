from app.services.article_parser import _parse_article_html


def test_parse_article_html_removes_css_and_script_content():
    html = """
    <div>
        <p>
            Visible opening text.
            <style>.mw-parser-output { text-decoration: none; }</style>
            Visible article content.
            <script>console.log("not article text");</script>
            Visible ending text.
        </p>
    </div>
    """

    article = _parse_article_html(
        html,
        title="Test Article",
        lang="en",
        source="test",
    )

    assert len(article.sections) == 1

    content = article.sections[0].clean_content

    assert "Visible opening text." in content
    assert "Visible article content." in content
    assert "Visible ending text." in content
    assert "text-decoration" not in content
    assert "mw-parser-output" not in content
    assert "console.log" not in content