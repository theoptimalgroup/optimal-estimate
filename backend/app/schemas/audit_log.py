from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogListRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    actor_user_id: UUID | None
    actor_email: str | None
    action: str
    entity_type: str
    entity_id: str | None
    summary: str
    ip_address: str | None
    created_at: datetime


class AuditLogDetailRead(AuditLogListRead):
    metadata: dict | None = None
    before_snapshot: dict | None = None
    after_snapshot: dict | None = None
