from pydantic import BaseModel, Field, EmailStr, model_validator, field_validator
from app.schemas.user import UserBaseSchema
from fastapi import HTTPException

class TokenSchema(BaseModel):
    token: str


class CreaateNewPasswordSchema(BaseModel):
    password: str = Field(min_length=8)
    passwordConfirm: str

    @field_validator('password')
    def validate_password_length(cls, v):
        if len(v) <= 8:
            raise HTTPException(400, 'Password must be longer than 8 characters')
        return v

    @model_validator(mode='after')
    def check_passwords_match(self):
        if self.password != self.passwordConfirm:
            raise HTTPException(400, 'Passwords do not match')
        return self
    
    
class CreateUserSchema(UserBaseSchema, CreaateNewPasswordSchema): ...


class ResetPasswordSchema(CreaateNewPasswordSchema):
    token: str


class LoginUserSchema(BaseModel):
    username: str
    password: str

    @field_validator('password')
    def validate_password_length(cls, v):
        if len(v) <= 8:
            raise HTTPException(400, 'Password must be longer than 8 characters')
        return v


class RefreshTokenResponseSchema(BaseModel):
    refresh_token: str


class AccessTokenResponseSchema(BaseModel):
    access_token: str


class AccessRefreshTokensResponseSchema(
    RefreshTokenResponseSchema, AccessTokenResponseSchema
): ...


class LogoutPayloadSchema(BaseModel):
    refresh_token: str
    access_token: str

class EmailPayloadSchema(BaseModel):
    email: EmailStr