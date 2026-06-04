from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.calculation_session import CalculationSession
from app.schemas.engineer_session import (
    EngineerDurationType,
    EngineerJobSummary,
    EngineerSessionRead,
    EngineerSiteVisitRead,
    EngineerSiteVisitUpdate,
    EngineerSiteVisitUpdateResponse,
)
from app.schemas.eworks_link import Step1Snapshot, Step2Snapshot, WorkBlockSnapshot
from app.services.eworks_link_service import get_session_by_token
from app.services.eworks_questionnaire_service import format_time_frame

FINANCIAL_RESPONSE_KEYS = frozenset(
    {
        "resolved",
        "breakdown",
        "subtotal",
        "vat_total",
        "final_total",
        "formula_source",
        "internal_notes",
        "profit_gbp",
        "profit_pct",
        "markup_value",
        "client_fee_pct",
        "last_result",
        "rate_rule",
    }
)


def _duration_type_from_block(block: WorkBlockSnapshot) -> EngineerDurationType:
    labour_type = (block.labour_type or "").lower()
    if labour_type == "half_day":
        return "half_day"
    if labour_type == "hourly" or block.engineer_time_unit == "hours":
        return "hourly"
    days = block.days if block.days > 0 else block.engineer_time_value
    if days and days >= 3:
        return "day_3_plus"
    return "day_up_to_2"


def _read_site_visit(block: WorkBlockSnapshot, step2: Step2Snapshot) -> EngineerSiteVisitRead:
    duration_type = _duration_type_from_block(block)
    hours = block.hours if block.hours > 0 else (block.engineer_time_value if block.engineer_time_unit == "hours" else None)
    days = block.days if block.days > 0 else (block.engineer_time_value if block.engineer_time_unit == "days" else None)
    parking_amount = block.parking_fixed_amount
    if block.parking_required and block.parking_type == "hourly" and block.parking_rate_per_hour and block.parking_hours:
        parking_amount = block.parking_rate_per_hour * block.parking_hours
    return EngineerSiteVisitRead(
        scope=block.scope,
        site_notes=block.other_notes,
        findings=block.findings,
        attachments=block.attachments,
        engineer_count=int(block.engineers_needed if block.engineers_required else block.engineers or 0),
        labourer_count=int(block.labour_needed if block.labour_required else block.labourers or 0),
        duration_type=duration_type,
        hours=hours,
        days=days,
        materials_required=block.shelf_materials or step2.shelf_materials,
        unit_cost=block.unit_cost if block.unit_cost > 0 else (step2.unit_cost if step2.unit_cost > 0 else None),
        parking_required=block.parking_required,
        parking_amount=parking_amount,
        congestion_required=block.congestion_required or step2.congestion_required,
        congestion_amount=block.congestion_amount if block.congestion_amount > 0 else step2.congestion_amount,
        ulez_required=step2.ulez_required,
        ulez_amount=step2.ulez_amount if step2.ulez_required else None,
        waste_required=step2.waste_disposal_required,
        waste_amount=step2.waste_disposal_amount if step2.waste_disposal_required else None,
    )


def _ensure_primary_work(step2: Step2Snapshot | None, trade_name: str) -> tuple[Step2Snapshot, WorkBlockSnapshot]:
    if step2 is None:
        step2 = Step2Snapshot()
    if not step2.works:
        block = WorkBlockSnapshot(skill_required=trade_name)
        step2 = step2.model_copy(update={"works": [block]})
    return step2, step2.works[0]


def _apply_duration(
    block: WorkBlockSnapshot,
    *,
    duration_type: EngineerDurationType,
    hours: Decimal | None,
    days: Decimal | None,
    engineer_count: int,
    labourer_count: int,
) -> WorkBlockSnapshot:
    engineers_required = engineer_count > 0
    labour_required = labourer_count > 0 and duration_type != "hourly"
    if duration_type == "hourly":
        time_value = hours or Decimal("1")
        unit = "hours"
        labour_type = "hourly"
        block_hours = time_value
        block_days = Decimal("0")
    elif duration_type == "half_day":
        time_value = days or Decimal("0.5")
        unit = "days"
        labour_type = "half_day"
        block_hours = Decimal("0")
        block_days = time_value
    else:
        time_value = days or Decimal("1")
        unit = "days"
        labour_type = "day"
        block_hours = Decimal("0")
        block_days = time_value

    return block.model_copy(
        update={
            "engineers_required": engineers_required,
            "engineers_needed": engineer_count,
            "engineers": engineer_count,
            "labour_required": labour_required,
            "labour_needed": labourer_count,
            "labourers": labourer_count,
            "engineer_time_unit": unit,
            "engineer_time_value": time_value,
            "labour_type": labour_type,
            "hours": block_hours,
            "days": block_days,
            "labourer_days": Decimal(str(labourer_count)) if labour_required else Decimal("0"),
            "labour_time_value": time_value if labour_required else Decimal("0"),
            "time_frame": format_time_frame(unit, time_value),
        }
    )


def get_engineer_session(db: Session, *, session_id: UUID, session_token: str) -> EngineerSessionRead:
    session = get_session_by_token(db, session_id, session_token)
    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2 = Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None
    step2, block = _ensure_primary_work(step2, step1.trade_name)
    return EngineerSessionRead(
        session_id=session.id,
        status=session.status,
        expires_at=session.expires_at,
        job=EngineerJobSummary(
            quote_number=step1.quote_number,
            job_number=step1.job_number,
            client_name=step1.client_name,
            trade_name=step1.trade_name,
            property_address=step1.property_address,
            engineer_name=step1.engineer_name,
            status=session.status,
        ),
        site_visit=_read_site_visit(block, step2),
    )


def update_engineer_site_visit(
    db: Session,
    *,
    session_id: UUID,
    session_token: str,
    payload: EngineerSiteVisitUpdate,
) -> EngineerSiteVisitUpdateResponse:
    try:
        payload.model_validate_duration()
    except ValueError as exc:
        raise AppError("VALIDATION_ERROR", str(exc), 400) from exc

    session = get_session_by_token(db, session_id, session_token)
    if session.status == "submitted":
        raise AppError("SESSION_SUBMITTED", "Cannot update site visit after submission", 409)

    step1 = Step1Snapshot.model_validate(session.step1_snapshot)
    step2, block = _ensure_primary_work(
        Step2Snapshot.model_validate(session.step2_snapshot) if session.step2_snapshot else None,
        step1.trade_name,
    )

    block = _apply_duration(
        block,
        duration_type=payload.duration_type,
        hours=payload.hours,
        days=payload.days,
        engineer_count=payload.engineer_count,
        labourer_count=payload.labourer_count,
    )
    if payload.scope is not None:
        block = block.model_copy(update={"scope": payload.scope.strip() or None})
    if payload.site_notes is not None:
        block = block.model_copy(update={"other_notes": payload.site_notes.strip() or None})
    if payload.findings is not None:
        block = block.model_copy(update={"findings": payload.findings.strip() or None})
    if payload.materials_required is not None:
        block = block.model_copy(update={"shelf_materials": payload.materials_required.strip() or None})
    if payload.unit_cost is not None:
        block = block.model_copy(update={"unit_cost": payload.unit_cost})

    parking_amount = payload.parking_amount or Decimal("0")
    block = block.model_copy(
        update={
            "parking_required": payload.parking_required,
            "parking_type": "fixed",
            "parking_fixed_amount": parking_amount if payload.parking_required else Decimal("0"),
            "congestion_required": payload.congestion_required,
            "congestion_amount": payload.congestion_amount or Decimal("0"),
        }
    )

    step2 = step2.model_copy(
        update={
            "works": [block],
            "scope": block.scope,
            "other_notes": block.other_notes,
            "findings": block.findings,
            "shelf_materials": block.shelf_materials,
            "unit_cost": block.unit_cost,
            "engineers": block.engineers,
            "labourers": block.labourers,
            "hours": block.hours,
            "days": block.days,
            "labour_type": block.labour_type,
            "labourer_days": block.labourer_days,
            "parking_required": block.parking_required,
            "parking_type": block.parking_type,
            "parking_fixed_amount": block.parking_fixed_amount,
            "congestion_required": block.congestion_required,
            "congestion_amount": block.congestion_amount,
            "ulez_required": payload.ulez_required,
            "ulez_amount": payload.ulez_amount or Decimal("0"),
            "waste_disposal_required": payload.waste_required,
            "waste_disposal_amount": payload.waste_amount or Decimal("0"),
        }
    )

    session.step2_snapshot = step2.model_dump(mode="json")
    db.flush()
    return EngineerSiteVisitUpdateResponse(session_id=session.id, status=session.status)


def assert_no_financial_keys(payload: dict) -> None:
    """Raise if response dict contains known financial keys at any depth."""

    def walk(obj: object, path: str = "") -> None:
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key in FINANCIAL_RESPONSE_KEYS:
                    raise AssertionError(f"Financial key exposed: {path}.{key}".strip("."))
                walk(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for index, item in enumerate(obj):
                walk(item, f"{path}[{index}]")

    walk(payload)
