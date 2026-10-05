
"""
SalesIA Enterprise
FASE 05-F.4

API HTTP de roles empresariales.

La identidad del administrador procede exclusivamente
del JWT y de su sesion persistida en PostgreSQL.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.models.usuario import Usuario

from app.schemas.roles import (
    RolResponse,
    RolPermisosResponse,
    AsignacionRolRequest,
    AsignacionRolResponse,
    RevocacionRolResponse,
)

from app.services.role_service import (
    RolServiceError,
    listar_roles_empresa,
    listar_permisos_rol,
    asignar_rol_usuario,
    revocar_rol_usuario,
)


router = APIRouter(
    prefix="/api/roles",
    tags=["Roles y permisos"],
)


def _rechazar_operacion_rbac(exc: RolServiceError):
    """
    Respuesta uniforme: no expone detalles internos
    ni permite descubrir recursos de otras empresas.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No fue posible autorizar esta operacion RBAC.",
    ) from exc


@router.get(
    "",
    response_model=list[RolResponse],
)
def listar_roles_http(
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return listar_roles_empresa(
            db,
            administrador_id=usuario_actual.id,
        )
    except RolServiceError as exc:
        _rechazar_operacion_rbac(exc)


@router.get(
    "/{rol_id}/permisos",
    response_model=RolPermisosResponse,
)
def listar_permisos_rol_http(
    rol_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return listar_permisos_rol(
            db,
            administrador_id=usuario_actual.id,
            rol_id=rol_id,
        )
    except RolServiceError as exc:
        _rechazar_operacion_rbac(exc)


@router.post(
    "/asignaciones",
    response_model=AsignacionRolResponse,
    status_code=status.HTTP_201_CREATED,
)
def asignar_rol_http(
    datos: AsignacionRolRequest,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return asignar_rol_usuario(
            db,
            administrador_id=usuario_actual.id,
            usuario_id=datos.usuario_id,
            rol_id=datos.rol_id,
        )
    except RolServiceError as exc:
        _rechazar_operacion_rbac(exc)


@router.delete(
    "/asignaciones",
    response_model=RevocacionRolResponse,
)
def revocar_rol_http(
    datos: AsignacionRolRequest,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return revocar_rol_usuario(
            db,
            administrador_id=usuario_actual.id,
            usuario_id=datos.usuario_id,
            rol_id=datos.rol_id,
        )
    except RolServiceError as exc:
        _rechazar_operacion_rbac(exc)
