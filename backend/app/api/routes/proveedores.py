"""Rutas HTTP proveedores — JWT y RBAC del backend existente."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.api.dependencies import get_current_active_user
from app.models.usuario import Usuario
from app.schemas.proveedores import (
    ProveedorCrear, ProveedorActualizar, ProveedorRespuesta, ProveedorPagina,
)
from app.services.proveedor_service import (
    ProveedorServiceError, crear_proveedor, obtener_proveedor,
    listar_proveedores, actualizar_proveedor, desactivar_proveedor,
)

router = APIRouter(prefix='/api/proveedores', tags=['Proveedores'])


def _http_error(exc: ProveedorServiceError):
    mensaje = str(exc)
    if 'autorización' in mensaje.lower() or 'inactiv' in mensaje.lower() and ('usuario' in mensaje.lower() or 'empresa' in mensaje.lower()):
        codigo = status.HTTP_403_FORBIDDEN
    elif 'no encontrado' in mensaje.lower():
        codigo = status.HTTP_404_NOT_FOUND
    elif 'duplicad' in mensaje.lower() or 'ya está registrado' in mensaje.lower():
        codigo = status.HTTP_409_CONFLICT
    else:
        codigo = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=codigo, detail=mensaje) from exc


@router.post('', response_model=ProveedorRespuesta, status_code=status.HTTP_201_CREATED)
def crear_proveedor_http(
    datos: ProveedorCrear,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return crear_proveedor(db, usuario_id=usuario.id, **datos.model_dump())
    except ProveedorServiceError as exc:
        _http_error(exc)


@router.get('', response_model=ProveedorPagina)
def listar_proveedores_http(
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=100),
    busqueda: str | None = Query(default=None, max_length=200),
    activo: bool | None = None,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return listar_proveedores(db, usuario_id=usuario.id, pagina=pagina, limite=limite,
                                 busqueda=busqueda, activo=activo)
    except ProveedorServiceError as exc:
        _http_error(exc)


@router.get('/{proveedor_id}', response_model=ProveedorRespuesta)
def obtener_proveedor_http(
    proveedor_id: int,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return obtener_proveedor(db, usuario_id=usuario.id, proveedor_id=proveedor_id)
    except ProveedorServiceError as exc:
        _http_error(exc)


@router.patch('/{proveedor_id}', response_model=ProveedorRespuesta)
def actualizar_proveedor_http(
    proveedor_id: int,
    datos: ProveedorActualizar,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    cambios = datos.model_dump(exclude_unset=True)
    if not cambios:
        raise HTTPException(status_code=422, detail='Proporcione al menos un campo.')
    try:
        return actualizar_proveedor(db, usuario_id=usuario.id, proveedor_id=proveedor_id, **cambios)
    except ProveedorServiceError as exc:
        _http_error(exc)


@router.post('/{proveedor_id}/desactivar', response_model=ProveedorRespuesta)
def desactivar_proveedor_http(
    proveedor_id: int,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return desactivar_proveedor(db, usuario_id=usuario.id, proveedor_id=proveedor_id)
    except ProveedorServiceError as exc:
        _http_error(exc)
