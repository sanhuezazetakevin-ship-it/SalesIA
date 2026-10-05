
"""
SalesIA Enterprise
FASE 06-D.2

API REST empresarial de clientes.

Seguridad:
- JWT y sesion persistida mediante get_current_user.
- RBAC validado nuevamente dentro del servicio.
- Aislamiento multiempresa.
- Nunca aceptar empresa_id desde el frontend.
- DELETE realiza baja logica.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.database.connection import get_db
from app.models.usuario import Usuario

from app.schemas.clientes import (
    ClienteCreate,
    ClienteUpdate,
    ClienteResponse,
    ClienteListadoResponse,
)

from app.services.client_service import (
    ClienteServiceError,
    crear_cliente,
    obtener_cliente,
    listar_clientes,
    actualizar_cliente,
    desactivar_cliente,
)


router = APIRouter(
    prefix="/api/clientes",
    tags=["Clientes"],
)


def _rechazar_operacion_clientes(exc: ClienteServiceError):
    """
    Respuesta uniforme para los errores del servicio.

    No revela documentos duplicados, existencia de
    clientes ajenos ni detalles internos de seguridad.
    """

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="No fue posible autorizar o completar esta operacion de clientes.",
    ) from exc


@router.post(
    "",
    response_model=ClienteResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_cliente_http(
    datos: ClienteCreate,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return crear_cliente(
            db,
            usuario_id=usuario_actual.id,
            datos=datos,
        )

    except ClienteServiceError as exc:
        _rechazar_operacion_clientes(exc)


@router.get(
    "",
    response_model=ClienteListadoResponse,
)
def listar_clientes_http(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=100),
    busqueda: str | None = Query(default=None, max_length=200),
    activo: bool | None = Query(default=None),
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return listar_clientes(
            db,
            usuario_id=usuario_actual.id,
            pagina=pagina,
            limite=limite,
            busqueda=busqueda,
            activo=activo,
        )

    except ClienteServiceError as exc:
        _rechazar_operacion_clientes(exc)


@router.get(
    "/{cliente_id}",
    response_model=ClienteResponse,
)
def obtener_cliente_http(
    cliente_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return obtener_cliente(
            db,
            usuario_id=usuario_actual.id,
            cliente_id=cliente_id,
        )

    except ClienteServiceError as exc:
        _rechazar_operacion_clientes(exc)


@router.patch(
    "/{cliente_id}",
    response_model=ClienteResponse,
)
def actualizar_cliente_http(
    cliente_id: int,
    datos: ClienteUpdate,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return actualizar_cliente(
            db,
            usuario_id=usuario_actual.id,
            cliente_id=cliente_id,
            datos=datos,
        )

    except ClienteServiceError as exc:
        _rechazar_operacion_clientes(exc)


@router.delete(
    "/{cliente_id}",
    response_model=ClienteResponse,
)
def desactivar_cliente_http(
    cliente_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return desactivar_cliente(
            db,
            usuario_id=usuario_actual.id,
            cliente_id=cliente_id,
        )

    except ClienteServiceError as exc:
        _rechazar_operacion_clientes(exc)
