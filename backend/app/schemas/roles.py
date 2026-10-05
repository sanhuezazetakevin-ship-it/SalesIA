
"""
SalesIA Enterprise
FASE 05-F.4

Esquemas HTTP para la gestion empresarial de roles.
"""

from pydantic import BaseModel, Field
from pydantic import ConfigDict

class RolResponse(BaseModel):
    rol_id: int
    empresa_id: int
    nombre: str
    descripcion: str | None = None


class RolPermisosResponse(RolResponse):
    permisos: list[str]


class AsignacionRolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usuario_id: int = Field(gt=0, strict=True)
    rol_id: int = Field(gt=0, strict=True)


class AsignacionRolResponse(BaseModel):
    usuario_id: int
    empresa_id: int
    rol_id: int
    rol_nombre: str
    estado: str
    administrador_id: int


class RevocacionRolResponse(AsignacionRolResponse):
    sesiones_revocadas: int
