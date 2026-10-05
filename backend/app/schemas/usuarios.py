
"""
SalesIA Enterprise
FASE 05-E.1

Contratos HTTP de invitaciones, registro
y aprobación administrativa.
"""

from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


class EsquemaEstricto(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------
# INVITACIONES
# ---------------------------------------

class CrearInvitacionRequest(EsquemaEstricto):
    email: EmailStr


class CrearInvitacionResponse(EsquemaEstricto):
    invitacion_id: int
    empresa_id: int
    email: EmailStr
    token: str
    fecha_expiracion: datetime


# ---------------------------------------
# REGISTRO POR INVITACIÓN
# ---------------------------------------

class RegistroInvitacionRequest(EsquemaEstricto):
    token: str = Field(
        min_length=43,
        max_length=43,
    )

    nombre: str = Field(
        min_length=2,
        max_length=120,
    )

    email: EmailStr

    password: str = Field(
        min_length=12,
        max_length=128,
    )


class RegistroInvitacionResponse(EsquemaEstricto):
    usuario_id: int
    empresa_id: int
    nombre: str
    email: EmailStr
    activo: bool
    estado: str
    mensaje: str


# ---------------------------------------
# APROBACIÓN ADMINISTRATIVA
# ---------------------------------------

class UsuarioPendienteResponse(EsquemaEstricto):
    usuario_id: int
    empresa_id: int
    nombre: str
    email: EmailStr
    activo: bool
    created_at: datetime


class AprobarUsuarioResponse(EsquemaEstricto):
    usuario_id: int
    empresa_id: int
    nombre: str
    email: EmailStr
    activo: bool
    estado: str
    aprobado_por_id: int
