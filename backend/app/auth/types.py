from dataclasses import dataclass

from app.core.security import UserRole


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str
    name: str
    role: UserRole
    is_active: bool
    auth_provider: str
