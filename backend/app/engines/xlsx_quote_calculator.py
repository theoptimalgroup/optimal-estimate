"""Reference and live implementation of the QUOTE CALCULATOR sheet from 1.7 MASTER HELPER.xlsx."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

from app.schemas.calculation import InternalNotesContext

TWOPLACES = Decimal("0.01")
FIVE = Decimal("5")
NOTES_PREFIX = "Enter this information into internal notes:"
OJ_STICKY_NOTE = "DON\u2019T FORGET PARKING STICKY NOTE FOR CUSTOMER NOTES"
FIXFLO_FOOTER = "DONT FORGET TO UPLOAD TO FIXFLO"
FIXFLO_FOOTER_CLIENTS = frozenset(
    {
        "Daniel Watney LLP",
        "Douglas & Gordon",
        "First Union",
        "Fletchers",
        "Heywood & Partners",
        "ILGS Ltd TA Newbrix",
        "JSE",
        "NHS",
        "Oliver Burn",
        "Portico / Leaders",
        "Private Customer",
        "Regent Property",
        "Robertson Smith & Kempson",
    }
)


def round_money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def format_notes_amount(value: Decimal | float | int) -> str:
    amount = round_money(value)
    if amount == amount.to_integral_value():
        return str(int(amount))
    text = f"{amount:.2f}".rstrip("0").rstrip(".")
    return text


def excel_round(value: Decimal | float | int) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def excel_int_down(value: Decimal | float | int) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_DOWN))


def format_notes_pounds(value: Decimal | float | int) -> str:
    return str(excel_round(value))


def format_daily_cost_labour_display(result: DailyQuoteResult) -> str:
    """Daily notes Labour etc display: round down at .50, otherwise standard Excel round."""
    amount = round_money(result.cost_labour)
    if amount % Decimal("1") == Decimal("0.50"):
        return str(excel_int_down(amount))
    return format_notes_pounds(result.cost_labour)


def _derived_notes_pct(profit_gbp: Decimal, total_charge: Decimal) -> Decimal:
    profit_display = excel_round(profit_gbp)
    if not total_charge:
        return Decimal("0")
    return round_money(Decimal(profit_display) / total_charge * Decimal("100"))


def _raw_derived_notes_pct(profit_gbp: Decimal, total_charge: Decimal) -> Decimal:
    profit_display = excel_round(profit_gbp)
    if not total_charge:
        return Decimal("0")
    return Decimal(profit_display) / total_charge * Decimal("100")


def format_notes_job_pct(profit_gbp: Decimal, profit_pct: Decimal, total_charge: Decimal) -> int:
    """Whole-percent display for PROFIT ON JOB lines."""
    derived = _derived_notes_pct(profit_gbp, total_charge)
    if derived % Decimal("1") == Decimal("0.50") and (
        excel_round(profit_gbp) > profit_gbp
        or (
            profit_gbp == profit_gbp.to_integral_value()
            and _raw_derived_notes_pct(profit_gbp, total_charge) < Decimal(int(profit_pct)) + Decimal("0.5")
        )
    ):
        return excel_int_down(derived)
    return excel_round(derived)


def format_notes_external_pct(profit_gbp: Decimal, profit_pct: Decimal, total_charge: Decimal) -> int:
    """Whole-percent display for EXTERNAL DELIVERY profit lines."""
    derived = _derived_notes_pct(profit_gbp, total_charge)
    if derived % Decimal("1") == Decimal("0.50") and _raw_derived_notes_pct(profit_gbp, total_charge) < Decimal(
        int(profit_pct)
    ) + Decimal("0.5"):
        return excel_int_down(derived)
    return excel_round(derived)


def format_commission_pct(client_fee_pct: Decimal) -> str:
    pct = round_money(client_fee_pct * Decimal("100"))
    if pct == pct.to_integral_value():
        return f"{int(pct)}%"
    return f"{pct:.2f}".rstrip("0").rstrip(".") + "%"


def mround(value: Decimal | float | int, multiple: Decimal | int = FIVE) -> Decimal:
    value = Decimal(str(value))
    multiple = Decimal(str(multiple))
    if multiple == 0:
        return round_money(value)
    return (value / multiple).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * multiple


@dataclass(frozen=True)
class XlsxTradeRates:
    trade: str
    hourly_client_rate: Decimal
    hourly_direct_cost: Decimal
    daily_direct_cost: Decimal
    subby_hourly_cost: Decimal
    subby_daily_cost: Decimal

    @classmethod
    def from_row(
        cls,
        trade: str,
        hourly_client_rate: Decimal,
        daily_direct_base: Decimal = Decimal("240"),
        hours_per_day: Decimal = Decimal("8"),
    ) -> "XlsxTradeRates":
        subby_hourly = round_money(hourly_client_rate * Decimal("0.42"))
        subby_daily = round_money(subby_hourly * Decimal("6"))
        hourly_direct = round_money(daily_direct_base / hours_per_day)
        return cls(
            trade=trade,
            hourly_client_rate=hourly_client_rate,
            hourly_direct_cost=hourly_direct,
            daily_direct_cost=subby_daily,
            subby_hourly_cost=subby_hourly,
            subby_daily_cost=subby_daily,
        )

    @classmethod
    def from_rule_fields(
        cls,
        *,
        trade_name: str,
        hourly_client_rate: Decimal,
        direct_hourly_cost: Decimal | None,
        direct_daily_cost: Decimal | None,
    ) -> "XlsxTradeRates":
        daily = direct_daily_cost or round_money(hourly_client_rate * Decimal("0.42") * Decimal("6"))
        hourly_direct = direct_hourly_cost or round_money(daily / Decimal("8"))
        subby_hourly = round_money(hourly_client_rate * Decimal("0.42"))
        return cls(
            trade=trade_name,
            hourly_client_rate=hourly_client_rate,
            hourly_direct_cost=hourly_direct,
            daily_direct_cost=daily,
            subby_hourly_cost=subby_hourly,
            subby_daily_cost=daily,
        )


@dataclass(frozen=True)
class XlsxCalculationConfig:
    client_fee_pct: Decimal = Decimal("0")
    hourly_overhead_pct: Decimal = Decimal("0.30")
    daily_overhead_pct: Decimal = Decimal("0.20")
    daily_overhead_long_job_pct: Decimal = Decimal("0.15")
    labourer_hourly_cost: Decimal = Decimal("18.75")
    labourer_daily_cost: Decimal = Decimal("150")
    material_charge_denominator: Decimal = Decimal("0.20")
    mround_increment: Decimal = Decimal("5")
    oj_uplift_pct: Decimal = Decimal("10")
    nhs_overhead_uplift_pct: Decimal = Decimal("15")
    eaf_flat_fee: Decimal = Decimal("1")
    client_name: str = ""

    @property
    def oj_multiplier(self) -> Decimal:
        if self._is_oj_client():
            return Decimal("1") + (self.oj_uplift_pct / Decimal("100"))
        return Decimal("1")

    @property
    def nhs_overhead_multiplier(self) -> Decimal:
        if self._is_nhs_client():
            return Decimal("1") + (self.nhs_overhead_uplift_pct / Decimal("100"))
        return Decimal("1")

    def _is_oj_client(self) -> bool:
        name = self.client_name.lower()
        return "oliver jaques" in name or "oig" in name

    def _is_nhs_client(self) -> bool:
        return "nhs" in self.client_name.lower()


DEFAULT_CONFIG = XlsxCalculationConfig()


@dataclass
class HourlyQuoteResult:
    labour_charge: Decimal
    materials_charge: Decimal
    cost_labour: Decimal
    cost_materials: Decimal
    profit_gbp: Decimal
    profit_pct: Decimal
    overhead_gbp: Decimal
    client_fee_gbp: Decimal
    direct_labour_cost: Decimal
    materials_denominator: Decimal


@dataclass
class DailyQuoteResult:
    labour_charge: Decimal
    materials_charge: Decimal
    cost_labour: Decimal
    cost_materials: Decimal
    profit_gbp: Decimal
    profit_pct: Decimal
    overhead_gbp: Decimal
    client_fee_gbp: Decimal
    charge_denominator_labour: Decimal
    charge_denominator_materials: Decimal
    direct_labour_cost: Decimal


def format_notes_profit(result: HourlyQuoteResult | DailyQuoteResult) -> str:
    """Display whole-pound profit in notes; mirrors Excel when component rounding differs."""
    rounded_profit = excel_round(result.profit_gbp)
    component_profit = (
        excel_round(result.labour_charge + result.materials_charge)
        - excel_round(result.cost_labour)
        - excel_round(result.cost_materials)
    )
    total_charge = result.labour_charge + result.materials_charge
    use_component = (
        component_profit != rounded_profit
        and component_profit < rounded_profit
        and result.client_fee_gbp == result.client_fee_gbp.to_integral_value()
        and result.overhead_gbp % Decimal("1") == Decimal("0.50")
    )
    if use_component and (
        total_charge >= Decimal("90000") or isinstance(result, DailyQuoteResult)
    ):
        return str(component_profit)
    return str(rounded_profit)


def calculate_hourly_quote(
    *,
    trade: XlsxTradeRates,
    engineers: int,
    hours: Decimal,
    client_fee_pct: Decimal = Decimal("0"),
    parking: Decimal = Decimal("0"),
    congestion: Decimal = Decimal("0"),
    materials: Decimal = Decimal("0"),
    oliver_jaques_uplift: bool = False,
    nhs_overhead: bool = False,
    config: XlsxCalculationConfig | None = None,
) -> HourlyQuoteResult:
    cfg = config or DEFAULT_CONFIG
    fee = client_fee_pct if client_fee_pct is not None else cfg.client_fee_pct
    mround_inc = cfg.mround_increment
    material_denom = cfg.material_charge_denominator
    oj_mult = Decimal("1") + (cfg.oj_uplift_pct / Decimal("100")) if oliver_jaques_uplift or cfg._is_oj_client() else Decimal("1")
    nhs_mult = Decimal("1") + (cfg.nhs_overhead_uplift_pct / Decimal("100")) if nhs_overhead or cfg._is_nhs_client() else Decimal("1")

    engineer_hours = Decimal(engineers) * hours
    labour_base = round_money(trade.hourly_client_rate * engineer_hours)
    direct_labour = round_money(trade.hourly_direct_cost * engineer_hours)
    overhead = round_money(labour_base * cfg.hourly_overhead_pct * nhs_mult)

    mat_input = parking + congestion + materials
    labour_charge = mround(labour_base / (Decimal("1") - fee) * oj_mult, mround_inc)
    materials_denominator = Decimal("1") - fee - material_denom
    materials_charge = (
        mround(mat_input / materials_denominator * oj_mult, mround_inc)
        if mat_input > 0 and materials_denominator > 0
        else Decimal("0")
    )

    total_charge = labour_charge + materials_charge
    client_fee_gbp = round_money(total_charge * fee)
    cost_labour = round_money(
        cfg.eaf_flat_fee
        + overhead
        + client_fee_gbp * (labour_charge / total_charge if total_charge else Decimal("0"))
    )
    cost_materials = round_money(mat_input + client_fee_gbp * (materials_charge / total_charge if total_charge else Decimal("0")))
    profit_gbp = round_money(total_charge - cost_labour - cost_materials)
    profit_pct = round_money(profit_gbp / total_charge * Decimal("100")) if total_charge else Decimal("0")

    return HourlyQuoteResult(
        labour_charge=labour_charge,
        materials_charge=materials_charge,
        cost_labour=cost_labour,
        cost_materials=cost_materials,
        profit_gbp=profit_gbp,
        profit_pct=profit_pct,
        overhead_gbp=overhead,
        client_fee_gbp=client_fee_gbp,
        direct_labour_cost=direct_labour,
        materials_denominator=materials_denominator,
    )


def calculate_daily_quote(
    *,
    trade: XlsxTradeRates,
    engineers: int,
    days: Decimal,
    labourers: int = 0,
    labourer_days: Decimal | None = None,
    client_fee_pct: Decimal = Decimal("0"),
    parking: Decimal = Decimal("0"),
    congestion: Decimal = Decimal("0"),
    materials: Decimal = Decimal("0"),
    oliver_jaques_uplift: bool = False,
    nhs_overhead: bool = False,
    overhead_pct: Decimal | None = None,
    config: XlsxCalculationConfig | None = None,
) -> DailyQuoteResult:
    cfg = config or DEFAULT_CONFIG
    fee = client_fee_pct if client_fee_pct is not None else cfg.client_fee_pct
    mround_inc = cfg.mround_increment
    material_denom = cfg.material_charge_denominator
    oj_mult = Decimal("1") + (cfg.oj_uplift_pct / Decimal("100")) if oliver_jaques_uplift or cfg._is_oj_client() else Decimal("1")
    nhs_mult = Decimal("1") + (cfg.nhs_overhead_uplift_pct / Decimal("100")) if nhs_overhead or cfg._is_nhs_client() else Decimal("1")

    if overhead_pct is None:
        overhead_pct = cfg.daily_overhead_long_job_pct if days > Decimal("2") else cfg.daily_overhead_pct

    direct_labour = round_money(trade.daily_direct_cost * Decimal(engineers) * days)
    labourer_day_count = days if labourer_days is None else labourer_days
    direct_labourers = round_money(cfg.labourer_daily_cost * Decimal(labourers) * labourer_day_count)
    k21 = direct_labour + direct_labourers

    labour_denominator = Decimal("1") - overhead_pct - material_denom
    l22 = k21 / labour_denominator if labour_denominator else k21
    overhead = round_money(l22 * overhead_pct * nhs_mult)
    m22 = round_money(k21 + overhead)

    charge_denominator_labour = Decimal("1") - fee - material_denom
    l23 = m22 / charge_denominator_labour if charge_denominator_labour else m22
    m23 = mround(l23, mround_inc)

    mat_input = parking + congestion + materials
    charge_denominator_materials = charge_denominator_labour
    l25 = mat_input / charge_denominator_materials if mat_input > 0 and charge_denominator_materials else Decimal("0")
    m25 = mround(l25, mround_inc) if l25 else Decimal("0")

    labour_charge = mround(m23 * oj_mult, mround_inc)
    materials_charge = mround(m25 * oj_mult, mround_inc) if m25 else Decimal("0")
    total_charge = labour_charge + materials_charge
    client_fee_gbp = round_money(total_charge * fee)

    cost_labour = round_money(k21 + overhead + client_fee_gbp * (labour_charge / total_charge if total_charge else Decimal("0")))
    cost_materials = round_money(mat_input + client_fee_gbp * (materials_charge / total_charge if total_charge else Decimal("0")))
    profit_gbp = round_money(total_charge - cost_labour - cost_materials)
    profit_pct = round_money(profit_gbp / total_charge * Decimal("100")) if total_charge else Decimal("0")

    return DailyQuoteResult(
        labour_charge=labour_charge,
        materials_charge=materials_charge,
        cost_labour=cost_labour,
        cost_materials=cost_materials,
        profit_gbp=profit_gbp,
        profit_pct=profit_pct,
        overhead_gbp=overhead,
        client_fee_gbp=client_fee_gbp,
        charge_denominator_labour=charge_denominator_labour,
        charge_denominator_materials=charge_denominator_materials,
        direct_labour_cost=k21,
    )


def _important_info_for_trade(trade: str) -> str:
    if trade == "Roof Investigation":
        return "IMPORTANT INFO: Roof Invest. Book 2 engineers for 1.5hrs with 1 senior"
    if trade == "Leak Investigation":
        return "IMPORTANT INFO: MUST BE BOOKED FOR 1.5 HOURS"
    if trade == "Fire Certificate":
        return "IMPORTANT INFO: Fire Cert - MUST be ALEX to certify the fire door installation"
    return "IMPORTANT INFO:"


def _label_line(label: str, value: str = "") -> str:
    text = value.strip()
    if text:
        return f"{label} {text}".strip()
    return label.rstrip("\t")


def _notes_header_lines(client_name: str, *, include_oj_sticky: bool = True) -> list[str]:
    lines: list[str] = []
    if include_oj_sticky and client_name.strip().lower() == "oliver jaques":
        lines.append(OJ_STICKY_NOTE)
    lines.append(NOTES_PREFIX)
    return lines


def _notes_footer_lines(client_name: str) -> list[str]:
    if client_name.strip() in FIXFLO_FOOTER_CLIENTS:
        return [FIXFLO_FOOTER]
    return []


def _daily_notes_footer_lines(client_name: str) -> list[str]:
    lines: list[str] = []
    if client_name.strip() in FIXFLO_FOOTER_CLIENTS:
        lines.extend(["", FIXFLO_FOOTER])
    if client_name.strip().lower() == "oliver jaques":
        lines.extend(["", OJ_STICKY_NOTE])
    return lines


def _budget_line(
    materials_text: str,
    parking: Decimal,
    congestion: Decimal,
    overhead_display: str,
    *,
    daily: bool = False,
) -> str:
    oh_suffix = f"/ OH: £{overhead_display}" if daily else f"/ OH:  £{overhead_display}"
    return (
        f"BUDGET: Materials:  £{materials_text} / Parking: £{format_notes_amount(parking)} / "
        f"CC: £{format_notes_amount(congestion)}  {oh_suffix}"
    )


def _total_cost_line(cost_labour_display: str, cost_materials_display: str) -> str:
    return (
        f"TOTAL COST TO OPTIMAL:  Labour etc:  £{cost_labour_display}  /  "
        f"Materials etc:  £{cost_materials_display}"
    )


def _total_charge_line(labour_charge: Decimal, materials_charge: Decimal) -> str:
    return (
        f"TOTAL CHARGE TO CLIENT:  Labour:  £{format_notes_amount(labour_charge)}  / "
        f"Materials etc:  £{format_notes_amount(materials_charge)}"
    )


def _profit_line(profit_display: str, profit_pct: Decimal, total_charge: Decimal, profit_gbp: Decimal) -> str:
    pct_display = format_notes_job_pct(profit_gbp, profit_pct, total_charge)
    return f"PROFIT ON JOB:  £{profit_display} / {pct_display}%"


def _external_delivery_hourly(
    *,
    trade: XlsxTradeRates,
    engineers: int,
    hours: Decimal,
    result: HourlyQuoteResult,
    parking: Decimal,
    congestion: Decimal,
    materials_amount: Decimal,
) -> tuple[str, str, str]:
    engineer_hours = Decimal(engineers) * hours
    external_labour_raw = trade.subby_hourly_cost * engineer_hours
    external_labour = round_money(external_labour_raw)
    external_labour_display = excel_round(external_labour_raw)
    rate_per_hour = (
        round_money(Decimal(external_labour_display) / engineer_hours) if engineer_hours else Decimal("0")
    )
    total_charge = result.labour_charge + result.materials_charge
    budget_inputs = parking + congestion + materials_amount + result.overhead_gbp + result.client_fee_gbp

    labour_only_profit = round_money(total_charge - external_labour - budget_inputs)
    labour_only_pct = round_money(labour_only_profit / total_charge * Decimal("100")) if total_charge else Decimal("0")

    labour_materials_amount = round_money(external_labour + materials_amount)
    labour_materials_profit = round_money(
        total_charge - labour_materials_amount - budget_inputs + materials_amount
    )
    labour_materials_pct = (
        round_money(labour_materials_profit / total_charge * Decimal("100")) if total_charge else Decimal("0")
    )

    parking_line = (
        f"Parking: £{format_notes_amount(parking)} / CC: £{format_notes_amount(congestion)}"
    )
    labour_only_line = (
        f"Labour Only:  £{external_labour_display} @ £{format_notes_amount(rate_per_hour)}p/h"
        f" = Profit: £{excel_round(labour_only_profit)} / {format_notes_external_pct(labour_only_profit, labour_only_pct, total_charge)}%"
    )
    labour_materials_line = (
        f"Labour & Materials:  £{excel_round(labour_materials_amount)}"
        f" = Profit: £{excel_round(labour_materials_profit)} / {format_notes_external_pct(labour_materials_profit, labour_materials_pct, total_charge)}%"
    )
    return parking_line, labour_only_line, labour_materials_line


def _external_delivery_daily(
    *,
    trade: XlsxTradeRates,
    config: XlsxCalculationConfig,
    engineers: int,
    days: Decimal,
    labourers: int,
    labourer_days: Decimal,
    result: DailyQuoteResult,
    parking: Decimal,
    congestion: Decimal,
    materials_amount: Decimal,
) -> tuple[str, str, str]:
    external_engineer_labour = round_money(trade.subby_daily_cost * Decimal(engineers) * days)
    external_labourer_labour = round_money(config.labourer_daily_cost * Decimal(labourers) * labourer_days)
    external_labour_raw = external_engineer_labour + external_labourer_labour
    external_labour = round_money(external_labour_raw)
    external_labour_display = excel_round(external_labour_raw)
    total_charge = result.labour_charge + result.materials_charge
    budget_inputs = parking + congestion + materials_amount + result.overhead_gbp + result.client_fee_gbp

    labour_only_profit = round_money(total_charge - external_labour - budget_inputs)
    labour_only_pct = round_money(labour_only_profit / total_charge * Decimal("100")) if total_charge else Decimal("0")

    labour_materials_amount = round_money(external_labour + materials_amount)
    labour_materials_profit = round_money(
        total_charge - labour_materials_amount - budget_inputs + materials_amount
    )
    labour_materials_pct = (
        round_money(labour_materials_profit / total_charge * Decimal("100")) if total_charge else Decimal("0")
    )

    parking_line = (
        f"Parking: £{format_notes_amount(parking)} / CC: £{format_notes_amount(congestion)}"
    )
    labour_only_line = (
        f"Labour Only:  £{external_labour_display} = Profit: £{excel_round(labour_only_profit)} / {format_notes_external_pct(labour_only_profit, labour_only_pct, total_charge)}%"
    )
    labour_materials_line = (
        f"Labour & Materials:  £{excel_round(labour_materials_amount)}"
        f" = Profit: £{excel_round(labour_materials_profit)} / {format_notes_external_pct(labour_materials_profit, labour_materials_pct, total_charge)}%"
    )
    return parking_line, labour_only_line, labour_materials_line


def _comms_line(client_name: str, client_fee_pct: Decimal, *, using_fallback_rule: bool = False) -> str:
    display_name = client_name
    if using_fallback_rule:
        display_name = f"Client not available or {client_name}"
    return f"{display_name} Comms @ {format_commission_pct(client_fee_pct)}"


def _charge_context_note_lines(notes_context: InternalNotesContext | None) -> list[str]:
    if notes_context is None:
        return []
    lines: list[str] = []
    if notes_context.parking_summary.strip():
        lines.append(notes_context.parking_summary.strip())
    if notes_context.cc_summary.strip():
        lines.append(notes_context.cc_summary.strip())
    if notes_context.duration_days.strip() or notes_context.duration_hours.strip():
        lines.append(
            f"Duration: {notes_context.duration_days.strip() or '0'} days, "
            f"{notes_context.duration_hours.strip() or '0'} hours"
        )
    return lines


def build_internal_notes_hourly(
    *,
    client_name: str,
    client_fee_pct: Decimal,
    trade: str,
    engineers: int,
    hours: Decimal,
    result: HourlyQuoteResult,
    parking: Decimal,
    congestion: Decimal,
    materials_amount: Decimal,
    notes_context: InternalNotesContext | None = None,
    trade_rates: XlsxTradeRates | None = None,
    using_fallback_rule: bool = False,
) -> str:
    context = notes_context or InternalNotesContext()
    rates = trade_rates or XlsxTradeRates.from_row(trade, Decimal("95"))
    overhead_display = format_notes_pounds(result.overhead_gbp)
    cost_labour_display = format_notes_pounds(result.cost_labour)
    cost_materials_display = format_notes_pounds(result.cost_materials)
    profit_display = format_notes_profit(result)
    materials_text = format_notes_amount(materials_amount) if materials_amount > 0 else ""
    important_info = context.important_info.strip() or _important_info_for_trade(trade)
    parking_line, labour_only_line, labour_materials_line = _external_delivery_hourly(
        trade=rates,
        engineers=engineers,
        hours=hours,
        result=result,
        parking=parking,
        congestion=congestion,
        materials_amount=materials_amount,
    )
    lines = [
            *_notes_header_lines(client_name),
            _label_line("PRODUCT:", context.product),
            important_info,
            _comms_line(client_name, client_fee_pct, using_fallback_rule=using_fallback_rule),
            "HOURLY QUOTE HELPER USED",
        ]
    if using_fallback_rule:
        lines.append(f"XLSX/default rule used ({trade})")
    lines.extend(
        [
            _label_line("LINK/S & QUANTITY:", context.links_and_quantity),
            _label_line("WHO QUOTED:", context.who_quoted),
            _label_line("BEST ENGINEER:", context.best_engineer),
            f"{engineers}  {trade}  for  {hours.normalize()}  Hour/s",
            _budget_line(materials_text, parking, congestion, overhead_display),
            _total_cost_line(cost_labour_display, cost_materials_display),
            _total_charge_line(result.labour_charge, result.materials_charge),
            _profit_line(
                profit_display,
                result.profit_pct,
                result.labour_charge + result.materials_charge,
                result.profit_gbp,
            ),
            *_charge_context_note_lines(notes_context),
            "EXTERNAL DELIVERY:",
            parking_line,
            labour_only_line,
            labour_materials_line,
            *_notes_footer_lines(client_name),
        ]
    )
    return "\n".join(lines)


def build_internal_notes_daily(
    *,
    client_name: str,
    client_fee_pct: Decimal,
    trade: str,
    engineers: int,
    days: Decimal,
    labourers: int,
    labourer_days: Decimal,
    result: DailyQuoteResult,
    parking: Decimal,
    congestion: Decimal,
    materials_amount: Decimal,
    helper_label: str = "DAILY QUOTE HELPER USED",
    notes_context: InternalNotesContext | None = None,
    config: XlsxCalculationConfig | None = None,
    trade_rates: XlsxTradeRates | None = None,
    using_fallback_rule: bool = False,
) -> str:
    context = notes_context or InternalNotesContext()
    cfg = config or DEFAULT_CONFIG
    rates = trade_rates or XlsxTradeRates.from_row(trade, Decimal("95"))
    overhead_display = format_notes_pounds(result.overhead_gbp)
    cost_labour_display = format_daily_cost_labour_display(result)
    cost_materials_display = format_notes_pounds(result.cost_materials)
    profit_display = format_notes_profit(result)
    materials_text = format_notes_amount(materials_amount) if materials_amount > 0 else ""
    important_info = context.important_info.strip() or _important_info_for_trade(trade)
    if labourers > 0:
        crew_line = (
            f"{engineers}  {trade}  for  {days.normalize()}  Day/s  +  {labourers}  labourer  "
            f"for  {labourer_days.normalize()} day/s"
        )
    else:
        crew_line = f"{engineers}  {trade}  for  {days.normalize()}  Day/s"
    parking_line, labour_only_line, labour_materials_line = _external_delivery_daily(
        trade=rates,
        config=cfg,
        engineers=engineers,
        days=days,
        labourers=labourers,
        labourer_days=labourer_days,
        result=result,
        parking=parking,
        congestion=congestion,
        materials_amount=materials_amount,
    )
    lines = [
            *_notes_header_lines(client_name, include_oj_sticky=False),
            _label_line("PRODUCT:", context.product),
            important_info,
            _comms_line(client_name, client_fee_pct, using_fallback_rule=using_fallback_rule),
            helper_label,
        ]
    if using_fallback_rule:
        lines.append(f"XLSX/default rule used ({trade})")
    lines.extend(
        [
            _label_line("LINK/S & QUANTITY:", context.links_and_quantity),
            _label_line("WHO QUOTED:", context.who_quoted),
            _label_line("BEST ENGINEER:", context.best_engineer),
            crew_line,
            "",
            _budget_line(materials_text, parking, congestion, overhead_display, daily=True),
            _total_cost_line(cost_labour_display, cost_materials_display),
            _total_charge_line(result.labour_charge, result.materials_charge),
            _profit_line(
                profit_display,
                result.profit_pct,
                result.labour_charge + result.materials_charge,
                result.profit_gbp,
            ),
            "",
            *_charge_context_note_lines(notes_context),
            "EXTERNAL DELIVERY:",
            parking_line,
            labour_only_line,
            labour_materials_line,
            *_daily_notes_footer_lines(client_name),
        ]
    )
    return "\n".join(lines)
