from pydantic import BaseModel, EmailStr

from app.core.security import UserRole


class CurrentUserRead(BaseModel):
    id: str
    email: EmailStr
    name: str
    role: UserRole
    is_active: bool
    auth_provider: str
