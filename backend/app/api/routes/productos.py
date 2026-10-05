
"""
SalesIA Enterprise
FASE 07-D — API REST empresarial de Productos.

JWT + sesion persistida.
RBAC validado dentro del servicio.
Aislamiento multiempresa.
DELETE realiza baja logica.
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

from app.schemas.productos import (
    ProductoCreate,
    ProductoUpdate,
    ProductoResponse,
    ProductoListadoResponse,
)

from app.services.product_service import (
    ProductoServiceError,
    crear_producto,
    obtener_producto,
    listar_productos,
    actualizar_producto,
    desactivar_producto,
)


router = APIRouter(
    prefix="/api/productos",
    tags=["Productos"],
)


def _rechazar_operacion_producto(exc: ProductoServiceError):
    """
    Respuesta uniforme para no revelar productos ajenos,
    duplicados u otros detalles empresariales.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "No fue posible autorizar o completar "
            "esta operacion de productos."
        ),
    ) from exc


@router.post(
    "",
    response_model=ProductoResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_producto_http(
    datos: ProductoCreate,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return crear_producto(
            db,
            usuario_id=usuario_actual.id,
            datos=datos,
        )
    except ProductoServiceError as exc:
        _rechazar_operacion_producto(exc)


@router.get(
    "",
    response_model=ProductoListadoResponse,
)
def listar_productos_http(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=100),
    busqueda: str | None = Query(default=None, max_length=200),
    categoria_id: int | None = Query(default=None, gt=0),
    tipo_item: str | None = Query(default=None),
    activo: bool | None = Query(default=None),
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return listar_productos(
            db,
            usuario_id=usuario_actual.id,
            pagina=pagina,
            limite=limite,
            busqueda=busqueda,
            categoria_id=categoria_id,
            tipo_item=tipo_item,
            activo=activo,
        )
    except ProductoServiceError as exc:
        _rechazar_operacion_producto(exc)


@router.get(
    "/{producto_id}",
    response_model=ProductoResponse,
)
def obtener_producto_http(
    producto_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return obtener_producto(
            db,
            usuario_id=usuario_actual.id,
            producto_id=producto_id,
        )
    except ProductoServiceError as exc:
        _rechazar_operacion_producto(exc)


@router.patch(
    "/{producto_id}",
    response_model=ProductoResponse,
)
def actualizar_producto_http(
    producto_id: int,
    datos: ProductoUpdate,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return actualizar_producto(
            db,
            usuario_id=usuario_actual.id,
            producto_id=producto_id,
            datos=datos,
        )
    except ProductoServiceError as exc:
        _rechazar_operacion_producto(exc)


@router.delete(
    "/{producto_id}",
    response_model=ProductoResponse,
)
def desactivar_producto_http(
    producto_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return desactivar_producto(
            db,
            usuario_id=usuario_actual.id,
            producto_id=producto_id,
        )
    except ProductoServiceError as exc:
        _rechazar_operacion_producto(exc)
