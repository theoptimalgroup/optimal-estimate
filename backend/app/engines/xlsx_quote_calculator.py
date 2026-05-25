"""Reference and live implementation of the QUOTE CALCULATOR sheet from 1.7 MASTER HELPER.xlsx."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.schemas.calculation import InternalNotesContext

TWOPLACES = Decimal("0.01")
FIVE = Decimal("5")


def round_money(value: Decimal | float | int) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def format_notes_amount(value: Decimal | float | int) -> str:
    amount = round_money(value)
    if amount == amount.to_integral_value():
        return str(int(amount))
    text = f"{amount:.2f}".rstrip("0").rstrip(".")
    return text


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
    return f"{label}\t{text}" if text else f"{label}\t"


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
    external_labour = round_money(trade.subby_hourly_cost * engineer_hours)
    external_labour_display = round_money(external_labour).to_integral_value()
    rate_per_hour = round_money(Decimal(external_labour_display) / engineer_hours) if engineer_hours else Decimal("0")
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
        f" = Profit: £{labour_only_profit.to_integral_value()} / {labour_only_pct:.0f}%"
    )
    labour_materials_line = (
        f"Labour & Materials:  £{labour_materials_amount.to_integral_value()}"
        f" = Profit: £{labour_materials_profit.to_integral_value()} / {labour_materials_pct:.0f}%"
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
    external_labour = round_money(external_engineer_labour + external_labourer_labour)
    external_labour_display = external_labour.to_integral_value()
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
        f"Labour Only:  £{external_labour_display} = Profit: £{labour_only_profit.to_integral_value()} / {labour_only_pct:.0f}%"
    )
    labour_materials_line = (
        f"Labour & Materials:  £{labour_materials_amount.to_integral_value()}"
        f" = Profit: £{labour_materials_profit.to_integral_value()} / {labour_materials_pct:.0f}%"
    )
    return parking_line, labour_only_line, labour_materials_line


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
) -> str:
    context = notes_context or InternalNotesContext()
    rates = trade_rates or XlsxTradeRates.from_row(trade, Decimal("95"))
    overhead_display = round_money(result.overhead_gbp).to_integral_value()
    cost_labour_display = round_money(result.cost_labour).to_integral_value()
    cost_materials_display = round_money(result.cost_materials).to_integral_value()
    profit_display = round_money(result.profit_gbp).to_integral_value()
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
    return "\n".join(
        [
            _label_line("PRODUCT:", context.product),
            important_info,
            f"{client_name} Comms @ {round_money(client_fee_pct * Decimal('100')):.0f}%",
            "HOURLY QUOTE HELPER USED",
            _label_line("LINK/S & QUANTITY:", context.links_and_quantity),
            _label_line("WHO QUOTED:", context.who_quoted),
            _label_line("BEST ENGINEER:", context.best_engineer),
            f"{engineers}  {trade}  for  {hours.normalize()}  Hour/s",
            "",
            (
                f"BUDGET: Materials: £{materials_text} / Parking: £{format_notes_amount(parking)} / "
                f"CC: £{format_notes_amount(congestion)} / OH: £{overhead_display}"
            ),
            f"TOTAL COST TO OPTIMAL: Labour etc: £{cost_labour_display} / Materials etc: £{cost_materials_display}",
            (
                f"TOTAL CHARGE TO CLIENT: Labour: £{format_notes_amount(result.labour_charge)} / "
                f"Materials etc: £{format_notes_amount(result.materials_charge)}"
            ),
            f"PROFIT ON JOB: £{profit_display} / {result.profit_pct:.0f}%",
            "",
            "EXTERNAL DELIVERY:",
            parking_line,
            labour_only_line,
            labour_materials_line,
        ]
    )


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
) -> str:
    context = notes_context or InternalNotesContext()
    cfg = config or DEFAULT_CONFIG
    rates = trade_rates or XlsxTradeRates.from_row(trade, Decimal("95"))
    overhead_display = round_money(result.overhead_gbp).to_integral_value()
    cost_labour_display = round_money(result.cost_labour).to_integral_value()
    cost_materials_display = round_money(result.cost_materials).to_integral_value()
    profit_display = round_money(result.profit_gbp).to_integral_value()
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
    return "\n".join(
        [
            _label_line("PRODUCT:", context.product),
            important_info,
            f"{client_name} Comms @ {round_money(client_fee_pct * Decimal('100')):.0f}%",
            helper_label,
            _label_line("LINK/S & QUANTITY:", context.links_and_quantity),
            _label_line("WHO QUOTED:", context.who_quoted),
            _label_line("BEST ENGINEER:", context.best_engineer),
            crew_line,
            "",
            (
                f"BUDGET: Materials: £{materials_text} / Parking: £{format_notes_amount(parking)} / "
                f"CC: £{format_notes_amount(congestion)} / OH: £{overhead_display}"
            ),
            f"TOTAL COST TO OPTIMAL: Labour etc: £{cost_labour_display} / Materials etc: £{cost_materials_display}",
            (
                f"TOTAL CHARGE TO CLIENT: Labour: £{format_notes_amount(result.labour_charge)} / "
                f"Materials etc: £{format_notes_amount(result.materials_charge)}"
            ),
            f"PROFIT ON JOB: £{profit_display} / {result.profit_pct:.0f}%",
            "",
            "EXTERNAL DELIVERY:",
            parking_line,
            labour_only_line,
            labour_materials_line,
        ]
    )
