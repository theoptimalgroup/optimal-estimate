"""Convert and sanitize eWorks HTML rich text for PDFs and plain-text fields."""

from __future__ import annotations

import re
from html import escape, unescape
from html.parser import HTMLParser

_HTML_LIKE = re.compile(r"<\/?[a-z][\s\S]*>", re.IGNORECASE)
_ENTITY_HTML_LIKE = re.compile(r"&lt;\/?[a-z]", re.IGNORECASE)
_MALFORMED_CLOSE_TAG = re.compile(r"<\/span\s+[^>]+>", re.IGNORECASE)
_SCRIPT_RE = re.compile(r"<script[\s\S]*?</script>", re.IGNORECASE)
_STYLE_RE = re.compile(r"<style[\s\S]*?</style>", re.IGNORECASE)
_IFRAME_RE = re.compile(r"<iframe[\s\S]*?(?:<\/iframe>|/>)", re.IGNORECASE)
_EVENT_HANDLER_RE = re.compile(r"\s+on[a-z]+\s*=\s*(['\"]).*?\1", re.IGNORECASE)
_JAVASCRIPT_HREF_RE = re.compile(r"href\s*=\s*(['\"])\s*javascript:[^'\"]*\1", re.IGNORECASE)
_SPAN_UNDERLINE_RE = re.compile(
    r'<span\b[^>]*style\s*=\s*(["\'])[^"\']*text-decoration\s*:\s*underline[^"\']*\1[^>]*>([\s\S]*?)</span>',
    re.IGNORECASE,
)

ALLOWED_TAGS = frozenset({"strong", "b", "em", "i", "u", "br", "p", "ul", "ol", "li", "div", "span"})


def is_html_like(value: str | None) -> bool:
    if not value:
        return False
    text = str(value)
    if _HTML_LIKE.search(text):
        return True
    if _ENTITY_HTML_LIKE.search(text):
        return True
    if _MALFORMED_CLOSE_TAG.search(text):
        return True
    return False


def decode_html_entities(value: str) -> str:
    if not value:
        return ""
    text = str(value).replace("\r\n", "\n")
    text = text.replace("&nbsp;", "\u00a0")
    return unescape(text)


def decode_html_entities_repeated(value: str, max_passes: int = 3) -> str:
    current = value
    for _ in range(max_passes):
        decoded = decode_html_entities(current)
        if decoded == current:
            break
        current = decoded
    return current


def normalize_malformed_eworks_html(html: str) -> str:
    out = html
    out = re.sub(r"<\/span\s+([^>]+)>", r"<span \1>", out, flags=re.IGNORECASE)
    out = re.sub(r"<\/strong\s+([^>]+)>", r"<strong \1>", out, flags=re.IGNORECASE)
    out = re.sub(r"<\/u\s+([^>]+)>", r"<u \1>", out, flags=re.IGNORECASE)
    return out


def _preprocess_eworks_html(html: str) -> str:
    normalized = normalize_malformed_eworks_html(html)
    return _SPAN_UNDERLINE_RE.sub(r"<u>\2</u>", normalized)


def _plain_text_to_safe_html(text: str) -> str:
    escaped = escape(text.replace("\u00a0", " "))
    return escaped.replace("\n", "<br />\n")


def _fallback_sanitize_rich_html(html: str) -> str:
    cleaned = _SCRIPT_RE.sub("", html)
    cleaned = _STYLE_RE.sub("", cleaned)
    cleaned = _IFRAME_RE.sub("", cleaned)
    cleaned = _EVENT_HANDLER_RE.sub("", cleaned)
    cleaned = _JAVASCRIPT_HREF_RE.sub("", cleaned)
    cleaned = _preprocess_eworks_html(cleaned)

    def _replace_tag(match: re.Match[str]) -> str:
        tag = match.group(1).lower().rstrip("/")
        if tag.startswith("/"):
            closing = tag[1:]
            return f"</{closing}>" if closing in ALLOWED_TAGS else ""
        if tag in ALLOWED_TAGS:
            return f"<{tag}>"
        return ""

    cleaned = re.sub(r"<\/?([a-z][a-z0-9]*)\b[^>]*>", _replace_tag, cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def sanitize_rich_html(value: str) -> str:
    if not value or not str(value).strip():
        return ""
    preprocessed = _preprocess_eworks_html(decode_html_entities_repeated(str(value).strip()))

    try:
        import bleach

        cleaned = bleach.clean(
            preprocessed,
            tags=sorted(ALLOWED_TAGS),
            attributes={},
            strip=True,
            strip_comments=True,
            protocols=[],
        )
    except ImportError:
        cleaned = _fallback_sanitize_rich_html(preprocessed)
    return cleaned.replace("\xa0", " ")


def prepare_pdf_rich_text(value: str | None) -> str:
    if not value or not str(value).strip():
        return ""
    raw = decode_html_entities_repeated(str(value).strip())
    normalized = normalize_malformed_eworks_html(raw)
    if is_html_like(normalized):
        return sanitize_rich_html(normalized)
    return _plain_text_to_safe_html(normalized.replace("\u00a0", " "))


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
    text = text.replace("\r\n", "\n").replace("\u00a0", " ")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def html_to_plain_text(value: str | None) -> str:
    if not value or not str(value).strip():
        return ""
    raw = decode_html_entities_repeated(str(value).strip())
    normalized = normalize_malformed_eworks_html(raw)
    if not is_html_like(normalized):
        return _collapse_blank_lines(raw.replace("\u00a0", " "))

    cleaned = _SCRIPT_RE.sub("", normalized)
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
        return _collapse_blank_lines(text.replace("\u00a0", " "))

    joined = re.sub(r"[ \t]+", " ", "".join(parser._parts))
    return _collapse_blank_lines(joined.replace("\u00a0", " "))
