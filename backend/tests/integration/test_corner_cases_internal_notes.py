"""Golden-file tests for corner_cases calculation outputs and internal notes.

Requires Postgres with the full XLSX rate rules imported (2528 rules):

    docker compose run --rm backend python scripts/import_quote_calculator_rules.py \\
      --overwrite --confirm-destructive

Run (hourly + daily):

    docker compose run --rm -v "$(pwd):/workspace" -w /workspace/backend backend \\
      sh -c "pip install -q openpyxl==3.1.5 && pytest tests/integration/test_corner_cases_internal_notes.py -q"
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ROOT / "scripts"
BACKEND = ROOT / "backend"

for path in (BACKEND, SCRIPTS, BACKEND / "tests"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from helpers.corner_cases_workbook import (  # noqa: E402
    DAYS_FIXTURE_PATH,
    FIXTURE_PATH,
    GoldenCompareMismatch,
    calculate_daily_result,
    calculate_hourly_result,
    compare_row_to_breakdown,
    format_mismatch_report,
    load_corner_case_days_rows,
    load_corner_case_rows,
)
from run_book2_batch_calculations import (  # noqa: E402
    _calculate_days_row,
    _calculate_row,
    _setup_backend_path,
)


@pytest.mark.integration
def test_corner_cases_match_excel_golden_file():
    pytest.importorskip("openpyxl")
    if not FIXTURE_PATH.exists():
        pytest.skip(f"Golden fixture missing: {FIXTURE_PATH}")

    _setup_backend_path()
    from app.db.session import SessionLocal

    rows = load_corner_case_rows()
    assert len(rows) == 1000

    db = SessionLocal()
    all_mismatches = []

    try:
        for row in rows:
            try:
                breakdown = _calculate_row(
                    db,
                    row.trade,
                    row.client,
                    row.engineers,
                    row.hours,
                    row.parking,
                    row.congestion,
                    row.materials,
                )
                quote_result = calculate_hourly_result(db, row)
            except Exception as exc:
                all_mismatches.append(
                    GoldenCompareMismatch(
                        row_num=row.row_num,
                        client=row.client,
                        trade=row.trade,
                        field="calculation_error",
                        expected="OK",
                        actual=str(exc),
                    )
                )
                continue

            all_mismatches.extend(compare_row_to_breakdown(row, breakdown, quote_result))
    finally:
        db.close()

    if all_mismatches:
        pytest.fail(format_mismatch_report(all_mismatches))


@pytest.mark.integration
def test_corner_cases_days_match_excel_golden_file():
    pytest.importorskip("openpyxl")
    if not DAYS_FIXTURE_PATH.exists():
        pytest.skip(f"Golden days fixture missing: {DAYS_FIXTURE_PATH}")

    _setup_backend_path()
    from app.db.session import SessionLocal

    rows = load_corner_case_days_rows()
    assert len(rows) == 1000

    db = SessionLocal()
    all_mismatches = []

    try:
        for row in rows:
            try:
                breakdown = _calculate_days_row(
                    db,
                    row.trade,
                    row.client,
                    row.engineers,
                    row.days,
                    row.parking,
                    row.congestion,
                    row.materials,
                )
                quote_result = calculate_daily_result(db, row)
            except Exception as exc:
                all_mismatches.append(
                    GoldenCompareMismatch(
                        row_num=row.row_num,
                        client=row.client,
                        trade=row.trade,
                        field="calculation_error",
                        expected="OK",
                        actual=str(exc),
                    )
                )
                continue

            all_mismatches.extend(compare_row_to_breakdown(row, breakdown, quote_result))
    finally:
        db.close()

    if all_mismatches:
        pytest.fail(format_mismatch_report(all_mismatches))
