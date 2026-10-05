
"""
SalesIA Enterprise
FASE 07-D — API REST empresarial de Categorias.

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

from app.schemas.categorias import (
    CategoriaCreate,
    CategoriaUpdate,
    CategoriaResponse,
    CategoriaListadoResponse,
)

from app.services.category_service import (
    CategoriaServiceError,
    crear_categoria,
    obtener_categoria,
    listar_categorias,
    actualizar_categoria,
    desactivar_categoria,
)


router = APIRouter(
    prefix="/api/categorias",
    tags=["Categorias"],
)


def _rechazar_operacion_categoria(exc: CategoriaServiceError):
    """
    No revela si una categoria pertenece a otra empresa,
    si existe un duplicado ni detalles internos del RBAC.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=(
            "No fue posible autorizar o completar "
            "esta operacion de categorias."
        ),
    ) from exc


@router.post(
    "",
    response_model=CategoriaResponse,
    status_code=status.HTTP_201_CREATED,
)
def crear_categoria_http(
    datos: CategoriaCreate,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return crear_categoria(
            db,
            usuario_id=usuario_actual.id,
            datos=datos,
        )
    except CategoriaServiceError as exc:
        _rechazar_operacion_categoria(exc)


@router.get(
    "",
    response_model=CategoriaListadoResponse,
)
def listar_categorias_http(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=100),
    busqueda: str | None = Query(default=None, max_length=120),
    activo: bool | None = Query(default=None),
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return listar_categorias(
            db,
            usuario_id=usuario_actual.id,
            pagina=pagina,
            limite=limite,
            busqueda=busqueda,
            activo=activo,
        )
    except CategoriaServiceError as exc:
        _rechazar_operacion_categoria(exc)


@router.get(
    "/{categoria_id}",
    response_model=CategoriaResponse,
)
def obtener_categoria_http(
    categoria_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return obtener_categoria(
            db,
            usuario_id=usuario_actual.id,
            categoria_id=categoria_id,
        )
    except CategoriaServiceError as exc:
        _rechazar_operacion_categoria(exc)


@router.patch(
    "/{categoria_id}",
    response_model=CategoriaResponse,
)
def actualizar_categoria_http(
    categoria_id: int,
    datos: CategoriaUpdate,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return actualizar_categoria(
            db,
            usuario_id=usuario_actual.id,
            categoria_id=categoria_id,
            datos=datos,
        )
    except CategoriaServiceError as exc:
        _rechazar_operacion_categoria(exc)


@router.delete(
    "/{categoria_id}",
    response_model=CategoriaResponse,
)
def desactivar_categoria_http(
    categoria_id: int,
    usuario_actual: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return desactivar_categoria(
            db,
            usuario_id=usuario_actual.id,
            categoria_id=categoria_id,
        )
    except CategoriaServiceError as exc:
        _rechazar_operacion_categoria(exc)
