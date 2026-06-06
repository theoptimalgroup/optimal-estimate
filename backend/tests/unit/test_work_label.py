"""Unit tests for work block display labels."""

from app.utils.work_label import format_product_label, format_work_label


def test_format_product_label_name_only():
    assert format_product_label("Carpenter") == "Carpenter"


def test_format_product_label_with_code():
    assert format_product_label("Carpenter", "CARP-001") == "Carpenter · CARP-001"


def test_format_work_label_uses_product_name():
    assert format_work_label(product_name="Painting", product_code="PAINT-01", index=0) == "Painting · PAINT-01"


def test_format_work_label_scope_fallback():
    scope = "A" * 80
    assert format_work_label(scope=scope, index=1) == f"{'A' * 60}…"


def test_format_work_label_final_fallback():
    assert format_work_label(index=2) == "Work 3"
