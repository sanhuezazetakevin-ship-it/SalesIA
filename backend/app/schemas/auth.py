
"""
SalesIA Enterprise
FASE 05-D.1

Contratos Pydantic para autenticación empresarial.
"""

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: EmailStr
    password: str = Field(
        min_length=1,
        max_length=1024,
    )


class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    refresh_token: str = Field(
        min_length=1,
    )


class UsuarioAuthResponse(BaseModel):
    id: int
    empresa_id: int
    nombre: str
    email: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(ge=1)


class LoginResponse(TokenResponse):
    usuario: UsuarioAuthResponse


class LogoutResponse(BaseModel):
    mensaje: str = "Sesión cerrada correctamente."


class MeResponse(BaseModel):
    id: int
    empresa_id: int
    nombre: str
    email: str
    activo: bool
