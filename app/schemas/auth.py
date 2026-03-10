from pydantic import BaseModel, EmailStr
from app.models.user import RoleEnum

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: int
    name: str
    email: str
    role: RoleEnum

class RefreshRequest(BaseModel):
    refresh_token: str