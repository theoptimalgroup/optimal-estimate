from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.calculation import ChargeInput, LabourInput, MaterialInput


TWOPLACES = Decimal("0.01")


def round_money(value: Decimal) -> Decimal:
    return value.quantize(TWOPLACES, rounding=ROUND_HALF_UP)


@dataclass
class LabourResult:
    total: Decimal
    formula: str
    rate_used: Decimal
    minimum_applied: bool = False


def calculate_labour(
    labour_type: str,
    engineers: int,
    hours: Decimal | None,
    days: Decimal | None,
    hourly_rate: Decimal | None,
    half_day_rate: Decimal | None,
    day_rate: Decimal | None,
    minimum_hours: Decimal | None = None,
    minimum_charge: Decimal | None = None,
    manual_override: bool = False,
    manual_rate: Decimal | None = None,
    override_reason: str | None = None,
) -> LabourResult:
    if manual_override and manual_rate is not None:
        if labour_type == "hourly":
            hours_val = hours or Decimal("0")
            total = round_money(Decimal(engineers) * hours_val * manual_rate)
            return LabourResult(total=total, formula=f"{engineers} × {hours_val} × {manual_rate} (override)", rate_used=manual_rate)
        if labour_type == "half_day":
            total = round_money(Decimal(engineers) * manual_rate)
            return LabourResult(total=total, formula=f"{engineers} × {manual_rate} (override)", rate_used=manual_rate)
        days_val = days or Decimal("0")
        total = round_money(Decimal(engineers) * days_val * manual_rate)
        return LabourResult(total=total, formula=f"{engineers} × {days_val} × {manual_rate} (override)", rate_used=manual_rate)

    minimum_applied = False
    if labour_type == "hourly":
        hours_val = hours or Decimal("0")
        if minimum_hours and hours_val < minimum_hours:
            hours_val = minimum_hours
            minimum_applied = True
        rate = hourly_rate or Decimal("0")
        total = round_money(Decimal(engineers) * hours_val * rate)
        if minimum_charge and total < minimum_charge:
            total = round_money(minimum_charge)
            minimum_applied = True
        return LabourResult(
            total=total,
            formula=f"{engineers} × {hours_val} × {rate}",
            rate_used=rate,
            minimum_applied=minimum_applied,
        )

    if labour_type == "half_day":
        rate = half_day_rate or Decimal("0")
        total = round_money(Decimal(engineers) * rate)
        if minimum_charge and total < minimum_charge:
            total = round_money(minimum_charge)
            minimum_applied = True
        return LabourResult(total=total, formula=f"{engineers} × {rate}", rate_used=rate, minimum_applied=minimum_applied)

    days_val = days or Decimal("0")
    rate = day_rate or Decimal("0")
    total = round_money(Decimal(engineers) * days_val * rate)
    if minimum_charge and total < minimum_charge:
        total = round_money(minimum_charge)
        minimum_applied = True
    return LabourResult(
        total=total,
        formula=f"{engineers} × {days_val} × {rate}",
        rate_used=rate,
        minimum_applied=minimum_applied,
    )


@dataclass
class MaterialResult:
    base_cost: Decimal
    markup_total: Decimal
    sell_total: Decimal
    formula: str


def calculate_material(
    quantity: Decimal,
    unit_cost: Decimal,
    delivery_cost: Decimal,
    markup_type: str,
    markup_value: Decimal,
    rule_markup_type: str | None = None,
    rule_markup_value: Decimal | None = None,
) -> MaterialResult:
    base_cost = round_money(quantity * unit_cost + delivery_cost)
    effective_type = markup_type if markup_type != "none" else (rule_markup_type or "none")
    effective_value = markup_value if markup_type != "none" else (rule_markup_value or Decimal("0"))

    if effective_type == "percentage":
        markup_total = round_money(base_cost * effective_value / Decimal("100"))
        formula = f"({quantity} × {unit_cost} + {delivery_cost}) + {effective_value}%"
    elif effective_type == "fixed":
        markup_total = round_money(effective_value)
        formula = f"({quantity} × {unit_cost} + {delivery_cost}) + {effective_value}"
    else:
        markup_total = Decimal("0")
        formula = f"{quantity} × {unit_cost} + {delivery_cost}"

    sell_total = round_money(base_cost + markup_total)
    return MaterialResult(base_cost=base_cost, markup_total=markup_total, sell_total=sell_total, formula=formula)


@dataclass
class ChargeResult:
    parking_total: Decimal
    congestion_total: Decimal
    ulez_total: Decimal
    waste_total: Decimal
    travel_total: Decimal
    other_total: Decimal
    breakdown: list[tuple[str, str, Decimal]]


def calculate_charges(charges: ChargeInput | None) -> ChargeResult:
    if charges is None:
        return ChargeResult(
            parking_total=Decimal("0"),
            congestion_total=Decimal("0"),
            ulez_total=Decimal("0"),
            waste_total=Decimal("0"),
            travel_total=Decimal("0"),
            other_total=Decimal("0"),
            breakdown=[],
        )

    breakdown: list[tuple[str, str, Decimal]] = []
    parking_total = Decimal("0")
    if charges.parking_required:
        # Parking cost multiplies by vehicle count (same rule as work_parking_raw / quote_parking_raw).
        vehicles = Decimal(max(1, charges.parking_vehicles or 1))
        if charges.parking_type == "hourly":
            rate = charges.parking_rate_per_hour or Decimal("0")
            hours = charges.parking_hours or Decimal("0")
            parking_total = round_money(rate * hours * vehicles)
            vehicle_note = f" × {int(vehicles)} vehicles" if vehicles > 1 else ""
            breakdown.append(("Parking", f"{rate} × {hours}{vehicle_note}", parking_total))
        elif charges.parking_type == "fixed":
            base = charges.parking_fixed_amount or Decimal("0")
            parking_total = round_money(base * vehicles)
            vehicle_note = f" × {int(vehicles)} vehicles" if vehicles > 1 else ""
            breakdown.append(("Parking", f"Fixed {base}{vehicle_note}", parking_total))
        elif charges.parking_type == "included":
            breakdown.append(("Parking", "Included", Decimal("0")))
        elif charges.parking_type == "not_chargeable":
            breakdown.append(("Parking", "Not chargeable", Decimal("0")))

    congestion_total = round_money(charges.congestion_amount) if charges.congestion_required else Decimal("0")
    if charges.congestion_required:
        breakdown.append(("Congestion", str(charges.congestion_amount), congestion_total))

    ulez_total = round_money(charges.ulez_amount) if charges.ulez_required else Decimal("0")
    if charges.ulez_required:
        breakdown.append(("ULEZ", str(charges.ulez_amount), ulez_total))

    waste_total = round_money(charges.waste_disposal_amount) if charges.waste_disposal_required else Decimal("0")
    if charges.waste_disposal_required:
        breakdown.append(("Waste Disposal", str(charges.waste_disposal_amount), waste_total))

    travel_total = round_money(charges.travel_charge)
    if travel_total > 0:
        breakdown.append(("Travel", str(charges.travel_charge), travel_total))

    other_total = round_money(charges.other_charge)
    if other_total > 0:
        breakdown.append(("Other", charges.other_charge_reason or "Other charge", other_total))

    return ChargeResult(
        parking_total=parking_total,
        congestion_total=congestion_total,
        ulez_total=ulez_total,
        waste_total=waste_total,
        travel_total=travel_total,
        other_total=other_total,
        breakdown=breakdown,
    )


def calculate_vat(subtotal: Decimal, vat_rate: Decimal) -> Decimal:
    if vat_rate <= 0:
        return Decimal("0.00")
    return round_money(subtotal * vat_rate / Decimal("100"))


def calculate_combined_labour(
    labour_type: str,
    engineers: int,
    labourers: int,
    hours: Decimal | None,
    days: Decimal | None,
    hourly_rate: Decimal | None,
    half_day_rate: Decimal | None,
    day_rate: Decimal | None,
    labourer_hourly_rate: Decimal | None = None,
    labourer_half_day_rate: Decimal | None = None,
    labourer_day_rate: Decimal | None = None,
    minimum_hours: Decimal | None = None,
    minimum_charge: Decimal | None = None,
    manual_override: bool = False,
    manual_rate: Decimal | None = None,
) -> LabourResult:
    engineer_result = calculate_labour(
        labour_type=labour_type,
        engineers=max(engineers, 0),
        hours=hours,
        days=days,
        hourly_rate=hourly_rate,
        half_day_rate=half_day_rate,
        day_rate=day_rate,
        minimum_hours=minimum_hours,
        minimum_charge=None,
        manual_override=manual_override,
        manual_rate=manual_rate,
    )
    if labourers <= 0:
        total = engineer_result.total
        if minimum_charge and total < minimum_charge:
            total = round_money(minimum_charge)
            engineer_result.minimum_applied = True
        engineer_result.total = total
        return engineer_result

    if labour_type == "hourly":
        hours_val = hours or Decimal("0")
        if minimum_hours and hours_val < minimum_hours:
            hours_val = minimum_hours
        labourer_rate = labourer_hourly_rate or Decimal("0")
        labourer_total = round_money(Decimal(labourers) * hours_val * labourer_rate)
        total = round_money(engineer_result.total + labourer_total)
        formula = f"{engineer_result.formula} + {labourers} × {hours_val} × {labourer_rate}"
    elif labour_type == "half_day":
        labourer_rate = labourer_half_day_rate or Decimal("0")
        labourer_total = round_money(Decimal(labourers) * labourer_rate)
        total = round_money(engineer_result.total + labourer_total)
        formula = f"{engineer_result.formula} + {labourers} × {labourer_rate}"
    else:
        days_val = days or Decimal("0")
        labourer_rate = labourer_day_rate or Decimal("0")
        labourer_total = round_money(Decimal(labourers) * days_val * labourer_rate)
        total = round_money(engineer_result.total + labourer_total)
        formula = f"{engineer_result.formula} + {labourers} × {days_val} × {labourer_rate}"

    if minimum_charge and total < minimum_charge:
        total = round_money(minimum_charge)
        return LabourResult(total=total, formula=formula, rate_used=engineer_result.rate_used, minimum_applied=True)
    return LabourResult(total=total, formula=formula, rate_used=engineer_result.rate_used, minimum_applied=engineer_result.minimum_applied)


def calculate_margin(sell_total: Decimal, base_cost: Decimal) -> Decimal:
    if sell_total <= 0:
        return Decimal("0")
    return round_money(((sell_total - base_cost) / sell_total) * Decimal("100"))
