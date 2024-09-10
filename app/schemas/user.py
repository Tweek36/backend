from datetime import datetime
from typing import Sequence
from pydantic import BaseModel, EmailStr
from uuid import UUID

from app.utils.pagination import PaginatedResponse


class UserBaseSchema(BaseModel):
    username: str
    email: EmailStr

    class Config:
        from_attributes = True


class UserResponseSchema(UserBaseSchema):
    id: UUID
    created_at: datetime
    updated_at: datetime


class PaginatedUserResponseSchema(PaginatedResponse):
    data: Sequence[UserResponseSchema]
