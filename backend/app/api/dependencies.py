
"""
SalesIA Enterprise
FASE 05-A.5

Dependencias de autenticación empresarial.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.usuario import Usuario
from app.services.session_service import (
    SesionInvalidaError,
    validar_sesion,
)


bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Devuelve el usuario autenticado después de validar
    el JWT y su sesión persistida en PostgreSQL.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionaron credenciales.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        return validar_sesion(
            db,
            access_token=credentials.credentials,
        )

    except SesionInvalidaError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciales inválidas o sesión expirada.",
            headers={"WWW-Authenticate": "Bearer"},
        )



def get_current_active_user(
    current_user: Usuario = Depends(get_current_user),
) -> Usuario:
    """
    Devuelve el usuario autenticado si está activo.
    """

    if not current_user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario se encuentra inactivo.",
        )

    return current_user


def get_current_empresa_id(
    current_user: Usuario = Depends(get_current_user),
) -> int:
    """
    Devuelve exclusivamente el identificador de empresa
    del usuario autenticado.

    No acepta empresa_id enviado por el cliente.
    """

    return current_user.empresa_id