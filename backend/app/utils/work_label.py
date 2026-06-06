"""Shared work block display labels for quotes, PDFs, and client views."""

from __future__ import annotations

SCOPE_TRUNCATE = 60


def format_product_label(product_name: str | None, product_code: str | None = None) -> str | None:
    name = (product_name or "").strip()
    if not name:
        return None
    code = (product_code or "").strip()
    return f"{name} · {code}" if code else name


def format_work_label(
    *,
    product_name: str | None = None,
    product_code: str | None = None,
    scope: str | None = None,
    index: int = 0,
) -> str:
    product_label = format_product_label(product_name, product_code)
    if product_label:
        return product_label

    scope_text = (scope or "").strip()
    if scope_text:
        if len(scope_text) > SCOPE_TRUNCATE:
            return f"{scope_text[:SCOPE_TRUNCATE]}…"
        return scope_text

    return f"Work {index + 1}"
