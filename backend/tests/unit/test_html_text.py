from app.utils.html_text import (
    decode_html_entities,
    html_to_plain_text,
    is_html_like,
    prepare_pdf_rich_text,
    sanitize_rich_html,
)

EWORKS_ACCESS_HTML = (
    '<span style="text-decoration: underline;"><strong>Access</strong></span><br />&nbsp;<br />'
    "Caretaker on site"
)
ENTITY_ENCODED_HTML = (
    "&lt;span style=&quot;text-decoration: underline;&quot;&gt;&lt;strong&gt;Quote&lt;/strong&gt;&lt;/span&gt;"
    "&lt;br /&gt;&amp;nbsp;"
)


def test_is_html_like():
    assert is_html_like("<p>Hello</p>") is True
    assert is_html_like(ENTITY_ENCODED_HTML) is True
    assert is_html_like("Plain text") is False
    assert is_html_like(None) is False


def test_decode_html_entities():
    assert decode_html_entities("&lt;span&gt;") == "<span>"
    assert decode_html_entities("&nbsp;") == "\u00a0"
    assert decode_html_entities("&amp;amp;") == "&amp;"


def test_html_to_plain_text_converts_br_and_headings():
    text = html_to_plain_text(EWORKS_ACCESS_HTML)
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


def test_sanitize_rich_html_renders_formatted_not_raw_tags():
    html = sanitize_rich_html(EWORKS_ACCESS_HTML)
    assert "Access" in html
    assert "<strong>" in html or "<b>" in html
    assert "<span style=" not in html
    assert "&nbsp;" not in html
    assert "&lt;span" not in html


def test_sanitize_rich_html_decodes_entity_encoded_markup():
    html = sanitize_rich_html(ENTITY_ENCODED_HTML)
    assert "Quote" in html
    assert "&lt;span" not in html
    assert "&nbsp;" not in html
    assert "<strong>" in html or "<b>" in html


def test_sanitize_rich_html_removes_unsafe_content():
    raw = (
        '<p onclick="alert(1)">Hello</p>'
        '<script>alert("x")</script>'
        '<a href="javascript:alert(1)">bad</a>'
        "<iframe src=\"evil\"></iframe>"
        "<strong>Safe</strong>"
    )
    html = sanitize_rich_html(raw)
    assert "Safe" in html
    assert "onclick" not in html.lower()
    assert "<script" not in html.lower()
    assert "javascript:" not in html.lower()
    assert "<iframe" not in html.lower()


def test_prepare_pdf_rich_text_converts_plain_line_breaks():
    html = prepare_pdf_rich_text("Line one\nLine two")
    assert "Line one<br" in html
    assert "Line two" in html
    assert "&lt;" not in html


def test_prepare_pdf_rich_text_handles_entity_encoded_html():
    html = prepare_pdf_rich_text(ENTITY_ENCODED_HTML)
    assert "Quote" in html
    assert "&lt;span" not in html
    assert "&nbsp;" not in html
