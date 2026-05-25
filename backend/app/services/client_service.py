from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.client_alias import ClientAlias

KNOWN_CLIENT_ALIASES: dict[str, str] = {
    "Lambert Chartered Surveyors": "Lamberts Chartered Surveyors",
}


def normalize_client_name(name: str) -> str:
    return " ".join(name.strip().split())


def get_canonical_client_name(name: str) -> str:
    normalized = normalize_client_name(name)
    return KNOWN_CLIENT_ALIASES.get(normalized, normalized)


def ensure_client_alias(db: Session, client: Client, alias_name: str) -> ClientAlias | None:
    normalized = normalize_client_name(alias_name)
    if normalized == client.name:
        return None

    existing = db.scalar(select(ClientAlias).where(ClientAlias.alias_name == normalized))
    if existing:
        if existing.client_id != client.id:
            raise ValueError(f"Alias '{normalized}' already belongs to another client")
        return existing

    alias = ClientAlias(client_id=client.id, alias_name=normalized)
    db.add(alias)
    db.flush()
    return alias


def find_client_by_name_or_alias(db: Session, name: str) -> Client | None:
    normalized = normalize_client_name(name)
    client = db.scalar(select(Client).where(Client.name == normalized))
    if client:
        return client

    alias = db.scalar(select(ClientAlias).where(ClientAlias.alias_name == normalized))
    if alias:
        return db.get(Client, alias.client_id)

    canonical = get_canonical_client_name(normalized)
    if canonical != normalized:
        return db.scalar(select(Client).where(Client.name == canonical))
    return None


def get_or_create_client_for_import(db: Session, source_name: str) -> tuple[Client, bool, bool]:
    """Return (client, created, alias_added)."""
    source_name = normalize_client_name(source_name)
    canonical_name = get_canonical_client_name(source_name)

    client = find_client_by_name_or_alias(db, canonical_name)
    if client is None and canonical_name != source_name:
        client = find_client_by_name_or_alias(db, source_name)

    created = False
    if client is None:
        client = Client(name=canonical_name, billing_email=None, default_vat_rate=Decimal("20"))
        db.add(client)
        db.flush()
        created = True

    alias_added = False
    if source_name != canonical_name:
        before = db.scalar(
            select(ClientAlias).where(
                ClientAlias.client_id == client.id,
                ClientAlias.alias_name == source_name,
            )
        )
        ensure_client_alias(db, client, source_name)
        after = db.scalar(
            select(ClientAlias).where(
                ClientAlias.client_id == client.id,
                ClientAlias.alias_name == source_name,
            )
        )
        alias_added = before is None and after is not None

    return client, created, alias_added


def get_client_aliases_map(db: Session, client_ids: list[UUID]) -> dict[UUID, list[str]]:
    if not client_ids:
        return {}
    rows = db.execute(
        select(ClientAlias.client_id, ClientAlias.alias_name)
        .where(ClientAlias.client_id.in_(client_ids))
        .order_by(ClientAlias.alias_name)
    ).all()
    aliases: dict[UUID, list[str]] = {client_id: [] for client_id in client_ids}
    for client_id, alias_name in rows:
        aliases[client_id].append(alias_name)
    return aliases


def client_ids_matching_search(db: Session, search: str) -> list[UUID]:
    term = f"%{search.strip().lower()}%"
    if not search.strip():
        return []

    alias_client_ids = select(ClientAlias.client_id).where(func.lower(ClientAlias.alias_name).like(term))
    rows = db.scalars(
        select(Client.id).where(
            or_(
                func.lower(Client.name).like(term),
                Client.id.in_(alias_client_ids),
            )
        )
    ).all()
    return list(rows)


def client_search_filter(search: str | None):
    if not search or not search.strip():
        return None

    term = f"%{search.strip().lower()}%"
    alias_client_ids = select(ClientAlias.client_id).where(func.lower(ClientAlias.alias_name).like(term))
    return or_(
        func.lower(Client.name).like(term),
        Client.id.in_(alias_client_ids),
    )
