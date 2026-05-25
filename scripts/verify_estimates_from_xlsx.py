#!/usr/bin/env python3
"""Extract and verify estimate rows from optimal_estimating_Alex.xlsx."""

from __future__ import annotations

import argparse
import json
import re
import sys
import zipfile
from dataclasses import asdict, dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_XLSX = ROOT / "tests" / "fixtures" / "optimal_estimating_Alex.xlsx"
DEFAULT_JSON = ROOT / "tests" / "fixtures" / "alex_xlsx_expected_estimates.json"
DEFAULT_REPORT = ROOT / "docs" / "ALEX_XLSX_VERIFICATION_REPORT.md"

NS = {"m": "http://purl.oclc.org/ooxml/spreadsheetml/main"}
CONGESTION_DEFAULT = Decimal("18")


@dataclass
class AlexEstimateRow:
    xlsx_row: int
    client: str
    trade: str
    time_frame: str
    helper_type: str
    hours: float
    days: float
    engineers: int
    labourers: int
    labourer_days: float
    materials: float
    parking: float
    congestion: float
    overhead: float | None
    expected_labour_charge_to_client: float
    expected_materials_parking_cc_charge: float
    expected_profit_gbp: float
    expected_profit_pct: float
    quote_number: str | None = None
    door_no: str | None = None

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _money(value: str | None) -> float:
    if value is None or value == "":
        return 0.0
    cleaned = value.replace("£", "").strip()
    if not cleaned:
        return 0.0
    return float(cleaned)


def _parse_helper_type(notes: str) -> str:
    if "HOURLY QUOTE HELPER USED" in notes:
        return "hourly"
    if "DAILY (3 Days >) QUOTE HELPER USED" in notes:
        return "daily_3_plus"
    if "DAILY (Up to 2 Days) QUOTE HELPER USED" in notes:
        return "daily_up_to_2"
    raise ValueError("Unknown helper type in internal notes")


def _parse_notes(notes: str) -> dict[str, Any]:
    helper_type = _parse_helper_type(notes)
    budget = re.search(
        r"BUDGET: Materials:\s*£?\s*([\d.]*)?\s*/ Parking: £?\s*([\d.]*)?\s*/ CC: £?\s*([\d.]*)?\s*/ OH:\s*£?\s*([\d.]+)",
        notes,
    )
    charges = re.search(
        r"TOTAL CHARGE TO CLIENT:\s*Labour:\s*£?\s*([\d.]+)\s*/\s*Materials etc:\s*£?\s*([\d.]+)",
        notes,
    )
    profit = re.search(r"PROFIT ON JOB:\s*£?\s*([\d.]+)\s*/\s*([\d.]+)%?", notes)
    if not budget or not charges or not profit:
        raise ValueError("Could not parse internal notes totals")

    daily_crew = re.search(
        r"(\d+)\s+Carpenter\s+for\s+([\d.]+)\s+(Day/s|Hour/s)\s*\+\s*(\d+)\s+labourer\s+for\s+([\d.]+)\s+day/s",
        notes,
    )
    hourly_crew = re.search(r"(\d+)\s+Carpenter\s+for\s+([\d.]+)\s+Hour/s", notes)

    engineers = 1
    hours = 0.0
    days = 0.0
    labourers = 0
    labourer_days = 0.0

    if hourly_crew:
        engineers = int(hourly_crew.group(1))
        hours = float(hourly_crew.group(2))
    elif daily_crew:
        engineers = int(daily_crew.group(1))
        days = float(daily_crew.group(2))
        labourers = int(daily_crew.group(4))
        labourer_days = float(daily_crew.group(5))

    materials = _money(budget.group(1))
    parking = _money(budget.group(2))
    cc_text = budget.group(3)
    congestion = _money(cc_text) if cc_text else 0.0
    overhead = _money(budget.group(4))

    return {
        "helper_type": helper_type,
        "hours": hours,
        "days": days,
        "engineers": engineers,
        "labourers": labourers,
        "labourer_days": labourer_days,
        "materials": materials,
        "parking": parking,
        "congestion": congestion,
        "overhead": overhead,
        "expected_labour_charge_to_client": _money(charges.group(1)),
        "expected_materials_parking_cc_charge": _money(charges.group(2)),
        "expected_profit_gbp": _money(profit.group(1)),
        "expected_profit_pct": _money(profit.group(2)),
    }


def load_workbook_rows(xlsx_path: Path) -> dict[int, dict[str, Any]]:
    with zipfile.ZipFile(xlsx_path) as zf:
        shared_strings: list[str] = []
        ss_root = ET.fromstring(zf.read("xl/sharedStrings.xml"))
        for si in ss_root.findall("m:si", NS):
            text_node = si.find("m:t", NS)
            if text_node is not None:
                shared_strings.append(text_node.text or "")
            else:
                shared_strings.append("".join((run.find("m:t", NS).text or "") for run in si.findall("m:r", NS)))

        sheet_root = ET.fromstring(zf.read("xl/worksheets/sheet1.xml"))
        rows: dict[int, dict[str, Any]] = {}
        for row in sheet_root.findall("m:sheetData/m:row", NS):
            row_num = int(row.get("r"))
            cells: dict[str, Any] = {}
            for cell in row.findall("m:c", NS):
                ref = cell.get("r")
                col = "".join(ch for ch in ref if ch.isalpha())
                value_node = cell.find("m:v", NS)
                if value_node is None:
                    continue
                if cell.get("t") == "s":
                    cells[col] = shared_strings[int(value_node.text)]
                else:
                    cells[col] = value_node.text
            rows[row_num] = cells
    return rows


def extract_estimates(xlsx_path: Path) -> list[AlexEstimateRow]:
    rows = load_workbook_rows(xlsx_path)
    estimates: list[AlexEstimateRow] = []
    for row_num in sorted(rows):
        if row_num == 1:
            continue
        cells = rows[row_num]
        notes = cells.get("Y") or ""
        if not notes.strip():
            continue
        parsed = _parse_notes(notes)
        cc_flag = cells.get("E")
        if parsed["congestion"] == 0 and str(cc_flag).lower() in {"yes", "true", "1"}:
            parsed["congestion"] = float(CONGESTION_DEFAULT)
        if parsed["materials"] == 0:
            material_w = cells.get("W")
            material_v = cells.get("V")
            if material_w is not None and material_v is not None:
                parsed["materials"] = float(material_w) + float(material_v)
            elif material_w is not None:
                parsed["materials"] = float(material_w)

        estimates.append(
            AlexEstimateRow(
                xlsx_row=row_num,
                client=str(cells.get("F") or "").strip(),
                trade=str(cells.get("O") or "").strip(),
                time_frame=str(cells.get("Q") or cells.get("R") or "").strip(),
                quote_number=cells.get("B"),
                door_no=cells.get("J"),
                **parsed,
            )
        )
    return estimates


def write_json(estimates: list[AlexEstimateRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [row.to_json_dict() for row in estimates]
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def compare_with_app(
    estimates: list[AlexEstimateRow],
    *,
    currency_tolerance: Decimal = Decimal("1"),
    pct_tolerance: Decimal = Decimal("1"),
) -> list[dict[str, Any]]:
    BACKEND = ROOT / "backend"
    sys.path.insert(0, str(BACKEND))
    from datetime import date

    from app.engines.approval_engine import build_calculation_breakdown
    from app.engines.rules_engine import MatchedRule
    from app.models.rate_rule import RateRule
    from app.schemas.calculation import ChargeInput, LabourInput, MaterialInput

    rule = RateRule(
        formula_source="xlsx",
        version="alex-xlsx-verify",
        hourly_rate=Decimal("95"),
        day_rate=Decimal("239.40"),
        direct_hourly_cost=Decimal("30"),
        direct_daily_cost=Decimal("239.40"),
        client_fee_pct=Decimal("0"),
        hourly_overhead_pct=Decimal("0.30"),
        daily_overhead_pct=Decimal("0.20"),
        daily_overhead_long_job_pct=Decimal("0.15"),
        labourer_hourly_cost=Decimal("18.75"),
        labourer_daily_cost=Decimal("150"),
        material_charge_denominator=Decimal("0.20"),
        parking_charge_denominator=Decimal("0.20"),
        congestion_charge_denominator=Decimal("0.20"),
        mround_increment=Decimal("5"),
        oj_uplift_pct=Decimal("10"),
        nhs_overhead_uplift_pct=Decimal("15"),
        eaf_flat_fee=Decimal("1"),
        xlsx_client_name="Lambert Chartered Surveyors",
        xlsx_trade_name="Carpenter",
        material_markup_type="percentage",
        material_markup_value=Decimal("20"),
        vat_rate=Decimal("20"),
        active_from=date(2024, 1, 1),
        is_active=True,
    )
    matched = MatchedRule(rule=rule, match_type="alex-verify")

    results: list[dict[str, Any]] = []
    for row in estimates:
        labour_type = "hourly" if row.helper_type == "hourly" else "day"
        labour_kwargs: dict[str, Any] = {
            "labour_type": labour_type,
            "number_of_engineers": row.engineers,
            "number_of_labourers": row.labourers,
        }
        if labour_type == "hourly":
            labour_kwargs["hours_on_site"] = Decimal(str(row.hours))
        else:
            labour_kwargs["days_on_site"] = Decimal(str(row.days))
            labour_kwargs["labourer_days"] = Decimal(str(row.labourer_days))

        materials = []
        if row.materials > 0:
            materials.append(
                MaterialInput(
                    material_name=f"Materials row {row.xlsx_row}",
                    quantity=Decimal("1"),
                    unit_cost=Decimal(str(row.materials)),
                )
            )
        charges = None
        if row.congestion > 0 or row.parking > 0:
            charges = ChargeInput(
                parking_required=row.parking > 0,
                parking_type="fixed" if row.parking > 0 else None,
                parking_fixed_amount=Decimal(str(row.parking)) if row.parking > 0 else None,
                congestion_required=row.congestion > 0,
                congestion_amount=Decimal(str(row.congestion)),
            )

        breakdown = build_calculation_breakdown(
            labour_items=[LabourInput(**labour_kwargs)],
            material_items=materials,
            charges=charges,
            matched_rule=matched,
            formula_version="alex-xlsx-verify",
        )

        actual = {
            "labour_charge_to_client": float(breakdown.labour_charge_to_client or 0),
            "materials_parking_cc_charge": float(breakdown.materials_parking_cc_charge or 0),
            "profit_gbp": float(breakdown.profit_gbp or 0),
            "profit_pct": float(breakdown.profit_pct or 0),
            "formula_source": breakdown.formula_source,
            "internal_notes_generated": bool(breakdown.internal_notes),
        }
        expected = {
            "labour_charge_to_client": row.expected_labour_charge_to_client,
            "materials_parking_cc_charge": row.expected_materials_parking_cc_charge,
            "profit_gbp": row.expected_profit_gbp,
            "profit_pct": row.expected_profit_pct,
        }
        diffs = {
            key: round(actual[key] - expected[key], 2)
            for key in expected
        }
        passed = (
            abs(Decimal(str(diffs["labour_charge_to_client"]))) <= currency_tolerance
            and abs(Decimal(str(diffs["materials_parking_cc_charge"]))) <= currency_tolerance
            and abs(Decimal(str(diffs["profit_gbp"]))) <= currency_tolerance
            and abs(Decimal(str(diffs["profit_pct"]))) <= pct_tolerance
            and actual["formula_source"] == "xlsx"
            and actual["internal_notes_generated"]
        )

        results.append(
            {
                "xlsx_row": row.xlsx_row,
                "helper_type": row.helper_type,
                "expected": expected,
                "actual": actual,
                "difference": diffs,
                "pass": passed,
            }
        )
    return results


def write_report(results: list[dict[str, Any]], report_path: Path, *, estimates_count: int) -> None:
    passed = sum(1 for r in results if r["pass"])
    total = len(results)
    pct = round((passed / total) * 100, 1) if total else 0.0
    lines = [
        "# Alex XLSX Verification Report",
        "",
        f"Generated from `optimal_estimating_Alex.xlsx`.",
        "",
        "## Summary",
        "",
        f"- Rows parsed: **{estimates_count}**",
        f"- Rows compared: **{total}**",
        f"- Passed: **{passed}**",
        f"- Failed: **{total - passed}**",
        f"- Pass rate: **{pct}%** (target ≥ 95%)",
        "",
        "## Results",
        "",
        "| Row | Helper | Labour £ | Mat/CC £ | Profit £ | Profit % | Pass |",
        "|-----|--------|----------|----------|----------|----------|------|",
    ]
    for item in results:
        exp = item["expected"]
        act = item["actual"]
        diff = item["difference"]
        status = "PASS" if item["pass"] else "FAIL"
        lines.append(
            f"| {item['xlsx_row']} | {item['helper_type']} | "
            f"exp {exp['labour_charge_to_client']:.0f} / act {act['labour_charge_to_client']:.0f} (Δ{diff['labour_charge_to_client']:+.2f}) | "
            f"exp {exp['materials_parking_cc_charge']:.0f} / act {act['materials_parking_cc_charge']:.0f} (Δ{diff['materials_parking_cc_charge']:+.2f}) | "
            f"exp {exp['profit_gbp']:.0f} / act {act['profit_gbp']:.2f} (Δ{diff['profit_gbp']:+.2f}) | "
            f"exp {exp['profit_pct']:.0f}% / act {act['profit_pct']:.2f}% (Δ{diff['profit_pct']:+.2f}) | {status} |"
        )

    failures = [r for r in results if not r["pass"]]
    if failures:
        lines.extend(["", "## Failures", ""])
        for item in failures:
            lines.append(f"### Row {item['xlsx_row']} ({item['helper_type']})")
            lines.append("")
            lines.append("```json")
            lines.append(json.dumps(item, indent=2))
            lines.append("```")
            lines.append("")

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--verify-app", action="store_true", help="Compare extracted rows against live calculation engine")
    args = parser.parse_args()

    if not args.xlsx.exists():
        raise FileNotFoundError(f"Workbook not found: {args.xlsx}")

    estimates = extract_estimates(args.xlsx)
    write_json(estimates, args.json_out)
    print(f"Extracted {len(estimates)} estimate rows -> {args.json_out}")

    if args.verify_app:
        results = compare_with_app(estimates)
        write_report(results, args.report_out, estimates_count=len(estimates))
        passed = sum(1 for r in results if r["pass"])
        print(f"Verification: {passed}/{len(results)} passed -> {args.report_out}")
        if passed / len(results) < 0.95:
            raise SystemExit(1)


if __name__ == "__main__":
    main()
