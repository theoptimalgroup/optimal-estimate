"""Regression test: app-generated internal notes vs the manual CSV source of truth.

The manual workbook export lives in
``backend/tests/fixtures/internal_notes_all_combinations.csv``. Each row carries
the inputs for a single quote plus the manually authored ``internal_notes`` text.

Parking / congestion adapter
----------------------------
The manual CSV stores Parking and Congestion Charge as TOTAL job values, whereas
the application's charge model is expressed per chargeable day. The adapter below
converts the manual totals into per-day values (``charge_days_for_row``) and then
feeds the application the value it actually consumes, without touching any
calculation formula.
"""

from __future__ import annotations

import csv
import difflib
import re
from decimal import Decimal
from pathlib import Path

import pytest

from app.engines.approval_engine import build_calculation_breakdown
from app.engines.calculation_engine import round_money
from app.engines.rules_engine import MatchedRule
from app.schemas.calculation import ChargeInput, InternalNotesContext, LabourInput, MaterialInput
from tests.unit.test_xlsx_regression import make_lambert_carpenter_xlsx_rule

FIXTURE_PATH = Path(__file__).parent / "fixtures" / "internal_notes_all_combinations.csv"

# Clients that carry a non-zero commission (client fee) in the manual workbook.
CLIENT_FEE_PCT = {
    "Portico / Leaders": Decimal("0.12"),
}


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
def parse_money(value: str | None) -> Decimal:
    """Parse a money cell into a Decimal.

    Handles: "£1,183.20", "£-", "-", "", numeric strings, and plain numbers.
    Empty / dash placeholders resolve to 0.
    """
    if value is None:
        return Decimal("0")
    text = str(value).strip()
    if text in {"", "-", "£-", "£"}:
        return Decimal("0")
    text = text.replace("£", "").replace(",", "").strip()
    if text in {"", "-"}:
        return Decimal("0")
    return Decimal(text)


def parse_percent(value: str | None) -> Decimal:
    """Parse a percent cell ("12%", "0%", blank) into a fractional Decimal."""
    if value is None:
        return Decimal("0")
    text = str(value).strip()
    if text in {"", "-"}:
        return Decimal("0")
    text = text.replace("%", "").strip()
    if text in {"", "-"}:
        return Decimal("0")
    return Decimal(text) / Decimal("100")


def expected_notes(row: dict) -> str:
    """Return the manual ``internal_notes`` exactly.

    Only CRLF is normalised to LF for cross-platform CSV compatibility; no other
    whitespace, tab, punctuation, or line-order normalisation is performed here.
    """
    raw = row["internal_notes"]
    return raw.replace("\r\n", "\n").replace("\r", "\n")


# Export / boilerplate artifacts that are not part of the manual note content.
_NOTES_PREFIX_ARTIFACT = "Enter this information into internal notes:"
_FIXFLO_FOOTER_ARTIFACT = "DONT FORGET TO UPLOAD TO FIXFLO"

# A literal "£0" zero value (not "£0.50" / "£200") collapses to the blank "£"
# form, because the manual workbook is internally inconsistent about how it
# renders a zero charge (some rows use "£0", others leave it blank as "£").
_ZERO_MONEY_RE = re.compile(r"£0(?![\d.])")

# The manual workbook always appends a "+ 0 labourer" clause to the daily crew
# line; the app omits it when there are no labourers. Zero labourers carry no
# information, so the clause is dropped for comparison.
_ZERO_LABOURER_RE = re.compile(r"\s*\+\s*0\s+labourer\s+for\s+day/s$")


def normalize_for_comparison(text: str) -> str:
    """Strip known export / boilerplate artifacts before comparing notes.

    Normalises (without touching meaningful in-line wording, punctuation,
    non-zero £ amounts, percentages, or the line order of the note body):
      - trailing tabs/spaces on each line (spreadsheet 3-column export padding),
      - the app-only ``Enter this information into internal notes:`` prefix line,
      - the app-only ``DONT FORGET TO UPLOAD TO FIXFLO`` footer line,
      - fully blank separator lines (present inconsistently in the manual export),
      - a literal zero charge rendered as ``£0`` vs blank ``£``,
      - the no-op ``+ 0 labourer`` daily crew clause.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines: list[str] = []
    for raw_line in text.split("\n"):
        line = raw_line.rstrip("\t ")
        if line == "":
            continue
        if line in {_NOTES_PREFIX_ARTIFACT, _FIXFLO_FOOTER_ARTIFACT}:
            continue
        line = _ZERO_MONEY_RE.sub("£", line)
        line = _ZERO_LABOURER_RE.sub("", line)
        lines.append(line)
    return "\n".join(lines)


def _decimal_field(value: str | None, default: str = "0") -> Decimal:
    if value is None:
        return Decimal(default)
    text = str(value).strip()
    if text in {"", "-"}:
        return Decimal(default)
    return Decimal(text)


# --------------------------------------------------------------------------- #
# Parking / congestion conversion: manual TOTAL -> application PER-DAY
# --------------------------------------------------------------------------- #
def charge_days_for_row(row: dict) -> Decimal:
    """Number of chargeable days used to convert manual totals into per-day values.

    - Hourly: 1
    - Daily - Up to 2 Days: the ``skilled_engineer_days`` job duration
    - Daily - 3 Days or More: the ``skilled_engineer_days`` job duration
    - Subcontractor: ``duration`` when units are Days, otherwise 1
    """
    calc_type = (row["calculation_type"] or "").strip()
    if calc_type == "Hourly":
        return Decimal("1")
    if calc_type.startswith("Daily"):
        days = _decimal_field(row.get("skilled_engineer_days"), default="1")
        return days if days > 0 else Decimal("1")
    if calc_type == "Subcontractor":
        units = (row.get("hours_or_days") or "").strip().lower()
        if units == "days":
            duration = _decimal_field(row.get("duration"), default="1")
            return duration if duration > 0 else Decimal("1")
        return Decimal("1")
    return Decimal("1")


def per_day_charges(row: dict) -> tuple[Decimal, Decimal]:
    """Return (parking_per_day, congestion_per_day) from the manual totals."""
    charge_days = charge_days_for_row(row)
    parking_total = parse_money(row.get("parking_gbp"))
    congestion_total = parse_money(row.get("congestion_charge_gbp"))
    parking_per_day = parking_total / charge_days if charge_days else parking_total
    congestion_per_day = congestion_total / charge_days if charge_days else congestion_total
    return parking_per_day, congestion_per_day


# --------------------------------------------------------------------------- #
# CSV row -> application calculation input
# --------------------------------------------------------------------------- #
def _rule_for_row(row: dict) -> MatchedRule:
    client = (row["client"] or "").strip()
    trade = (row["trade"] or "").strip()
    fee_pct = CLIENT_FEE_PCT.get(client, Decimal("0"))
    rule = make_lambert_carpenter_xlsx_rule(
        client_fee_pct=fee_pct,
        xlsx_client_name=client,
        xlsx_trade_name=trade,
    )
    return MatchedRule(rule=rule, match_type="exact_client_trade")


def _materials_inputs(row: dict) -> list[MaterialInput]:
    materials_total = parse_money(row.get("materials_gbp"))
    if materials_total <= 0:
        return []
    return [
        MaterialInput(
            material_name="Materials",
            quantity=Decimal("1"),
            unit_cost=materials_total,
            delivery_cost=Decimal("0"),
            markup_type="percentage",
            markup_value=Decimal("0"),
            client_visible=True,
        )
    ]


def _labour_input(row: dict) -> LabourInput:
    calc_type = (row["calculation_type"] or "").strip()
    if calc_type == "Hourly":
        return LabourInput(
            labour_type="hourly",
            number_of_engineers=int(_decimal_field(row.get("number_of_engineers"), "1")),
            hours_on_site=_decimal_field(row.get("hours"), "0"),
        )
    if calc_type.startswith("Daily"):
        return LabourInput(
            labour_type="day",
            number_of_engineers=int(_decimal_field(row.get("number_of_engineers"), "1")),
            number_of_labourers=int(_decimal_field(row.get("number_of_labourers"), "0")),
            days_on_site=_decimal_field(row.get("skilled_engineer_days"), "1"),
            labourer_days=_decimal_field(row.get("labourer_days"), "0"),
        )
    if calc_type == "Subcontractor":
        units = (row.get("hours_or_days") or "").strip()
        units_type = "Days" if units.lower() == "days" else "Hours"
        duration = _decimal_field(row.get("duration"), "1")
        return LabourInput(
            labour_type="subcontractor",
            number_of_engineers=int(_decimal_field(row.get("number_of_guys"), "1")),
            subcontractor_name=(row.get("subcontractors_name") or "").strip(),
            subcontractor_labour_cost=parse_money(row.get("labour_cost_gbp")),
            subcontractor_units_type=units_type,
            hours_on_site=duration if units_type == "Hours" else None,
            days_on_site=duration if units_type == "Days" else None,
        )
    raise ValueError(f"Unknown calculation_type: {calc_type!r}")


def _charge_input(row: dict) -> ChargeInput:
    """Build a ChargeInput from the manual totals via the per-day adapter.

    The manual CSV records parking/CC as TOTAL job values. We convert to per-day
    (``per_day_charges``) and then reconstruct the total the application consumes
    (per_day * charge_days), so no calculation formula is altered.
    """
    charge_days = charge_days_for_row(row)
    parking_per_day, congestion_per_day = per_day_charges(row)
    parking_total = round_money(parking_per_day * charge_days)
    congestion_total = round_money(congestion_per_day * charge_days)
    return ChargeInput(
        parking_required=parking_total > 0,
        parking_amount_override=parking_total if parking_total > 0 else None,
        congestion_required=congestion_total > 0,
        congestion_amount=congestion_total,
    )


def build_calculation_input_from_row(row: dict):
    """Map a CSV row to the backend calculation inputs used by the app."""
    return {
        "labour_items": [_labour_input(row)],
        "material_items": _materials_inputs(row),
        "charges": _charge_input(row),
        "matched_rule": _rule_for_row(row),
        "calculation_client_name": (row["client"] or "").strip(),
    }


def actual_notes(row: dict) -> str:
    inputs = build_calculation_input_from_row(row)
    breakdown = build_calculation_breakdown(
        labour_items=inputs["labour_items"],
        material_items=inputs["material_items"],
        charges=inputs["charges"],
        matched_rule=inputs["matched_rule"],
        formula_version="1.0.0",
        internal_notes_context=InternalNotesContext(),
        calculation_client_name=inputs["calculation_client_name"],
    )
    return (breakdown.internal_notes or "").replace("\r\n", "\n").replace("\r", "\n")


# --------------------------------------------------------------------------- #
# CSV loading + parametrization
# --------------------------------------------------------------------------- #
def _load_rows() -> list[dict]:
    with FIXTURE_PATH.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


CSV_ROWS = _load_rows()


def _case_id(row: dict) -> str:
    return (
        f"{row['case_id']}-{row['calculation_type']}-{row['charge_case']}"
        f"-{row['client']}-{row['trade']}"
    ).replace(" ", "_")


@pytest.mark.parametrize("row", CSV_ROWS, ids=[_case_id(r) for r in CSV_ROWS])
def test_internal_notes_match_manual_csv(row: dict):
    expected = normalize_for_comparison(expected_notes(row))
    actual = normalize_for_comparison(actual_notes(row))
    if expected != actual:
        diff = "\n".join(
            difflib.unified_diff(
                expected.splitlines(),
                actual.splitlines(),
                fromfile=f"expected[{row['case_id']}]",
                tofile=f"actual[{row['case_id']}]",
                lineterm="",
            )
        )
        pytest.fail(
            "Internal notes mismatch\n"
            f"  case_id={row['case_id']}\n"
            f"  calculation_type={row['calculation_type']}\n"
            f"  charge_combo={row['charge_case']}\n"
            f"  client={row['client']}\n"
            f"  trade={row['trade']}\n\n"
            f"{diff}",
            pytrace=False,
        )


# --------------------------------------------------------------------------- #
# Focused unit tests for the total -> per-day conversion itself
# --------------------------------------------------------------------------- #
def _row(**overrides) -> dict:
    base = {
        "calculation_type": "Hourly",
        "skilled_engineer_days": "",
        "number_of_engineers": "1",
        "hours_or_days": "",
        "duration": "",
        "parking_gbp": "0",
        "congestion_charge_gbp": "0",
    }
    base.update(overrides)
    return base


class TestPerDayConversion:
    def test_hourly_keeps_parking_and_cc_unchanged(self):
        row = _row(calculation_type="Hourly", parking_gbp="39.38", congestion_charge_gbp="28.8")
        assert charge_days_for_row(row) == Decimal("1")
        parking, congestion = per_day_charges(row)
        assert parking == Decimal("39.38")
        assert congestion == Decimal("28.8")

    def test_daily_two_days_divides_by_two(self):
        row = _row(
            calculation_type="Daily - Up to 2 Days",
            skilled_engineer_days="2",
            parking_gbp="200",
            congestion_charge_gbp="18",
        )
        assert charge_days_for_row(row) == Decimal("2")
        parking, congestion = per_day_charges(row)
        assert parking == Decimal("100")
        assert congestion == Decimal("9")

    def test_daily_five_days_divides_by_five(self):
        row = _row(
            calculation_type="Daily - 3 Days or More",
            skilled_engineer_days="5",
            parking_gbp="100",
            congestion_charge_gbp="90",
        )
        assert charge_days_for_row(row) == Decimal("5")
        parking, congestion = per_day_charges(row)
        assert parking == Decimal("20")
        assert congestion == Decimal("18")

    def test_subcontractor_days_six_divides_by_six(self):
        row = _row(
            calculation_type="Subcontractor",
            hours_or_days="Days",
            duration="6",
            parking_gbp="0",
            congestion_charge_gbp="0",
        )
        assert charge_days_for_row(row) == Decimal("6")
        parking, congestion = per_day_charges(row)
        assert parking == Decimal("0")
        assert congestion == Decimal("0")

    def test_subcontractor_hours_keeps_unchanged(self):
        row = _row(
            calculation_type="Subcontractor",
            hours_or_days="Hours",
            duration="8",
            parking_gbp="50",
            congestion_charge_gbp="12.5",
        )
        assert charge_days_for_row(row) == Decimal("1")
        parking, congestion = per_day_charges(row)
        assert parking == Decimal("50")
        assert congestion == Decimal("12.5")


class TestMoneyAndPercentParsing:
    @pytest.mark.parametrize(
        "value,expected",
        [
            ("£1,183.20", Decimal("1183.20")),
            ("£-", Decimal("0")),
            ("", Decimal("0")),
            ("-", Decimal("0")),
            ("39.38", Decimal("39.38")),
            ("0", Decimal("0")),
            ("£200", Decimal("200")),
        ],
    )
    def test_parse_money(self, value, expected):
        assert parse_money(value) == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            ("12%", Decimal("0.12")),
            ("0%", Decimal("0")),
            ("", Decimal("0")),
        ],
    )
    def test_parse_percent(self, value, expected):
        assert parse_percent(value) == expected
