from pathlib import Path
from uuid import uuid4

from jinja2 import Environment, FileSystemLoader, select_autoescape


def _template_env() -> Environment:
    return Environment(
        loader=FileSystemLoader(Path(__file__).parent.parent / "templates"),
        autoescape=select_autoescape(["html", "xml"]),
    )


def render_quote_document(context: dict, *, is_draft: bool) -> tuple[bytes, str, str]:
    """Render quote PDF/HTML. Returns (content_bytes, file_name, media_type)."""
    template = _template_env().get_template("quote_pdf.html")
    html_content = template.render(**context, is_draft=is_draft)
    file_name = f"quote_{context['quote_number']}_{'draft' if is_draft else 'final'}_{uuid4().hex[:8]}.pdf"

    try:
        from weasyprint import HTML

        return HTML(string=html_content).write_pdf(), file_name, "application/pdf"
    except (ImportError, OSError):
        html_name = file_name.replace(".pdf", ".html")
        return html_content.encode("utf-8"), html_name, "text/html"


def render_eworks_estimate_document(context: dict, *, is_draft: bool) -> tuple[bytes, str, str]:
    """Render eWorks estimation PDF/HTML matching the field document layout."""
    template = _template_env().get_template("eworks_estimate_pdf.html")
    html_content = template.render(**context, is_draft=is_draft)
    quote_number = context.get("quote_number") or "estimate"
    file_name = f"document_{quote_number}_{'draft' if is_draft else 'final'}_{uuid4().hex[:8]}.pdf"

    try:
        from weasyprint import HTML

        return HTML(string=html_content).write_pdf(), file_name, "application/pdf"
    except (ImportError, OSError):
        html_name = file_name.replace(".pdf", ".html")
        return html_content.encode("utf-8"), html_name, "text/html"
