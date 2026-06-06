"""Convert eWorks HTML rich text to plain text for editable fields."""

from __future__ import annotations

import re
from html import unescape
from html.parser import HTMLParser


_HTML_LIKE = re.compile(r"<\/?[a-z][\s\S]*>", re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<script[\s\S]*?</script>", re.IGNORECASE)
_STYLE_RE = re.compile(r"<style[\s\S]*?</style>", re.IGNORECASE)


def is_html_like(value: str | None) -> bool:
    if not value:
        return False
    return bool(_HTML_LIKE.search(value))


class _PlainTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._ol_index = 1
        self._list_ordered = False

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in {"script", "style"}:
            return
        if tag == "br":
            self._parts.append("\n")
        elif tag == "li":
            prefix = f"{self._ol_index}. " if self._list_ordered else "• "
            if self._list_ordered:
                self._ol_index += 1
            self._parts.append(prefix)
        elif tag == "ol":
            self._list_ordered = True
            self._ol_index = 1
        elif tag == "ul":
            self._list_ordered = False
        elif tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "table", "section"}:
            pass

    def handle_endtag(self, tag: str) -> None:
        if tag in {"p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "tr", "li", "ol", "ul", "table", "section"}:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)


def _collapse_blank_lines(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_plain_text(value: str | None) -> str:
    if not value or not str(value).strip():
        return ""
    raw = str(value).strip()
    if not is_html_like(raw):
        return _collapse_blank_lines(unescape(raw))

    cleaned = _SCRIPT_RE.sub("", raw)
    cleaned = _STYLE_RE.sub("", cleaned)

    parser = _PlainTextHTMLParser()
    try:
        parser.feed(cleaned)
        parser.close()
    except Exception:
        text = re.sub(r"<br\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
        text = re.sub(r"</p>", "\n", text, flags=re.IGNORECASE)
        text = re.sub(r"<li[^>]*>", "\n• ", text, flags=re.IGNORECASE)
        text = re.sub(r"<[^>]+>", "", text)
        return _collapse_blank_lines(unescape(text))

    joined = re.sub(r"[ \t]+", " ", "".join(parser._parts))
    return _collapse_blank_lines(unescape(joined))
