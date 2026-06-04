from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.calculation_session import CalculationSession
from app.models.client import Client
from app.models.rate_rule import RateRule
from app.schemas.client_admin import ClientDetailRead, ClientListRead
from app.services.client_service import client_search_filter, normalize_client_name


def _client_counts(db: Session, client_id: UUID) -> tuple[int, int]:
    rate_rules_count = db.scalar(select(func.count()).select_from(RateRule).where(RateRule.client_id == client_id)) or 0
    sessions_count = (
        db.scalar(
            select(func.count()).select_from(CalculationSession).where(CalculationSession.client_id == client_id)
        )
        or 0
    )
    return rate_rules_count, sessions_count


def _client_to_read(db: Session, client: Client) -> ClientListRead:
    rate_rules_count, sessions_count = _client_counts(db, client.id)
    aliases = [alias.alias_name for alias in client.client_aliases]
    return ClientListRead(
        id=client.id,
        name=client.name,
        billing_email=client.billing_email,
        default_vat_rate=client.default_vat_rate,
        is_active=client.is_active,
        aliases=aliases,
        rate_rules_count=rate_rules_count,
        calculation_sessions_count=sessions_count,
        created_at=client.created_at,
        updated_at=client.updated_at,
    )


def list_clients_admin(
    db: Session,
    *,
    search: str | None = None,
    active: bool | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ClientListRead], int]:
    limit = min(max(limit, 1), 200)
    offset = max(offset, 0)

    query = select(Client).options(selectinload(Client.client_aliases))
    search_filter = client_search_filter(search)
    if search_filter is not None:
        query = query.where(search_filter)

    if active is not None:
        query = query.where(Client.is_active.is_(active))

    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    clients = db.scalars(query.order_by(Client.name).offset(offset).limit(limit)).all()
    return [_client_to_read(db, client) for client in clients], total


def get_client_admin(db: Session, client_id: UUID) -> ClientDetailRead | None:
    client = db.scalar(
        select(Client).options(selectinload(Client.client_aliases)).where(Client.id == client_id)
    )
    if client is None:
        return None
    return ClientDetailRead.model_validate(_client_to_read(db, client).model_dump())


def update_client_admin(
    db: Session,
    client_id: UUID,
    *,
    name: str | None = None,
    billing_email: str | None = None,
    default_vat_rate=None,
    is_active: bool | None = None,
) -> ClientDetailRead | None:
    client = db.scalar(
        select(Client).options(selectinload(Client.client_aliases)).where(Client.id == client_id)
    )
    if client is None:
        return None

    if name is not None:
        trimmed = normalize_client_name(name)
        if not trimmed:
            raise ValueError("Client name is required")
        client.name = trimmed

    if billing_email is not None:
        client.billing_email = billing_email.strip() if billing_email.strip() else None

    if default_vat_rate is not None:
        client.default_vat_rate = default_vat_rate

    if is_active is not None:
        client.is_active = is_active

    db.flush()
    return get_client_admin(db, client_id)
