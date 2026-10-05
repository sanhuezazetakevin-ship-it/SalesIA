
"""
SalesIA Enterprise
FASE 05-D.2

Endpoints HTTP de autenticación empresarial.

La lógica de negocio permanece en los servicios.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from sqlalchemy.orm import Session

from app.database.connection import get_db

from app.schemas.auth import (
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    TokenResponse,
    LogoutResponse,
    MeResponse,
)

from app.services.login_service import (
    LoginError,
    iniciar_sesion,
)

from app.services.session_service import (
    SesionInvalidaError,
    validar_sesion,
    renovar_sesion,
    revocar_sesion,
)


router = APIRouter(
    prefix="/api/auth",
    tags=["Autenticación"],
)

bearer_scheme = HTTPBearer(
    auto_error=False,
)


def obtener_access_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> str:
    """Extrae el Bearer token de la solicitud."""

    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autenticación requerida.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return credentials.credentials


@router.post(
    "/login",
    response_model=LoginResponse,
)
def login(
    datos: LoginRequest,
    db: Session = Depends(get_db),
):
    try:
        return iniciar_sesion(
            db,
            email=str(datos.email),
            password=datos.password,
        )

    except LoginError as exc:
        # No revelar por HTTP si el correo existe,
        # si falta aprobación o si la empresa está inactiva.
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No fue posible iniciar sesión con estas credenciales.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh(
    datos: RefreshRequest,
    db: Session = Depends(get_db),
):
    try:
        return renovar_sesion(
            db,
            refresh_token=datos.refresh_token,
        )

    except SesionInvalidaError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No fue posible renovar la sesión.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.post(
    "/logout",
    response_model=LogoutResponse,
)
def logout(
    access_token: str = Depends(obtener_access_token),
    db: Session = Depends(get_db),
):
    try:
        revocar_sesion(
            db,
            access_token=access_token,
        )

        return LogoutResponse()

    except SesionInvalidaError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no es válida.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


@router.get(
    "/me",
    response_model=MeResponse,
)
def me(
    access_token: str = Depends(obtener_access_token),
    db: Session = Depends(get_db),
):
    try:
        usuario = validar_sesion(
            db,
            access_token=access_token,
        )

        return MeResponse(
            id=usuario.id,
            empresa_id=usuario.empresa_id,
            nombre=usuario.nombre,
            email=usuario.email,
            activo=usuario.activo,
        )

    except SesionInvalidaError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="La sesión no es válida.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
