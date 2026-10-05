
"""
SalesIA Enterprise
FASE 05-E.2

API de invitaciones, registro por invitación
y aprobación administrativa.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.connection import get_db

from app.api.routes.auth import obtener_access_token

from app.schemas.usuarios import (
    CrearInvitacionRequest,
    CrearInvitacionResponse,
    RegistroInvitacionRequest,
    RegistroInvitacionResponse,
    UsuarioPendienteResponse,
    AprobarUsuarioResponse,
)

from app.services.session_service import (
    SesionInvalidaError,
    validar_sesion,
)

from app.services.invitation_service import (
    InvitacionError,
    crear_invitacion,
)

from app.services.registration_service import (
    RegistroInvitacionError,
    registrar_con_invitacion,
)

from app.services.approval_service import (
    AprobacionError,
    listar_usuarios_pendientes,
    aprobar_usuario,
)


router = APIRouter(tags=["Gestión de usuarios"])


def obtener_administrador_id(
    access_token: str = Depends(obtener_access_token),
    db: Session = Depends(get_db),
) -> int:
    """
    Obtiene la identidad desde una sesión válida.

    Nunca acepta administrador_id ni empresa_id
    enviados por el frontend.
    """

    try:
        usuario = validar_sesion(
            db,
            access_token=access_token,
        )

        return usuario.id

    except SesionInvalidaError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no es válida.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post(
    "/api/invitaciones",
    response_model=CrearInvitacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_invitacion_http(
    datos: CrearInvitacionRequest,
    administrador_id: int = Depends(obtener_administrador_id),
    db: Session = Depends(get_db),
):
    try:
        return crear_invitacion(
            db,
            administrador_id=administrador_id,
            email_invitado=str(datos.email),
        )

    except InvitacionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/api/auth/register-invitation",
    response_model=RegistroInvitacionResponse,
    status_code=status.HTTP_201_CREATED,
)
def registro_invitacion_http(
    datos: RegistroInvitacionRequest,
    db: Session = Depends(get_db),
):
    try:
        return registrar_con_invitacion(
            db,
            token=datos.token,
            nombre=datos.nombre,
            email=str(datos.email),
            password=datos.password,
        )

    except RegistroInvitacionError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fue posible completar el registro con esta invitación.",
        ) from exc


@router.get(
    "/api/usuarios/pendientes",
    response_model=list[UsuarioPendienteResponse],
)
def usuarios_pendientes_http(
    administrador_id: int = Depends(obtener_administrador_id),
    db: Session = Depends(get_db),
):
    try:
        return listar_usuarios_pendientes(
            db,
            administrador_id=administrador_id,
        )

    except AprobacionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene autorización para consultar usuarios pendientes.",
        ) from exc


@router.post(
    "/api/usuarios/{usuario_id}/aprobar",
    response_model=AprobarUsuarioResponse,
)
def aprobar_usuario_http(
    usuario_id: int,
    administrador_id: int = Depends(obtener_administrador_id),
    db: Session = Depends(get_db),
):
    try:
        return aprobar_usuario(
            db,
            administrador_id=administrador_id,
            usuario_id=usuario_id,
        )

    except AprobacionError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No fue posible autorizar esta operación.",
        ) from exc
