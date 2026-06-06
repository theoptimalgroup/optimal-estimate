from app.utils.html_text import html_to_plain_text, is_html_like


def test_is_html_like():
    assert is_html_like("<p>Hello</p>") is True
    assert is_html_like("Plain text") is False
    assert is_html_like(None) is False


def test_html_to_plain_text_converts_br_and_headings():
    raw = (
        '<span style="text-decoration: underline;"><strong>Access</strong></span><br />&nbsp;<br />'
        "Caretaker on site"
    )
    text = html_to_plain_text(raw)
    assert "Access" in text
    assert "Caretaker on site" in text
    assert "<span" not in text
    assert "&nbsp;" not in text


def test_html_to_plain_text_converts_lists():
    text = html_to_plain_text("<ol><li>First item</li><li>Second item</li></ol>")
    assert "First item" in text
    assert "Second item" in text
    assert "<li" not in text


def test_html_to_plain_text_removes_scripts():
    text = html_to_plain_text('<script>alert("x")</script><p>Safe text</p>')
    assert "alert" not in text
    assert "Safe text" in text


def test_html_to_plain_text_passes_through_plain_text():
    assert html_to_plain_text("Plain scope") == "Plain scope"
