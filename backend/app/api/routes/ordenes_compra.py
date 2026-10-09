"""Rutas HTTP órdenes de compra — JWT, RBAC y aislamiento provistos por SalesIA."""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.connection import get_db
from app.api.dependencies import get_current_active_user
from app.models.usuario import Usuario
from app.models.orden_compra_detalle import OrdenCompraDetalle
from app.schemas.ordenes_compra import OrdenCompraCrear, OrdenCompraRespuesta, OrdenCompraPagina
from app.services.orden_compra_service import (
    OrdenCompraServiceError, crear_orden_compra, obtener_orden_compra,
    listar_ordenes_compra, confirmar_orden_compra, cancelar_orden_compra,
)

router = APIRouter(prefix='/api/compras/ordenes', tags=['Órdenes de compra'])


def _http_error(exc: OrdenCompraServiceError):
    mensaje = str(exc)
    m = mensaje.lower()
    if 'autorización' in m or 'usuario inactivo' in m or 'empresa inactiva' in m:
        codigo = status.HTTP_403_FORBIDDEN
    elif 'no encontrada' in m or 'no encontrado' in m:
        codigo = status.HTTP_404_NOT_FOUND
    elif 'duplicad' in m or 'solo se puede' in m:
        codigo = status.HTTP_409_CONFLICT
    else:
        codigo = status.HTTP_400_BAD_REQUEST
    raise HTTPException(status_code=codigo, detail=mensaje) from exc


def _con_detalles(db: Session, orden):
    """Respuesta explícita: los modelos actuales no definen relación ORM a detalles."""
    detalles = db.scalars(select(OrdenCompraDetalle).where(
        OrdenCompraDetalle.orden_id == orden.id,
        OrdenCompraDetalle.empresa_id == orden.empresa_id,
    ).order_by(OrdenCompraDetalle.id)).all()
    return OrdenCompraRespuesta.model_validate({
        **{campo: getattr(orden, campo) for campo in OrdenCompraRespuesta.model_fields if campo != 'detalles'},
        'detalles': [DetalleCompraRespuesta.model_validate(d) for d in detalles],
    })

# Importado después de definir el método para mantener explícitos los contratos.
from app.schemas.ordenes_compra import DetalleCompraRespuesta


@router.post('', response_model=OrdenCompraRespuesta, status_code=status.HTTP_201_CREATED)
def crear_orden_http(
    datos: OrdenCompraCrear,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        orden = crear_orden_compra(db, usuario_id=usuario.id, **datos.model_dump())
        return _con_detalles(db, orden)
    except OrdenCompraServiceError as exc:
        _http_error(exc)


@router.get('', response_model=OrdenCompraPagina)
def listar_ordenes_http(
    estado: str | None = Query(default=None, max_length=30),
    proveedor_id: int | None = Query(default=None, gt=0),
    pagina: int = Query(default=1, ge=1),
    limite: int = Query(default=20, ge=1, le=100),
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        resultado = listar_ordenes_compra(db, usuario_id=usuario.id, estado=estado,
                                          proveedor_id=proveedor_id, pagina=pagina, limite=limite)
        return {**resultado, 'items': [_con_detalles(db, o) for o in resultado['items']]}
    except OrdenCompraServiceError as exc:
        _http_error(exc)


@router.get('/{orden_id}', response_model=OrdenCompraRespuesta)
def obtener_orden_http(
    orden_id: int,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return _con_detalles(db, obtener_orden_compra(db, usuario_id=usuario.id, orden_id=orden_id))
    except OrdenCompraServiceError as exc:
        _http_error(exc)


@router.post('/{orden_id}/confirmar', response_model=OrdenCompraRespuesta)
def confirmar_orden_http(
    orden_id: int,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return _con_detalles(db, confirmar_orden_compra(db, usuario_id=usuario.id, orden_id=orden_id))
    except OrdenCompraServiceError as exc:
        _http_error(exc)


@router.post('/{orden_id}/cancelar', response_model=OrdenCompraRespuesta)
def cancelar_orden_http(
    orden_id: int,
    usuario: Usuario = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    try:
        return _con_detalles(db, cancelar_orden_compra(db, usuario_id=usuario.id, orden_id=orden_id))
    except OrdenCompraServiceError as exc:
        _http_error(exc)
